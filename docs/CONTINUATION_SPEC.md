CONTINUATION MISSION — CLOSE ACCEPTANCE GAPS AND FINISH THE PRODUCT

Continue the existing implementation in:
[https://github.com/Kerim-Sabic/Gigahack](https://github.com/Kerim-Sabic/Gigahack)

This is a new continuation of the completed first build. Resume implementation now.

Do not restart, re-scaffold, discard functioning features or repeat completed architecture work.

Preserve the original product requirements and integrate the judging, engineering, branding, UI/UX, PDF and optional Laya requirements below.

Target:
NVIDIA RTX 3070 Ti Laptop GPU
8 GB VRAM
24 GB system RAM

Use the configured Astra model at medium effort.

1. START FROM THE ACTUAL HANDOFF

The supplied handoff reports:

- Branch: main.
- Remote checkpoint:
  0363960d8f41ed4806cc0f956f67aa632288c4e1
- Application implementation checkpoint:
  fc2cdd949c4071eb9a54d7760d1fb1c90c5a8a65
- The final checkpoint updated verification notes.
- 80 backend tests and 6 frontend tests passed.
- GitHub CI passed, reported run 36174094193.
- Real synthetic workflow passed through local ASR, extraction, evidence review, approved minutes, PDF/JSON and Mailpit.
- Complete Linux isolated workflow and service cleanup passed.
- Model/dependency pins, provenance and native-file integrity checks are implemented.

Acceptance remains incomplete:

- T01: date-correction failure.
- T10: missing-unit failure.
- Fixed-corpus text evaluation: 23 pass, 2 fail, 5 outside that text run.
- T22 stateful overlap/replay and the T26 silence branch were tested separately.
- Development hardware was RTX 5080, not the target laptop.
- Shared total GPU readings around 9.2–9.8 GiB do not establish isolated model use or compatibility with an 8 GB laptop.
- Difficult multilingual audio, long meetings, native-language review, physical microphone faults and sustained target performance remain unqualified.
- Windows host egress qualification remains open.
- Some settings/templates, accessibility, recovery and other requirements remain incomplete in the matrix.
- The current standalone Windows offline kit was not refreshed.
- Automatic approval review rejected the hardlinked-kit action with “blocked by policy.”
- A separate copy exceeded available space while preserving the required 5 GiB working reserve.
- The older prepared kit does not contain all current changes.

Treat these as the supplied checkpoint, not fresh verification.

First inspect the current remote state, working tree, AGENTS.md, STATUS.md, REQUIREMENTS\_MATRIX.md, TEST\_RESULTS.md, model manifests and handoff.

Do not reset to the cited commit if newer legitimate work exists. Preserve current work and establish the actual starting revision.

Do not assume the old absolute checkout path, prepared assets or hardware are accessible in the current environment.

2. THE OFFICIAL RUBRIC GOVERNS PRIORITY

SECURITY & ARCHITECTURE — 20%, INCLUDING DISQUALIFICATION

Any external API call at runtime, including cloud ASR or cloud LLM, disqualifies the submission.

Audio and transcripts must remain exclusively within the internal boundary. The architecture must be reproducible on the reference hardware.

LINGUISTIC ACCURACY — 30%

Evaluate abrupt Romanian/Russian/English code-switching, hallucination, medical terminology and consequential transcription errors.

OUTPUT QUALITY & STRUCTURE — 30%

Extract actual decisions and action items. Produce usable minutes without broad manual rewriting. Identify owners and deadlines correctly.

UX — 10%

Minimize meeting-end-to-email time, simplify upload/recording and minimize necessary intervention.

PRESENTATION — 10%

Clearly explain the technical and medical context and demonstrate the real workflow convincingly.

Implementation priority:
P0: Disqualification risks and broken mandatory behavior.
P1: T01/T10 and other consequential linguistic/output errors.
P2: Target-resource qualification and reproducible deployment.
P3: Complete remaining functional and usability requirements.
P4: Branding, visual refinement, document quality and presentation.
P5: Optional model experiments.

Accessibility and usable interaction belong throughout implementation. Later priority does not make required branding, UX or PDF work optional.

Do not claim perfection, clinical suitability, maximum marks or guaranteed victory.

3. REPRODUCE THE FAILURES BEFORE CHANGING THEM

Stop only application-owned services as required by the existing evaluation workflow. Never kill unrelated processes.

Use the existing commands and scripts; inspect them before execution:

python -m scripts.mom test
python -m ruff check .
npm test --prefix apps/web
npm run build --prefix apps/web
python -m tests.browser\_fixture
python -m scripts.evaluate\_text
python -m scripts.evaluate\_silence

Confirm the current commands and prerequisites against the repository. Do not blindly recreate environments or redownload verified assets.

Run the relevant baseline once and preserve:

- Tested commit.
- Model/runtime/config revisions.
- Inputs.
- Raw model outputs.
- Parsed candidates.
- Validation results.
- Reconciled state.
- Evaluator failures.

Do not fix a failure by weakening the assertion, changing gold labels to fit the output, excluding the case or hardcoding its answer.

If the evaluator is genuinely defective, demonstrate that independently and preserve the intended semantic requirement.

4. FIX T01 AT THE CORRECT LAYER

T01 concerns a proposed Monday maintenance date corrected to Wednesday and then confirmed.

Inspect the full chain:

- Meeting date and timezone supplied to extraction.
- Recognition/extraction of the correction.
- Raw and normalized temporal expressions.
- Subject association.
- Confirmation scope.
- Event ordering.
- Reducer behavior.
- Final projection.

Identify whether the defect is in prompting, schema, temporal normalization, reconciliation, reduction or evaluation.

Implement a general correction rule supported by evidence.

Do not special-case fixture IDs, names, dates or exact wording.

Add variations covering:

- Different weekdays and dates.
- Different meeting dates.
- Romanian and Russian phrasing.
- Mixed-language corrections.
- A rejected correction.
- A later tentative suggestion.
- A date correction separated from the original proposal by several turns.
- An owner-only amendment that must preserve the date.
- Ambiguous expressions that must remain unresolved.

Keep explicit source evidence for the final date and the superseded proposal.

5. FIX T10 WITHOUT LOSING UNITS OR SCOPE

T10 concerns a quantity corrected from 20 to 25 beds for Ward A.

Trace where the unit is lost:

- Candidate extraction.
- Schema parsing.
- Normalization.
- Event payload.
- State projection.
- Document rendering.
- Evaluation.

Preserve quantity as a structured concept:

- Value.
- Unit.
- Subject/scope.
- Raw expression.
- Supporting evidence.
- Uncertainty when applicable.

Do not infer a unit that was never stated.

Add variations with different quantities, wards, currencies and noninterchangeable units. Verify that quantities belonging to different subjects are not treated as contradictions.

Test that a discussion of a quantity does not automatically create a procurement or clinical action.

Verify the correct result in the actual UI, JSON and PDF—not only in an isolated helper test.

6. CLOSE SEMANTIC ACCEPTANCE HONESTLY

Rerun the full text suite after the fixes and inspect regressions.

Preserve all 30 specifications. Classify each as:

- Text-model.
- Stateful workflow.
- Audio-required.
- Human-review-dependent.

The previous five out-of-scope text cases must not disappear from the overall acceptance report.

Retain separate evidence for T22 and T26. Passing silence does not establish correct behavior on music, overlap or ambiguous numbers.

Add held-out variations not used to tune the fixes. Record all attempts rather than presenting only a favorable generation.

Measure:

- Decision/action precision and recall.
- Correct final state.
- Owner/deadline correctness.
- Quantity/unit correctness.
- Unsupported statements.
- Evidence validity.
- Abstention/unresolved rate.
- Required human corrections.

Do not obtain apparent precision by discarding difficult actions or returning everything unresolved.

7. QUALIFY MULTILINGUAL AND LONG-MEETING BEHAVIOR

The successful synthetic English workflow is a valuable integration result. It is not evidence of difficult Romanian/Russian/English meeting accuracy.

Create a versioned evaluation set covering:

- Each language separately.
- Abrupt switches between turns.
- Switching inside sentences.
- Medical English embedded in Romanian/Russian speech.
- Unfamiliar names.
- Similar-sounding names.
- Negation.
- Dates, decimals and units.
- Quiet/distant speech.
- Overlap.
- Silence and music.
- Long-distance references and late corrections.

Prefer human-recorded synthetic-content meetings when available. Document limitations of synthetic speech or public licensed audio.

Keep development and held-out recordings separate.

Measure WER alongside critical term/name/number/negation errors. Do not normalize away important distinctions.

Test long-window reconciliation with:

- A commitment early in the meeting.
- Unrelated intervening discussion.
- A late amendment.
- Repeated topic names.
- Different subjects with similar wording.

Inspect the final decision and evidence chain.

Do not claim medical acceptability or native-language validation without appropriate assessment. If human evaluation is unavailable, provide the evaluation materials and clearly mark that gate open.

8. RESOLVE THE MEMORY QUESTION WITHOUT MISLEADING MEASUREMENTS

The development RTX 5080 measurements do not prove that the app fits or fails on the RTX 3070 Ti Laptop.

Separate:

- Total device memory.
- Idle desktop/background use.
- Application-process memory where measurable.
- Model/runtime allocations.
- Peak memory during loading and inference.

If a measurement is unavailable, state that explicitly. A simple idle subtraction is only an approximation, not authoritative process attribution.

Inspect:

- Simultaneous model residency.
- Orphaned subprocesses.
- ASR batch/window sizes.
- LLM context and generation slots.
- KV/runtime buffers.
- Browser/PDF processes.
- Host-memory duplication.
- Device selection.

Enforce one GPU model process at a time.

Do not assume an allocator cap on a larger GPU reproduces the target laptop. It is only an additional stress test.

Preserve accuracy when reducing memory. Do not silently truncate prompts or omit transcript windows.

If target hardware is accessible, execute real qualification there. If it is not, finish the code and produce exact target commands while leaving target fit, thermals and latency unverified.

Use the existing qualify-target command and improve it where needed rather than creating competing qualification systems.

9. FINISH THE REMAINING REQUIREMENTS MATRIX

Inspect all existing requirement rows and close each independently achievable gap.

Specifically audit:

- Full queue/crash recovery.
- Long-transcript navigation.
- Re-extraction after transcript correction.
- Stale approval handling through the browser.
- Settings and template workflows.
- Recipient-group selection and frozen recipient display.
- Upload/render/SSE security fault cases.
- Retention behavior and backup restoration.
- Physical versus synthetic microphone qualification.
- Optional model availability reporting.
- Accessibility and localization completeness.

Do not mark an entire requirement verified because one subcase passed.

Reconcile stale test counts, commit references and timings in the documentation. Preserve historical results with their revisions; distinguish them from current results.

Existing passing features are regression requirements. Do not weaken their security or behavior during redesign.

10. RESOLVE PACKAGING THROUGH A PERMITTED, NONDESTRUCTIVE PATH

Respect the prior automatic approval rejection.

Do not repeat the rejected hardlink action through another tool, rename it, or replace it with an equivalent link-based workaround intended to bypass the rejection.

Do not delete existing data, lower the required working reserve or mutate the previously tested kit just to claim completion.

Inspect the current packaging code, available disk space and permitted destinations.

Possible legitimate approaches:

- A normal standalone copy on an explicitly available destination with sufficient space.
- A small versioned application bundle plus documented reuse/import of already prepared assets, validating all revisions and hashes.
- A clearly labeled update package for a known compatible prepared installation, with compatibility checks and recovery instructions.

Do not call an update or asset-reuse package a standalone offline kit.

Do not assume compression will create sufficient space; measure projected peak space, including temporary files and installation.

Preserve:

- Integrity checks.
- Model/native-tool provenance.
- Dependency pins.
- License notices.
- Clean first-run state.
- Exclusion of accounts, recordings and secrets.

Test the chosen delivery method from a fresh directory with the final application revision.

If a full standalone kit genuinely requires additional storage or approval, document that exact dependency and complete all other work. Never claim the old kit contains the new release.

11. PRESERVE AND EXTEND OFFLINE SECURITY EVIDENCE

Keep the successful Linux namespace rehearsal as evidence for its actual scope.

It does not establish Windows host isolation or a LAN-client deployment.

Audit runtime:

- External inference.
- Downloads.
- Telemetry.
- Updates.
- Remote assets.
- External authentication.
- Email relay.
- PDF fetching.

Missing assets must fail locally with no cloud fallback.

Test the final changed application after UI, branding and rendering assets are integrated, because those changes can introduce external dependencies.

Use the existing complete isolated-app qualification where applicable:
python -m scripts.qualify\_isolated\_app --path /path/to/synthetic.wav

Do not alter a shared Work host’s global firewall. Provide a scoped, reversible Windows/WSL target procedure.

If claiming LAN operation, test the actual local client path, authorization and microphone secure-context requirements separately from localhost-only operation.

Report external attempts, observed connections, coverage, interval and monitor health. Missing observation is “Not measured,” not zero.

12. KEEP ARCHITECTURE REVIEWABLE AND CORRECT

Preserve React/FastAPI/SQLite and the existing working boundaries unless a concrete defect justifies change.

Keep domain logic independent of HTTP, database and model runtimes.

Maintain:

- Strict contracts.
- Field-level evidence.
- Immutable accepted history.
- Rebuildable projections.
- Version-checked edits.
- Separate approval and delivery.
- Durable outbox.
- Explicit uncertainty.
- Source chronology independent of ingestion order.
- GPU subprocess ownership and cleanup.

Use short transactions. Do not hold them across inference, rendering or SMTP.

Test stale-worker fencing, duplicate requests, failed atomic changes, cross-meeting references and artifact/database crash recovery.

Do not add architectural layers merely to appear sophisticated.

Reviewers should find understandable responsibilities and enforced invariants, not claims that the code is “world-class.”

13. CREATE THE FINAL PRODUCT NAME AND IDENTITY

“Secure MOM” remains the challenge title, not the intended final app name.

If no final identity exists, develop 8–12 candidates and select one based on:

- Professional credibility.
- Pronunciation in Romanian/Russian/English.
- Memorability.
- Relevant meaning.
- Visual identity.
- Obvious conflict screening.

Document preliminary screening without claiming trademark clearance.

Choose autonomously. Keep the repository named Gigahack.

If image generation is available, use it to explore original logo concepts and inspect the results.

Deliver:

- Symbol.
- Wordmark/lockup.
- Favicon.
- Monochrome variants.
- Transparent raster assets.
- A true simplified SVG where feasible.

Verify small-size and print legibility.

Avoid generic shield/microphone/medical-cross combinations and implied certification.

If image generation is unavailable, create a considered original typographic/geometric identity and document the limitation.

Centralize the display name and update UI, PDF, email, browser metadata and documentation consistently without disruptive internal migrations.

14. COMPLETE AND REFINE THE UI/UX

Inspect the real running app before redesigning it.

Choose one coherent visual system:

- Calm, precise and contemporary.
- Strong typography.
- Deliberate density.
- Restrained color.
- Clear hierarchy.
- Distinctive evidence and change-history treatment.

Avoid meaningless metrics, decorative charts, random gradients and generic AI-dashboard clutter.

Design from secretary, physician, executive and administrator perspectives. Label these as internal heuristic reviews, not actual clinical validation.

The core flow must be simple:
Create → Record/upload → Process → Review → Preview → Approve → Send.

The review workspace must make it easy to:

- Identify the final decision.
- Inspect changed fields.
- Select separate owner/deadline evidence.
- Play contextual audio.
- Resolve uncertainty.
- Distinguish meeting statements from later human amendments.

Clearly distinguish:
Confirmed in meeting
Reviewed
Approved
SMTP accepted
Delivery uncertain

Keep technical configuration outside the ordinary path.

Finish settings/templates and useful empty/loading/error states. Preserve user input during recoverable failures.

Support English/Romanian/Russian UI, locally bundled fonts, keyboard navigation, visible focus, reduced motion and 200% zoom.

Native language review remains a separate gate when qualified reviewers are unavailable.

15. MAKE NOTIFICATIONS AND RECOVERY EXCELLENT

Implement a coherent policy:

- Inline field errors.
- Persistent banners for consequential failures.
- Durable activity history.
- Brief nonblocking success feedback.
- Confirmation only for consequential actions.

Cover recording loss, unsaved audio, connection failure, disk pressure, worker failure, edit conflicts, stale approval and uncertain SMTP delivery.

Explain:

- What happened.
- Whether data is safe.
- What to do next.

Prevent notification storms and duplicate alerts.

Never expose sensitive meeting content in desktop notifications.

Never show fabricated percentages, unjustified confidence or success before authoritative acknowledgement.

16. UPGRADE PDF QUALITY BEYOND FILE-EXISTS TESTS

The existing real PDF generation is the baseline. Inspect the actual documents visually.

Create refined templates containing:

- Meeting metadata.
- Participants.
- Decisions.
- Action table.
- Changed/rejected items.
- Unresolved matters.
- Version and approval details.
- Page numbers.
- Appropriate evidence references.

Test short, long, multilingual and no-action meetings.

Verify:

- Page breaks.
- Repeated table headers.
- Long names and rows.
- No clipping.
- No missing characters.
- Readable text.
- Selectable content.
- Local/embedded fonts.
- Draft/approved/superseded distinction.

Render representative PDFs and inspect the pages. Extract text to check completeness.

Keep UI, PDF, JSON and email consistent with the exact snapshot.

Do not introduce remote rendering assets.

17. OPTIONAL MODELS MUST EARN THEIR PLACE

Keep optional NeMo/Parakeet, pyannote and Laya work separate from core acceptance.

Report unavailable gated assets honestly.

For Laya evaluate:
[https://github.com/NandhaKishorM/laya](https://github.com/NandhaKishorM/laya)
[https://huggingface.co/convaiinnovations/laya-multilingual](https://huggingface.co/convaiinnovations/laya-multilingual)

Start behind a disabled feature flag in shadow mode.

Test short-window speech-act classification and disagreement signals on labeled multilingual examples.

Measure accuracy, missed decisions, false review flags, calibration, latency and memory.

Do not let Laya approve, choose recipients, suppress transcript coverage or resolve critical uncertainty.

Enable an optional component only when measured benefits justify it. Do not delay the finished product for an unproven enhancement.

18. VERIFY THE FINAL CHANGES AND PREPARE THE DEMO

After meaningful changes:

- Run affected tests immediately.
- Fix regressions.
- Update notes.
- Commit coherent progress.

Before final handoff:

- Run the complete relevant backend/frontend/CI checks.
- Rerun actual model evaluation.
- Exercise the real browser workflow.
- Render and inspect PDFs.
- Confirm Mailpit receipt.
- Verify service cleanup.
- Rehearse recovery.
- Test the final release/install method.
- Repeat offline qualification for the changed runtime.

Do not count previous revision results as verification of changed code.

Prepare a demonstration showing:

- Mixed-language input.
- Deadline and owner correction.
- Rejected proposal.
- Genuine unresolved issue.
- Field-specific evidence.
- Final minutes.
- Approval and local delivery.
- Honest offline evidence.

Do not fabricate model disagreements or present prepared output as live processing.

19. REPOSITORY, EVIDENCE AND HANDOFF

Maintain accurate:

- STATUS and requirement matrix.
- Judging scorecard.
- Architecture and decisions.
- Actual test/model-evaluation results.
- Resource/performance results.
- Offline scope.
- Packaging/install instructions.
- Brand/design/UX/notification/PDF notes.
- Reviewer guide.
- Demo and recovery instructions.

Record tested commits, configurations and environments.

Use synthetic public artifacts only. Do not commit secrets, recordings, databases or model weights.

Push coherent improvements under the existing repository rules. Never force-push or discard unrelated work. Verify the remote commit and the CI result for that revision.

Final handoff must state:

- What changed since 0363960.
- Whether T01 and T10 now pass, with evidence.
- The status of every remaining acceptance gate.
- The chosen product name and branding assets.
- Real UI/PDF verification.
- Exact startup and qualification commands.
- Current install/package type and limitations.
- Work/development results versus target-laptop results.
- Remaining external prerequisites.
- Verified remote commit and CI run.

Do not claim the app is fully qualified if target hardware, difficult audio or required human validation remains untested.

Complete all independently achievable work instead of stopping because one external prerequisite is unavailable.

START NOW:
Read the current checkpoint and reproduce T01/T10. Fix their root causes, preserve the working baseline, then continue through target readiness, remaining requirements, product polish, packaging and final verification.