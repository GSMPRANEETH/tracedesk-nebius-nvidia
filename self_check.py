"""Offline invariant checks. Does not claim live model integration or answer quality."""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import tempfile
from unittest.mock import patch

from tracedesk.core import Store, answer, load_runbook, validate_response


def rejects(fn, error=ValueError):
    try:
        fn()
    except error:
        return
    raise AssertionError("Expected rejection")


def main():
    runbook = load_runbook()
    assert len(runbook) == 16
    evidence = [p for p in runbook if p["version"] == "2.0"]
    payload = dict(status="answer", answer="The default port is 9090.", citations=["rg2-port"], used_correction_ids=[])
    assert validate_response(payload, evidence, [])["status"] == "answer"
    rejects(lambda: validate_response({**payload, "citations": ["made-up"]}, evidence, []))
    rejects(lambda: validate_response({**payload, "citations": ["rg1-port"]}, evidence, []))
    rejects(lambda: validate_response({**payload, "citations": []}, evidence, []))
    rejects(lambda: validate_response({**payload, "used_correction_ids": ["mem-9"]}, evidence, []))
    rejects(lambda: validate_response({**payload, "status": "insufficient_evidence"}, evidence, []))
    quote = "RelayGate 2.0 listens on TCP port 9090 by default."
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
                '{"status":"answer","answer":"9090","citations":["rg2-port"]}'}}], "usage": [1]}):
            rejects(lambda: answer("Port?", "RelayGate", "2.0", []), RuntimeError)
        with patch("tracedesk.core._infer", side_effect=RuntimeError("Provider failed")):
            rejects(lambda: answer("Port?", "RelayGate", "2.0", []), RuntimeError)
        rejects(lambda: answer(" ", "RelayGate", "2.0", []))
        rejects(lambda: answer("é" * 1_001, "RelayGate", "2.0", []))
        rejects(lambda: answer("\ud800", "RelayGate", "2.0", []))
        rejects(lambda: answer("Port?", "RelayGate", "3.0", []))
        rejects(lambda: answer("Port?", "RelayGate", "2.0", [], use_memory="false"))
        with patch.dict("os.environ", {"NEBIUS_API_KEY": ""}):
            rejects(lambda: answer("Port?", "RelayGate", "2.0", []), RuntimeError)
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
    print("PASS: offline scope, evidence, approval, persistence, idempotency, response, and failure checks")


if __name__ == "__main__":
    main()
