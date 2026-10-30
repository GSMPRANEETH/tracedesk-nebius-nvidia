"""Offline/local-HTTP invariant checks. No live model or answer-quality claim."""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import subprocess
import tempfile
import threading
import time
from unittest.mock import patch

from tracedesk.core import Store, answer, load_runbook, validate_response


def rejects(fn, error=ValueError):
    try:
        fn()
    except error:
        return
    raise AssertionError("Expected rejection")


class ProviderFixture(BaseHTTPRequestHandler):
    """Local HTTP transport fixture; never represents a Nebius result."""

    def log_message(self, *_):
        pass

    def do_GET(self):
        self.server.received.append(dict(path=self.path, headers=dict(self.headers), body=None))
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        self.server.received.append(dict(path=self.path, headers=dict(self.headers), body=json.loads(body)))
        mode = self.server.mode
        status, raw = 200, json.dumps(self.server.response).encode()
        if mode == "invalid-json":
            raw = b"fixture-private-marker: not JSON"
        elif mode == "invalid-utf8":
            raw = b"\xff"
        elif mode == "unauthorized":
            status, raw = 401, b"fixture-private-marker"
        elif mode == "redirect":
            self.send_response(302)
            self.send_header("Location", self.server.redirect)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        elif mode == "oversized":
            raw = b"x" * 1_000_001
        elif mode == "truncated":
            self.send_response(200)
            self.send_header("Content-Length", "100")
            self.end_headers()
            self.wfile.write(b"{}")
            self.close_connection = True
            return
        elif mode == "transient" and len(self.server.received) == 1:
            status, raw = 503, b"fixture-private-marker"
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if mode == "slow-drip":
            try:
                for octet in raw:
                    self.wfile.write(bytes([octet]))
                    self.wfile.flush()
                    time.sleep(.02)  # Each byte arrives well inside urllib's 25-second idle timeout.
            except (BrokenPipeError, ConnectionResetError):
                self.server.disconnected.set()
            return
        self.wfile.write(raw)


def transport_checks(payload):
    provider = HTTPServer(("127.0.0.1", 0), ProviderFixture)
    target = HTTPServer(("127.0.0.1", 0), ProviderFixture)
    response = dict(choices=[dict(message=dict(content=json.dumps(payload)))],
                    usage=dict(prompt_tokens=50, completion_tokens=10, total_tokens=60))
    for server in (provider, target):
        server.received, server.mode, server.response = [], "success", response
        threading.Thread(target=server.serve_forever, daemon=True).start()
    provider.redirect = f"http://127.0.0.1:{target.server_port}/credential-target"
    try:
        with patch("tracedesk.core.API_URL", f"http://127.0.0.1:{provider.server_port}/v1/chat/completions"), \
                patch.dict("os.environ", {"NEBIUS_API_KEY": "fixture-key-not-real", "NEBIUS_MODEL": "nvidia/fixture-not-real"}):
            result = answer("Port?", "RelayGate", "2.0", [])
            assert result["evidence_quotes"] == payload["evidence_quotes"]
            assert result["evidence_validation"] == "exact-source-quotes"
            sent = provider.received[-1]
            assert sent["path"] == "/v1/chat/completions"
            assert sent["headers"]["Authorization"] == "Bearer fixture-key-not-real"
            assert sent["headers"]["Content-Type"] == "application/json"
            assert sent["body"]["model"] == "nvidia/fixture-not-real"
            assert sent["body"]["response_format"] == {"type": "json_object"}
            assert sent["body"]["max_tokens"] == 1400
            assert all(p["version"] == "2.0" for p in json.loads(sent["body"]["messages"][1]["content"])["evidence"])
            assert "evidence_quotes" in sent["body"]["messages"][0]["content"]
            for mode in ("invalid-json", "invalid-utf8", "unauthorized", "redirect", "oversized", "truncated"):
                provider.mode, provider.received = mode, []
                try:
                    answer("Port?", "RelayGate", "2.0", [])
                except RuntimeError as exc:
                    assert "fixture-private-marker" not in str(exc) and "fixture-key" not in str(exc)
                else:
                    raise AssertionError(f"Provider mode {mode} should fail")
            assert not target.received, "A provider credential must never follow a redirect"
            provider.mode, provider.received = "transient", []
            assert answer("Port?", "RelayGate", "2.0", [])["status"] == "answer"
            assert len(provider.received) == 2
            provider.mode, provider.received = "slow-drip", []
            provider.disconnected = threading.Event()
            processes = []
            real_popen = subprocess.Popen
            def capture_process(*args, **kwargs):
                assert Path(args[0][1]).is_absolute() and args[0][-1] == "--provider-worker"
                assert Path(kwargs["cwd"]).resolve() == Path(__file__).resolve().parent
                assert not any("fixture-key" in str(arg) for arg in args[0])
                process = real_popen(*args, **kwargs)
                processes.append(process)
                return process
            started = time.monotonic()
            with patch("tracedesk.core.PROVIDER_DEADLINE_SECONDS", .6), \
                    patch("tracedesk.core.subprocess.Popen", side_effect=capture_process):
                try:
                    answer("Port?", "RelayGate", "2.0", [])
                except RuntimeError as exc:
                    assert "total request deadline" in str(exc)
                    assert "fixture-key" not in str(exc)
                else:
                    raise AssertionError("A continuously dripping body must not escape the overall deadline")
            assert time.monotonic() - started < 3, "The worker exceeded the bounded local-test deadline"
            assert len(processes) == 1 and processes[0].poll() is not None, "Timed-out worker must be killed and reaped"
            assert len(provider.received) == 1, "Retries must not continue beyond the total budget"
            assert provider.disconnected.wait(1), "Killed worker must close its active provider connection"
            provider.mode = "success"
            provider.response = dict(choices=[dict(message=dict(content=json.dumps({
                **payload, "evidence_quotes": [{"passage_id": "rg2-port", "quote": "Fabricated fixture evidence"}]})))])
            rejects(lambda: answer("Port?", "RelayGate", "2.0", []), RuntimeError)
    finally:
        for server in (provider, target):
            server.shutdown()
            server.server_close()


