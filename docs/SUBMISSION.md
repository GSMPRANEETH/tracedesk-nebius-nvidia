# Nebius submission working copy

**Status: preparation only.** Copy only claims supported by the final functioning build. Replace runtime-pending wording only after a real verification. No public video or Devpost submission exists yet.

**Name:** TraceDesk

**Tagline:** Technical support answers with a source, a scope, and a human review.

**Track:** Best Apps and Agents.

## Inspiration

Support answers often depend on the product version. In Python queues, `join()` normally tracks completed work, while immediate shutdown can bypass that completion expectation. A plausible generic answer can therefore be wrong for the user's actual mode/release. We built a workbench where versions, source evidence, exact excerpts, and reviewed decisions stay inspectable.

The Python case is documented upstream and has a runnable local reproduction; the separate RelayGate example is fictional. Support-team value remains a hypothesis, without customer interviews or measured time savings.

## What it does

TraceDesk selects version-specific documentation, asks an NVIDIA model through Nebius Token Factory for a structured response, and requires authentic excerpts for every citation. Its Version lens compares supplied passages from two releases and downloads a Markdown brief without making a model call. Source links let the user check original context. The prompt requests abstention when evidence is absent. An operator can approve a source excerpt and save it to SQLite; later requests may include that memory only within the exact product/version scope.

The app demonstrates reviewed source prioritization, not model training. Quote validation proves exact passage membership; it cannot prove every generated assertion follows from the excerpt. Semantic evaluation remains required.

## How it is built

Python standard-library HTTP, SQLite, and urllib; browser-native HTML/CSS/JavaScript; an NVIDIA inference integration for Nebius Token Factory. No vector database or orchestration framework. API key stays server-side and provider redirects are refused to avoid forwarding credentials. Original summaries of official Python 3.12/3.13 queue documentation and synthetic RelayGate 1.0/2.0 runbooks provide reproducible version-sensitive cases without private data. Actual provider execution remains pending account access.

## Challenges and lessons

A small prototype still needs trust boundaries: scope validation, unsupported citation rejection, explicit approval, real provider errors, and concurrency-safe storage. Concurrent-save testing reproduced a correction-cap race; the storage transaction now makes the count check and write atomic. Adding a correction is not proof of better answers, so the evaluation compares the same model with memory enabled and disabled.

## What is verified

Local invariant, HTTP transport, and browser workflows pass. A local Python 3.14.4 reproduction observed immediate shutdown returning from `join()` without processing the queued job; this demonstrates the developer problem, not Nebius execution. The 24-case synthetic/public-document evaluation is prepared. Live provider execution and semantic evaluation remain pending account access. Do not remove this disclosure or call the project a functioning AI demo until those gates pass.

## Next steps

Run the real-model evaluation and manually inspect evidence support. If memory adds no value on this small runbook, retain the simpler cited-answer flow and report the result. Any later real-user/hosted version needs permissioned data, isolated workspaces, budget controls, and a new release review.

## Tools / Built With

Python, SQLite, JavaScript, HTML, CSS, NVIDIA Nemotron, Nebius Token Factory. Only include the exact model after a successful runtime test. Playwright is used for optional local UI QA, not inference. Codex assisted development and testing; all competition disclosures should follow the final rules/form.

## Video storyboard — target 2 minutes 45 seconds

| Time | Show | Narration purpose |
|---|---|---|
| 0:00–0:20 | Python version lens and local queue reproduction | Explain a concrete completion-accounting support risk |
| 0:20–0:55 | Actual model answer, exact excerpt, upstream source | Show genuine NVIDIA-on-Nebius output and runtime metadata |
| 0:55–1:20 | Unsupported pricing question | Show observed abstention, or honestly report a failure |
| 1:20–1:55 | Review an excerpt, save, reload, rerun | Demonstrate persistence/scope; no weight-update claim |
| 1:55–2:25 | Actual evaluation result and version switch | Give real sample count, failures, and observed effect |
| 2:25–2:45 | Architecture and limitations | State remote inference, curated public/synthetic scope, and next step |

Do not use a transport-test fixture in the video. A recording of the missing-key screen may document build status but does not meet a working-AI demonstration requirement. Do not invent provider feedback, a model score, or a demo URL.
