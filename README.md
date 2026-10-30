# TraceDesk

**A small technical-support workbench with scoped evidence and human-reviewed memory.** Built for the Nebius × NVIDIA Global AI Hackathon, Best Apps and Agents track.

TraceDesk answers from a bounded fictional runbook using an NVIDIA model through Nebius Token Factory. Every supported response must cite valid passage IDs for the selected product version. An operator can approve an exact source excerpt for future questions; the app keeps it in SQLite. Model weights do not change.

**Current verification boundary:** local storage, validation, HTTP protections, responsive UI, and error paths have been tested. **Live Nebius inference and semantic answer quality have not yet been verified** because an API key is not configured in the build environment. No hosted service, video submission, acceptance receipt, or prize is claimed. The application never substitutes prerecorded answers for failed inference.

## Run locally

Requires Python **3.10+**, with no production dependencies. Open a terminal in this directory:

```bash
python3 -m tracedesk.server
```

Open **http://127.0.0.1:8765**. Source browsing and reviewed-memory save/list/clear work without a provider key. The server intentionally binds only to loopback. On Windows, `py -m tracedesk.server` can replace `python3`.

To enable actual inference without writing a key to disk or command history:

```bash
python3 -m tracedesk.server --prompt-key
```

Enter your Nebius API key at the hidden terminal prompt. It is kept in that process's environment, never sent to the browser or saved to the correction database. Alternatively, set `NEBIUS_API_KEY` in your process environment. The `.env.example` documents variable names; the app does not automatically load `.env` files.

Default model: `nvidia/Nemotron-3_5-Lightning`. Confirm exact current availability in your Nebius account. Set `NEBIUS_MODEL` to another accessible NVIDIA model identifier if needed. The app uses the [official OpenAI-compatible endpoint](https://docs.tokenfactory.nebius.com/quickstart), `https://api.tokenfactory.nebius.com/v1/chat/completions`. JSON-mode support and access need a real request; a configured key alone is not a connectivity pass.

## Try the workflow

1. Select RelayGate **1.0**, ask its default port, and inspect the returned `rg1-port` citation.
2. Switch to **2.0** and ask the same question. The fictional default is different; only version 2.0 evidence is sent.
3. Ask about subscription prices or refunds. The runbook has no such facts; the model is instructed to abstain. Its actual behavior must be checked during live evaluation.
4. Select a source passage, supply a question, and explicitly review/approve the excerpt. Save it, reload, and inspect Reviewed memory.
5. Turn memory on/off and compare actual answers. Clear memory when finished.

Saving free-form unsupported advice is rejected. Excerpts prioritize existing source evidence; they do not add new knowledge, establish truth by themselves, or demonstrate model training. A stored correction may not improve an answer the base runbook already supports.

## Architecture

```mermaid
flowchart LR
    User[Support engineer] --> UI[Browser workbench]
    UI -->|same-origin JSON + CSRF token| Server[Loopback Python server]
    Runbook[16 synthetic passages\nRelayGate 1.0 / 2.0] --> Scope[Exact product/version scope]
    DB[(Local SQLite\nreviewed source excerpts)] --> Scope
    Server --> Scope
    Scope -->|question + scoped sources\noptional approved memory| Model[NVIDIA model\nNebius Token Factory]
    Model --> Validate[Validate JSON, citations\nand correction references]
    Validate --> UI
    UI -->|explicit review + source quote| DB
```

One Python process; standard-library HTTP, SQLite, and HTTPS client; browser-native HTML/CSS/JavaScript. No framework, vector database, agent runtime, analytics, remote font, or cloud database. All source content is synthetic and authored for this demonstration. It has no connection to an employer, real product, or customer incident.

## Checks and evaluation

```bash
python3 self_check.py
python3 -m compileall -q tracedesk evaluate.py
```

The assert-based check covers scope isolation, invalid citations, approval, unsupported corrections, idempotent saves, persistence, concurrent cap enforcement, malformed provider responses, and missing-key errors. It uses explicit fake provider boundaries for software checks and **does not measure model accuracy**.

Optional browser QA runs in a disposable environment; Playwright is not a production dependency:

```bash
uv run --with playwright python3 qa/browser_check.py
```

Install a compatible Playwright Chromium browser if none is present, or set `CHROMIUM_EXECUTABLE` to an existing compatible Chromium executable. QA captures go outside this source directory to `../artifacts/`. It tests real local storage and errors; one explicitly labeled response fixture tests UI rendering and escaping only. No test fixture is a model result.

For a live connection check, set `NEBIUS_API_KEY`, then:

```bash
python3 evaluate.py --split dev --memory off --limit 1
python3 evaluate.py --split dev --memory both
python3 evaluate.py --split heldout --memory both
```

The final command should follow development decisions, without further tuning against held-out results. There are 20 synthetic questions: 8 supported, 4 unsupported, 4 paraphrases, 4 version-sensitive. Reports are written atomically under `.local/`, with source fingerprint, actual provider output, latency, usage, and regression flags. The model never receives the reference statuses, phrases, or citation expectations. A provider failure stops the run to avoid further spend.

The phrase/citation checks are **heuristics requiring human semantic review**. They may flag a valid paraphrase or miss an unsupported claim. Report manually reviewed numerators/denominators, not an inflated “accuracy” score. Twenty synthetic cases do not establish real-world reliability. No live scores have been produced yet.

## Data and operational limits

- Intended for one operator on their own machine. Its SQLite store and CSRF token are shared by browser tabs in that local workspace. Do not expose the server with a tunnel, reverse proxy, or external bind.
- Question/scoped runbook/approved excerpts are sent to Nebius when inference is requested. Use synthetic content only. This is not an offline or zero-retention product; organization/vendor settings are unverified.
- API secrets remain server-side. Access logging is suppressed; no browser tracking/cookies/third-party assets are used by this code.
- Questions: 2 KB UTF-8; runbook: 20 passages / 30 KB; approved memories: 20 per version. Full scoped context is sent; ranked retrieval is an upgrade only if this grows.
- Corrections are durable in `.local/corrections.sqlite3`; “Clear all memory” deletes local rows. That action makes no claim about provider retention.
- One paid request runs at a time; a request retries once for transient provider failure. This does not establish a monthly spending cap. Use provider-side account limits and credits.
- Valid citation IDs prove structural scope, not that a generated sentence follows from them. Sources and questions are untrusted; no tools or autonomous actions are available.

Read [the release checklist](docs/RELEASE-CHECKLIST.md) and [submission materials](docs/SUBMISSION.md). MIT license applies to this source code and authored synthetic samples; NVIDIA/model/provider terms remain separate.
