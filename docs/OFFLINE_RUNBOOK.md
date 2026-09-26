# Offline operation and evidence scope

Prepare dependencies, local Chromium, models, compiled web/fonts and Mailpit while online.
Run verify-assets, then start without downloading. All API paths are local; SMTP defaults to loopback.
The UI truthfully says network observation is not measured. It never claims zero host traffic.

Do not disconnect all interfaces or change a shared host firewall automatically. For a target rehearsal:
1. Save current firewall configuration and arrange local console access/recovery before policy changes.
2. Use a dedicated Linux worker namespace with loopback only, no veth/default route, and scoped job files.
3. Permit API/browser loopback and the explicitly configured internal SMTP address only; cover IPv4,
   IPv6 and DNS. If containers are used, evaluate forwarded traffic separately from host OUTPUT.
4. Capture only this application's process/namespace interval. Deliberately test blocked external routes
   separately, then cold-start and process newly recorded synthetic audio through Mailpit.
5. Restore the saved policy and verify expected connectivity from local console.

This is a review procedure, not an executed firewall proof. On Windows/WSL2, measure Windows, WSL and
container boundaries separately. A Linux namespace observation cannot establish Windows host-wide silence.
No privileged firewall or driver changes were performed by implementation scripts.

## Executed scope

Windows `prepare-offline` produced a checksummed platform-specific kit; `install_offline.py` verified its
files and installed all 57 pinned Python packages from its wheelhouse using --no-index. This does not
prove Windows networking was blocked. Models, browser assets and native tools are included; FFmpeg,
Python and the GPU driver are host prerequisites. No private runtime state is copied.

`python -m scripts.offline_probe` was run under WSL with a dedicated unprivileged network namespace.
Both IPv4 and IPv6 external probes failed with errno 101 (ENETUNREACH). With Linux dependencies/tools
prepared, `MOM_ISOLATE_WORKER=1 python -m scripts.mom start` uses that boundary for the inference worker.
Mail delivery remains a separate process. The production Whisper and Qwen path subsequently completed in this namespace on WSL (51.038 s);
API/browser/PDF/SMTP and Windows-host networking were outside that test.

## Complete Linux app rehearsal

After preparation, run `python -m scripts.qualify_isolated_app --path /path/to/synthetic.wav`.
This creates its own unprivileged loopback-only namespace and fresh data under /var/tmp. It uses
production models and the real browser/API/PDF/Mailpit path, checks external IPv4/IPv6 failure before
and after, and verifies service cleanup. If your browser is prepared elsewhere, explicitly set
PLAYWRIGHT_BROWSERS_PATH. No host interface/firewall change is made.

Executed successfully on prepared Ubuntu 24.04 WSL: 84.589 s total, no owned services left.
This supersedes the earlier worker-only scope for Linux, but says nothing about Windows host egress.
Read the report at the printed data directory's proofs/isolated-app.json; keep it and the synthetic
screenshots locally. Do not open a live Linux SQLite database from Windows.

## Version-2 core package refresh

Use `python -m scripts.mom prepare-offline --path /new/kit --wheelhouse /prior/kit/wheels`
from clean committed prepared Windows source. The builder creates ordinary copies and leaves the
prior kit unchanged; it verifies compatible wheel hashes/lock and includes configuration, committed
source/notices, built UI and pinned core assets. It does not package the optional Linux runtime.
See Decision 020. Copy the resulting directory to the destination, verify the authenticated source
of that delivery, and run `python install_offline.py` with networking disconnected. Do not overlay
an existing installation. Keep the prior installation for rollback; migrate data only with the
separate stopped backup/restore procedure. On failure, retain the report/partial directory and
correct the prerequisite before preparing a new destination; no cleanup or replacement is automatic.

Python, FFmpeg/ffprobe and NVIDIA drivers remain host prerequisites. Windows host egress and target
8 GB qualification remain separate from no-index installation. A complete current Linux package
including optional dependencies still needs distribution qualification.