def main():
    runbook = load_runbook()
    assert len(runbook) == 20
    evidence = [p for p in runbook if p["version"] == "2.0"]
    quote = "RelayGate 2.0 listens on TCP port 9090 by default."
    payload = dict(status="answer", answer="The default port is 9090.", citations=["rg2-port"], used_correction_ids=[],
                   evidence_quotes=[dict(passage_id="rg2-port", quote=quote)])
    assert validate_response(payload, evidence, [])["status"] == "answer"
    rejects(lambda: validate_response({**payload, "citations": ["made-up"]}, evidence, []))
    rejects(lambda: validate_response({**payload, "citations": ["rg1-port"]}, evidence, []))
    rejects(lambda: validate_response({**payload, "citations": []}, evidence, []))
    rejects(lambda: validate_response({**payload, "used_correction_ids": ["mem-9"]}, evidence, []))
    rejects(lambda: validate_response({**payload, "status": "insufficient_evidence"}, evidence, []))
    no_evidence = dict(status="insufficient_evidence", answer="The supplied sources do not answer that.",
                       citations=[], used_correction_ids=[], evidence_quotes=[])
    assert validate_response(no_evidence, evidence, [])["status"] == "insufficient_evidence"
    assert validate_response({**payload, "status": "review_needed"}, evidence, [])["status"] == "review_needed"
    rejects(lambda: validate_response({k: v for k, v in payload.items() if k != "evidence_quotes"}, evidence, []))
    for quotes in (None, {}, [], [None], [dict(passage_id="rg2-port", quote="")],
                   [dict(passage_id="rg2-port", quote=42)], [dict(passage_id="rg2-port", quote="é" * 1001)],
                   [dict(passage_id="rg2-port", quote="The port is 6666.")],
                   [dict(passage_id="rg1-port", quote="RelayGate 1.0 listens on TCP port 8080 by default.")],
                   [dict(passage_id="rg2-auth", quote=evidence[1]["text"])],
                   payload["evidence_quotes"] + [dict(passage_id="rg2-auth", quote=evidence[1]["text"])],
                   payload["evidence_quotes"] * 2):
        rejects(lambda q=quotes: validate_response({**payload, "evidence_quotes": q}, evidence, []))
    rejects(lambda: validate_response({**no_evidence, "evidence_quotes": payload["evidence_quotes"]}, evidence, []))
    rejects(lambda: validate_response({**payload, "citations": ["rg2-port", "rg2-auth"]}, evidence, []))
    rejects(lambda: validate_response({**no_evidence, "status": "review_needed"}, evidence, []))
    python_sources = [p for p in runbook if (p["product"], p["version"]) == ("Python queues", "3.13")]
    public_payload = dict(status="answer", answer="Immediate shutdown does not prove work completed.",
                          citations=["py313-join"], used_correction_ids=[],
                          evidence_quotes=[dict(passage_id="py313-join", quote=python_sources[1]["text"])])
    assert validate_response(public_payload, python_sources, [])["evidence_validation"] == "exact-source-quotes"
    rejects(lambda: validate_response(public_payload,
        [p for p in runbook if (p["product"], p["version"]) == ("Python queues", "3.12")], []))
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "memory.sqlite"
        store = Store(path)
        rejects(lambda: store.save("RelayGate", "2.0", "Port?", quote, ["rg2-port"], False))
        rejects(lambda: store.save("RelayGate", "2.0", "Port?", quote, ["rg1-port"], True))
        rejects(lambda: store.save("RelayGate", "2.0", "Port?", "Use port 6666.", ["rg2-port"], True))
        rejects(lambda: store.save("RelayGate", "2.0", "Port?", quote, [], True))
        correction = store.save("RelayGate", "2.0", "Port?", quote, ["rg2-port"], True)
        updated = store.save("RelayGate", "2.0", "  PORT? ", quote, ["rg2-port"], True)
        assert correction["id"] == updated["id"]
        assert len(Store(path).list("RelayGate", "2.0")) == 1
        assert not store.list("RelayGate", "1.0")
        used_payload = {**payload, "used_correction_ids": [correction["id"]]}
        assert validate_response(used_payload, evidence, [correction])["used_correction_ids"] == [correction["id"]]
        rejects(lambda: validate_response({**used_payload, "citations": ["rg2-auth"]}, evidence, [correction]))

        captured = []
        def fake_infer(messages, model):
            import json
            captured.append(json.loads(messages[1]["content"]))
            return dict(choices=[dict(message=dict(content=json.dumps(payload)))],
                        usage=dict(prompt_tokens=50, completion_tokens=10, total_tokens=60))

        with patch("tracedesk.core._infer", side_effect=fake_infer):
            result = answer("What port?", "RelayGate", "2.0", [correction])
            assert result["provider"] == "Nebius Token Factory" and result["usage"]["total_tokens"] == 60
            assert captured[-1]["approved_corrections"][0]["id"] == correction["id"]
            answer("What port?", "RelayGate", "2.0", [correction], use_memory=False)
            assert captured[-1]["approved_corrections"] == []
            # A wrong-version record must never reach the model.
            answer("What port?", "RelayGate", "2.0", [{**correction, "version": "1.0"}])
            assert captured[-1]["approved_corrections"] == []
            assert all(p["version"] == "2.0" for p in captured[-1]["evidence"])
        with patch("tracedesk.core._infer", return_value={"choices": []}):
            rejects(lambda: answer("Port?", "RelayGate", "2.0", []), RuntimeError)
        with patch("tracedesk.core._infer", return_value={"choices": [{"message": {"content":
                json.dumps(payload)}}], "usage": [1]}):
            rejects(lambda: answer("Port?", "RelayGate", "2.0", []), RuntimeError)
        with patch("tracedesk.core._infer", side_effect=RuntimeError("Provider failed")):
            rejects(lambda: answer("Port?", "RelayGate", "2.0", []), RuntimeError)
        rejects(lambda: answer(" ", "RelayGate", "2.0", []))
        rejects(lambda: answer("é" * 1_001, "RelayGate", "2.0", []))
        rejects(lambda: answer("\ud800", "RelayGate", "2.0", []))
        rejects(lambda: answer("Port?", "RelayGate", "3.0", []))
        rejects(lambda: answer("Port?", "RelayGate", "2.0", [], use_memory="false"))
        with patch.dict("os.environ", {"NEBIUS_API_KEY": ""}):
            with patch("tracedesk.core.subprocess.run") as worker:
                rejects(lambda: answer("Port?", "RelayGate", "2.0", []), RuntimeError)
                worker.assert_not_called()
        with patch.dict("os.environ", {"NEBIUS_API_KEY": "fixture-key-not-real"}), \
                patch("tracedesk.core.subprocess.run", return_value=subprocess.CompletedProcess(
                    [], 1, stdout=b"fixture-private-marker", stderr=b"fixture-private-marker")):
            try:
                answer("Port?", "RelayGate", "2.0", [])
            except RuntimeError as exc:
                assert "fixture-private-marker" not in str(exc) and "fixture-key" not in str(exc)
            else:
                raise AssertionError("Unexpected worker failure must be sanitized")
        store.clear()
        assert not Store(path).list("RelayGate", "2.0")
        for i in range(19):
            store.save("RelayGate", "2.0", f"saved {i}", quote, ["rg2-port"], True)
        def simultaneous_save(i):
            try:
                store.save("RelayGate", "2.0", f"concurrent {i}", quote, ["rg2-port"], True)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            saved = list(pool.map(simultaneous_save, range(8)))
        assert sum(saved) == 1 and len(store.list("RelayGate", "2.0")) == 20
        store.save("RelayGate", "2.0", "saved 0", quote, ["rg2-port"], True)
        assert len(store.list("RelayGate", "2.0")) == 20
    transport_checks(payload)
    print("PASS: offline quote/scope/storage checks and local HTTP auth/retry/redirect/errors/slow-drip deadline with worker termination. Live Nebius NOT RUN.")


if __name__ == "__main__":
    main()
