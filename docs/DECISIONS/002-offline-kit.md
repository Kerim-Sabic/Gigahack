# ADR 002 — Prepared deployment kit

Keep the existing runtime. The Windows kit packages its compiled frontend, exact model files,
llama.cpp/Mailpit, pinned wheels and the Playwright-matched browser revisions. Startup does not install.
The installer verifies every file hash before creating a new environment and installs with --no-index.
It is platform/Python-specific; it is not a cross-platform executable or a public release installer.

Use an explicit source inclusion list. Never copy .env, runtime accounts, meeting databases, recordings,
Git metadata, process files or logs. Model weights and dependency wheels remain outside Git. FFmpeg,
Python and the GPU driver are host prerequisites, with their own installation/license requirements.

Tool licenses are fetched from version-tagged upstream sources and tracked with hashes in
manifests/tool-license-sources.json. CUDA runtime libraries have NVIDIA terms, not an open-source license;
retain their notices with the kit. The CUDA 12.4.1 EULA distribution requirements and redistributable
library list were reviewed. This internal deployment preparation is not permission to redistribute
arbitrary SDK components or to remove vendor conditions. The pinned wheel notices are also preserved.

Executed: preparation and installation of all 57 pinned wheels without an index. Complete disconnected
application operation is still unverified. The kit checksum manifest detects corruption, not malicious
replacement of both content and manifest; authenticated distribution is an operator responsibility.
