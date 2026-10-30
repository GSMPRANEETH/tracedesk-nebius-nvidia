# Release checklist — 30 October 2026

This is an engineering checklist, not legal clearance. The current deliverable is source for a **local, single-operator public/synthetic-document demo**, not a hosted multi-user service.

## Verified locally

- Core scope/approval/citation/exact-quote/persistence/error checks pass, including concurrent correction-cap enforcement. Local HTTP transport tests cover credential headers, bounded retries, redirect refusal, and sanitized failures; they are not live-model evaluation.
- Linux and native Windows Python pass the provider-worker regression: slow-drip responses cannot evade the 55-second communication budget; timeout kills and reaps the worker. Process creation/cleanup overhead and provider-side charges are outside that guarantee.
- Browser checks pass at 1440, 768, and 390 pixels: no horizontal overflow; source version change; reviewed save/reload/delete; invalid quote rejection; honest missing-runtime error.
- Host, same-origin, CSRF, explicit static-file routes, text rendering, input bounds, connection timeout, and serialized inference are implemented.
- Browser asset requests are same-origin; system fonts; no analytics/replay/email/payment SDKs in this app.
- The version-lens comparison, Markdown download, and target-version question handoff work on original summaries of official Python documentation. A queue reproduction actually runs on the local Python interpreter without inference.
- Inputs are original public-document summaries plus authored synthetic passages, with source provenance. No private email, employer record, credential, or organizer dataset belongs in a release.

## Remaining gates before an eligible competition entry

- [ ] Confirm entrant's actual eligibility against the [official rules](https://nebiusglobalaihackathon.devpost.com/rules).
- [ ] Confirm Nebius sign-in, credit balance, selected NVIDIA model access, JSON-mode behavior, and a real successful inference request.
- [ ] Run development evaluation, freeze decisions, run held-out evaluation, and manually check factual support/abstention. Keep failures visible.
- [ ] Verify clean setup on another machine and judge access through **23 December 2026**. A transient credit balance is not an availability commitment.
- [x] Publish the source repository with a visible license and stable revision; release only this project's allowlisted files. Public v0.2.0 is verified; later fixes must be packaged and rechecked before a new release.
- [ ] Record a public YouTube video under three minutes showing actual model execution, not a UI fixture or screenshot montage.
- [ ] Finish the Devpost description, tools/integration explanation, demo/test-build URL, and observed provider feedback.
- [ ] Submit before the official deadline and preserve the confirmation. A local build, public repo, or draft form is not a submitted entry.

## Public hosting is a separate release

The current stdlib server is deliberately loopback-only. Do not rehost it unchanged. A hosted product would need real authentication/tenant isolation, request/budget controls, appropriate secret management, vendor/retention verification, and a refreshed audit of actual audience, jurisdictions, data flow, and deployment settings. No universal age gate or compliance promise is implied.

Six-area audit summary for this local code: no child-directed workflow was found; browser remote fonts/resources absent; analytics/replay absent; marketing email absent; subscriptions/renewals absent; public content sharing/uploads absent. These observations do not prove future-hosting compliance. Operator location, actual audience/markets, vendor contract/settings, and operational controls still need confirmation for any hosted launch. Remote inference is a real third-party disclosure even though browser assets are local.

## Status wording

Use “local workflow tested; live inference pending” until a real provider call succeeds. Use “software tests passed” separately from “model evaluation passed.” Human-reviewed source prioritization is not autonomous fine-tuning or demonstrated learning. Do not claim a prize, submission, uptime, privacy certification, or measured time savings without evidence.
