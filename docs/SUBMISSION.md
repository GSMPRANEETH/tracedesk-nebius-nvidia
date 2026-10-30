# Nebius submission working copy

**Status: preparation only.** Copy only claims supported by the final functioning build. Replace runtime-pending wording only after a real verification. No public video or Devpost submission exists yet.

**Name:** TraceDesk  
**Tagline:** Technical support answers with a source, a scope, and a human review.  
**Track:** Best Apps and Agents.

## Inspiration

Support answers often depend on the product version. Repeating a plausible fix from the wrong release can be worse than admitting that the documentation is incomplete. We wanted a small workbench where evidence and reviewed decisions remain inspectable.

This is a product hypothesis illustrated with fictional data, not a claim based on customer interviews or measured support-team savings.

## What it does

TraceDesk selects a version-specific runbook, asks an NVIDIA model through Nebius Token Factory for a structured response, and validates passage IDs before displaying a supported answer. The prompt requests abstention when the runbook does not contain an answer. An operator can approve a source excerpt and save it to local SQLite memory. The next request can include those reviewed excerpts within the exact product/version scope.

The app currently demonstrates reviewed source prioritization. It does not train the model or add facts beyond its evidence. Citation validation is structural; semantic support requires evaluation.

## How it is built

Python standard-library HTTP, SQLite, and urllib; browser-native HTML/CSS/JavaScript; hosted NVIDIA inference on Nebius Token Factory. No vector database or orchestration framework. API key stays server-side. Synthetic RelayGate 1.0/2.0 runbooks make version-sensitive behavior reproducible without using private data.

## Challenges and lessons

A small prototype still needs trust boundaries: scope validation, unsupported citation rejection, explicit approval, real provider errors, and concurrency-safe storage. Concurrent-save testing reproduced a correction-cap race; the storage transaction now makes the count check and write atomic. Adding a correction is not proof of better answers, so the evaluation compares the same model with memory enabled and disabled.

## What is verified

Local invariant checks and browser workflows pass. Live provider execution and semantic evaluation remain pending until account credentials are available. Do not remove this disclosure or call the project a functioning AI demo until those gates pass.

## Next steps

Run the real-model evaluation and manually inspect evidence support. If memory adds no value on this small runbook, retain the simpler cited-answer flow and report the result. Any later real-user/hosted version needs permissioned data, isolated workspaces, budget controls, and a new release review.

## Tools / Built With

Python, SQLite, JavaScript, HTML, CSS, NVIDIA Nemotron, Nebius Token Factory. Only include the exact model after a successful runtime test. Playwright is used for optional local UI QA, not inference. Codex assisted development and testing; all competition disclosures should follow the final rules/form.

## Video storyboard — target 2 minutes 45 seconds

| Time | Show | Narration purpose |
|---|---|---|
| 0:00–0:20 | Workbench and two runbook versions | Explain a concrete wrong-version support risk |
| 0:20–0:55 | Real answer and source passage | Show actual NVIDIA-on-Nebius output and runtime metadata |
| 0:55–1:20 | Unsupported pricing question | Show observed abstention, or honestly report a failure |
| 1:20–1:55 | Review an excerpt, save, reload, rerun | Demonstrate persistence/scope; no weight-update claim |
| 1:55–2:25 | Actual evaluation result and version switch | Give real sample count, failures, and observed effect |
| 2:25–2:45 | Architecture and limitations | State remote inference, synthetic scope, and next step |

Do not use a transport-test fixture in the video. A recording of the missing-key screen may document build status but does not meet a working-AI demonstration requirement. Do not invent provider feedback, a model score, or a demo URL.
