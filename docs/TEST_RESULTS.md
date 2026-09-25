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
