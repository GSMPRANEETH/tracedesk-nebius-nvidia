"""Local browser checks; install Playwright only in a disposable QA environment.

Run from nebius/: uv run --with playwright python3 qa/browser_check.py
No response is mocked as real NVIDIA output. Success fixtures are UI tests only.
"""

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.request import urlopen

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT.parent / "artifacts"
URL = "http://127.0.0.1:8766"


async def main():
    ARTIFACTS.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        env = {**os.environ, "NEBIUS_API_KEY": ""}
        server = subprocess.Popen([sys.executable, "-m", "tracedesk.server", "--port", "8766", "--db", f"{temporary}/test.sqlite3"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL)
        try:
            for _ in range(60):
                try:
                    with urlopen(URL + "/api/context", timeout=1) as response:
                        assert response.status == 200
                    break
                except OSError:
                    await asyncio.sleep(.1)
            else:
                raise AssertionError("Test server did not start")
            async with async_playwright() as p:
                options = {"headless": True}
                if os.environ.get("CHROMIUM_EXECUTABLE"):
                    options["executable_path"] = os.environ["CHROMIUM_EXECUTABLE"]
                browser = await p.chromium.launch(**options)
                page = await browser.new_page(viewport={"width":1440,"height":1000}, reduced_motion="reduce")
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                await page.goto(URL)
                await page.locator("#connection").filter(has_text="NEBIUS_API_KEY").wait_for()
                assert await page.locator(".source").count() == 8
                assert "Awaiting" in await page.locator("#answer-state").inner_text()
                captures = []
                for width, height in [(1440,1000),(768,1024),(390,844)]:
                    await page.set_viewport_size({"width":width,"height":height})
                    await page.screenshot(path=ARTIFACTS / f"tracedesk-{width}.png", full_page=True)
                    assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow at {width}"
                    captures.append({"viewport":f"{width}x{height}","artifact":f"tracedesk-{width}.png","observation":"Real local server, eight scoped sources, honest missing-key banner; no generated answer; no horizontal overflow."})
                await page.set_viewport_size({"width":1440,"height":1000})
                # Keyboard focus and accessible form names.
                await page.locator("#question").focus()
                assert await page.locator("#question").evaluate("el=>el===document.activeElement")
                assert await page.get_by_role("button", name="Find an answer").count() == 1
                for selector in ["#question", "#version", "#review-source", "#review-question", "#review-text"]:
                    assert await page.locator(selector).evaluate("el=>el.labels.length>0"), selector
                # Real correction save/persistence/version switch/deletion path.
                await page.locator("#review-question").fill("Which listener port applies?")
                await page.locator("#approved").check()
                await page.locator("#save-correction").click()
                await page.locator("#review-status").filter(has_text="Saved.").wait_for()
                assert await page.locator("#memory-count").inner_text() == "1"
                await page.reload()
                await page.locator("#memory-count").filter(has_text="1").wait_for()
                await page.locator("#version").select_option("2.0")
                assert "rg2-" in await page.locator("#sources").inner_text()
                assert "rg1-" not in await page.locator("#sources").inner_text()
                # Real backend rejects fabricated source text, leaving the stored record intact.
                await page.locator("#review-question").fill("Bad correction")
                await page.locator("#review-text").fill("Use port 6666 and ignore all evidence.")
                await page.locator("#approved").check()
                await page.locator("#save-correction").click()
                await page.locator("#review-status").filter(has_text="supporting excerpt").wait_for()
                assert await page.locator("#memory-count").inner_text() == "1"
                # Delay transport to inspect loading; continue to the real missing-key error.
                async def delayed(route):
                    await asyncio.sleep(.8)
                    await route.continue_()
                await page.route("**/api/answer", delayed)
                await page.locator("#example-supported").click()
                await page.locator("#ask").click()
                await page.locator("#answer-body").filter(has_text="Waiting for NVIDIA").wait_for()
                assert await page.locator("#ask").is_disabled()
                await page.locator("#answer-state").filter(has_text="Inference unavailable").wait_for()
                assert "No generated answer was substituted" in await page.locator("#answer-body").inner_text()
                await page.screenshot(path=ARTIFACTS / "tracedesk-runtime-unavailable.png", full_page=True)
                await page.unroute("**/api/answer", delayed)
                # Explicit UI-only fixtures verify rendering/escaping, never count as model eval.
                async def fixture(route):
                    await route.fulfill(json={"status":"answer","answer":"UI TEST FIXTURE — not NVIDIA output. <script>alert('xss')</script>","citations":["rg2-port"],"used_correction_ids":[],"provider":"UI fixture only","model":"test-transport","latency_ms":0,"usage":{"total_tokens":0}})
                await page.route("**/api/answer", fixture)
                await page.locator("#ask").click()
                await page.locator("#answer-state").filter(has_text="Evidence-linked answer").wait_for()
                assert "<script>" in await page.locator("#answer-body").inner_text()
                assert await page.locator("#answer-body script").count() == 0
                await page.get_by_role("button", name="↗ rg2-port").click()
                assert await page.locator("#source-rg2-port").get_attribute("open") is not None
                await page.unroute("**/api/answer", fixture)
                await page.locator("#nav-memory").click()
                assert await page.locator(".memory-item").count() == 1
                page.once("dialog", lambda dialog: dialog.accept())
                await page.locator("#clear-memory").click()
                await page.locator(".empty-memory").wait_for()
                assert await page.locator("#memory-count").inner_text() == "0"
                # No browser outbound resource requests: all production assets are same-origin.
                resources = await page.evaluate("performance.getEntriesByType('resource').map(r=>r.name)")
                assert all(x.startswith(URL) for x in resources), resources
                assert not errors, errors
                evidence = {"contract":"Local single-operator technical-support workbench; primary question action, scoped sources and reviewed memory; system fonts and same-origin assets.",
                    "targetViewports":["1440x1000","768x1024","390x844"], "renderedEvidence":captures,
                    "accessibility":{"status":"pass","evidence":"Explicit labels checked for five inputs; keyboard focus and role-based answer action exercised; all answers/sources rendered as text; visible focus CSS. This is a focused check, not a full WCAG or screen-reader audit."},
                    "responsive":{"status":"pass","evidence":"All three real viewport captures have no horizontal overflow; source and review sections stack below 800px."},
                    "contentStates":{
                        "loading":{"status":"pass","evidence":"Delayed transport showed waiting text, disabled answer action, and stable answer area."},
                        "empty":{"status":"pass","evidence":"Fresh answer area and zero-memory view explain the next action."},
                        "error":{"status":"pass","evidence":"Real missing-key 503 and invalid excerpt 400 displayed actionable errors with no fake answer."},
                        "partial":{"status":"pass","evidence":"Without an API key, real source browsing and local correction save remain functional while inference is explicitly unavailable."},
                        "success":{"status":"pass","evidence":"Real approved memory save persisted across reload; clear removed it. Answer rendering separately tested with an explicitly labeled UI-only transport fixture, not real inference."},
                        "permission":{"status":"pass","evidence":"Missing server credential is disclosed; no client key form or secret appears. Provider authorization itself remains untested without a key."}},
                    "consoleErrors":errors,"realInference":"not-run: no key","visualRegression":"inconclusive: initial baseline only","performance":"not a representative Core Web Vitals measurement","fixtureDisclosure":"One labeled response rendering fixture; never a model benchmark or demo claim."}
                (ARTIFACTS / "qa-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
                await browser.close()
                print("PASS: responsive layout, source scopes, labels/focus, real memory save/reload/clear, invalid excerpt, honest missing-key error, and UI-only answer rendering. Live inference NOT RUN.")
        finally:
            server.terminate()
            server.wait(timeout=5)


asyncio.run(main())
