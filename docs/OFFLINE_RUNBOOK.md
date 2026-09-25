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
Mail delivery remains a separate process. The complete isolated inference path has not been verified.
