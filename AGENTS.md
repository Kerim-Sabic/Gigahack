# Secure MOM engineering conventions

Read docs/STATUS.md, docs/REQUIREMENTS_MATRIX.md and recent Git history before continuing.
The user contracts are docs/PRODUCT_SPEC.md, docs/CONTINUATION_SPEC.md and the newer
docs/SPEECH_UPGRADE_SPEC.md (newer explicit requirements take priority). The current
primary target is the dual RTX 5080 workstation; see Decision 021. Preserve unrelated work. Never commit secrets,
recordings, runtime databases, model weights, caches or environments.
Use Python 3.11/3.12 and project-local dependencies. Production inference never uses fixtures.
Only the supervisor may admit GPU processes. The current implementation still admits
one process at a time under a host lock. The user requests a measured dual-GPU scheduler;
implement and verify that ownership/resource policy before allowing concurrent models.
Do not import inference frameworks in the API. Source sample offsets are canonical.
All meeting-content routes require membership, including admins. Approval and delivery are separate.
Use `python -m pytest`, `python -m ruff check .`, and `npm run build` in apps/web.
The cohesive operator CLI is `python -m scripts.mom`; see README for available subcommands.
Record actual checks and pending requirements. Never describe unrun inference as passing.
