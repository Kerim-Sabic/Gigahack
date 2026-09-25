# Verification results

Environment: Windows development host, Python 3.12.10, two RTX 5080 16 GB, 128 GiB RAM.

| Check | Observed result |
|---|---|
| Backend/domain/recovery tests | 38 passed; 0 skipped; one Starlette httpx deprecation warning |
| Frontend component/capture queue tests | 5 passed |
| Python lint | Passed |
| Frontend strict TypeScript + production build | Passed |
| OpenAPI type generation | Passed with TypeScript 5.9.3 |
| Real Whisper GPU smoke | Passed on synthetic English, original language retained |
| Real Qwen GPU smoke | Initial semantic/citation failure; revised prompt produces supported expected smoke result |
| Real browser upload-to-Mailpit | Passed; no browser page errors; PDF header validated |
| Browser dimensions | 1366×768 and 1920×1080 screenshots; 683px layout overflow check |
| Browser keyboard | Focus moves from skip link to semantic control |
| 200% browser zoom | Not yet run; small viewport alone is not a zoom test |
| Synthetic microphone | 305-second real-time browser capture, pause/resume, flush and abrupt-browser-loss recovery passed; physical device not measured |
| Backup/restore | Test restores stopped database and acknowledged audio |
| SMTP timeout | Test leaves uncertain state and does not retry automatically |
| 30 actual extraction cases | 28 structurally valid outputs; 2 validation failures; semantic gate NOT passed |
| Target 8 GB GPU/24 GB RAM | NOT RUN — TARGET MACHINE REQUIRED |
| Human RO/RU/EN and code-switch accuracy | Not measured |
| Scoped WSL namespace probe | IPv4/IPv6 external route attempts fail ENETUNREACH; real Whisper/Qwen worker completed; full application boundary unverified |
| Offline kit | Preparation and no-index wheel installation passed; disconnected run not verified |
| GPU/host sampling | Actual samples recorded; total-host RAM gate failed on shared dev workstation |

Local evidence (ignored, synthetic): `.runtime/proofs/browser-e2e.json`, review/minutes screenshots,
`.runtime/smoke/`, `.runtime/jobs/*/*-receipt.json`, `.runtime/evaluations/text-results.json`.
Public reports must remove absolute local paths and raw model response identifiers.

Fresh prepared-kit environment (new database/account, packaged browser/models/tools) completed real
upload-to-PDF-to-Mailpit in 25.168 seconds, zero page errors. Networking was not disabled.

Linux isolated real stages: Whisper 27.723 s, Qwen 22.977 s; peak total GPU 0 9769 MiB.
This exceeds the target total-VRAM budget and is not a target-laptop pass.

Operator recovery milestone: 44 backend tests, 5 frontend tests, lint/build pass. Expanded fixture
browser workflow 12.175 s with no page errors; metadata, account/grant and amendment-history assertions
pass. Internal SMTP TLS/authentication uses test doubles; real local Mailpit delivery passes.

## Current evidence/reconciliation milestone

63 backend tests passed on Windows using the documented CLI's repository-local temporary directory;
6 frontend tests, Python lint and strict production build passed. Direct pytest with the machine's
shared default temporary directory encountered access-denied errors; explicit --basetemp resolved it.
One Starlette test-client deprecation warning remains. Linux recovery subset: 14 passed.

Latest text run 1790358152930512100: 23 PASS / 2 FAIL / 5 NOT RUN. T01 retains the old date
because a correction was misclassified; T10 loses the unit. T08/T11/T26/T29 require actual audio,
T22 requires stateful integration. Development corpus tuning is not held-out accuracy. Subsequent
process-identity and canonical-dedup changes were unit tested, not a rerun of the entire model corpus.

Complete real Linux isolated app passed: 56.394 s browser flow, 84.589 s total, no page errors,
all services in one loopback-only namespace, IPv4/IPv6 ENETUNREACH before/after, cleanup list empty.
Linux FFmpeg 6.1.1-3ubuntu5 and Playwright 1.63.0 Chromium revision 1243 were prepared.
The original /tmp run directory vanished on WSL reboot; its complete console receipt was retained
locally. Future rehearsals use /var/tmp so database, screenshots and receipts survive that reboot.

Latest Linux fixture browser integration: 13.766 s, no page errors; metadata, account/grant, recipient
group edits, manual topic link, retained amendments, real PDF and Mailpit passed. RO/RU preference,
source preservation and localized recipient errors passed. This run uses explicit fixture inference.

Security/recovery follow-up: 72 backend tests passed. Denied admin cannot read ranges/evidence/search/history/exports/SSE; valid byte ranges work; expired/logout/revoked streams terminate; malformed uploads create no assets; paths remain server-owned; HTML escapes source content. Restore retains source, reviewed evidence, immutable approval and delivery deduplication. Corruption and nonempty destinations are refused before writing.
