# ADR 001 — Focused local components

Accepted 2026-09-25. Keep React/Vite, FastAPI, SQLite and isolated model subprocesses.
The API uses explicit sqlite3 transactions rather than an ORM: short BEGIN IMMEDIATE
transactions make review revision checks and outbox insertion auditable. SQLAlchemy/Alembic
were provisioned but are not used; versioned SQL migrations now retain and test schema upgrade history.
No downloaded reference application or copied security layer is trusted wholesale.

Reuse: FastAPI/Pydantic (MIT), React/Vite (MIT), TanStack Query (MIT), Argon2-cffi (MIT),
faster-whisper (MIT), CTranslate2 (MIT), llama.cpp (MIT), Mailpit (MIT), Playwright (Apache-2.0),
Noto Sans (OFL-1.1). Installed package notices and dependency graphs are in manifests/.
Resolved versions are in requirements.lock.txt and package-lock.json. Model sources/revisions
and file SHA-256 hashes are in manifests/models.lock.json. No model repository code executes.
The Qwen GGUF is the Unsloth conversion of official Qwen3.5-4B; Apache-2.0 model card checked.
The conversion's exact converter build was not supplied by the artifact: record that provenance
limit rather than inventing it. llama.cpp b11146 was tested with this artifact.

Resource evidence: real sequential Whisper and Qwen CUDA smoke runs on RTX 5080 development
hardware, plus a browser-to-Mailpit run. These do not qualify RTX 3070 Ti 8 GB memory.
The scheduler admits one model process under a host lock and pins GPU device 0.
Optional NeMo and pyannote dependencies remain isolated and unqualified; do not install the
entire ecosystem merely to show an enabled switch. Their availability must remain explicit.

Online preparation is separate from startup. Serving compiled assets has no npm/CDN requirement.
FFmpeg is an external prerequisite; its build/license varies, so this repository does not redistribute it.
Local runtime contains no cloud inference adapter. Kernel-enforced isolation is a separate deployment
boundary and must not be inferred from offline flags or local URLs.
