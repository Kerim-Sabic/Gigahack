# Secure MOM engineering conventions

Read docs/STATUS.md, docs/REQUIREMENTS_MATRIX.md and recent Git history before continuing.
The user contract is docs/PRODUCT_SPEC.md. Preserve unrelated work. Never commit secrets,
recordings, runtime databases, model weights, caches or environments.
Use Python 3.11/3.12 and project-local dependencies. Production inference never uses fixtures.
Only the supervisor may admit GPU processes; one process at a time under a host lock.
Do not import inference frameworks in the API. Source sample offsets are canonical.
All meeting-content routes require membership, including admins. Approval and delivery are separate.
Use `python -m pytest`, `python -m ruff check .`, and `npm run build` in apps/web.
The cohesive operator CLI is `python -m scripts.mom`; see README for available subcommands.
Record actual checks and pending requirements. Never describe unrun inference as passing.
