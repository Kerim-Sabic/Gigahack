# Notavra

Product name: **Notavra**. Repository: Gigahack. Original challenge: Secure MOM.
Display identity is centralized in `config/brand.json`; see [brand notes](docs/BRAND.md).

Local meeting audio → original transcript → evidence review → approved minutes → local SMTP.
**In active implementation.** A real synthetic upload-to-PDF-to-Mailpit workflow has passed on the
Windows development GPU. Full product acceptance, 30-case accuracy and the target 8 GB laptop remain
unqualified. See [status](docs/STATUS.md), [tests](docs/TEST_RESULTS.md) and [requirements](docs/REQUIREMENTS_MATRIX.md).

## Prepare once while online

Use Python 3.11/3.12, Node 22, Git, FFmpeg/ffprobe on PATH. Linux or Windows + WSL2 is the intended
deployment; native Windows is the tested development path. Do not install a WSL display driver.

```powershell
git clone https://github.com/Kerim-Sabic/Gigahack.git
cd Gigahack
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
npm ci --prefix apps/web
npm run build --prefix apps/web
python -m playwright install chromium
python -m scripts.mom prepare-models
python -m scripts.mom prepare-tools
python -m scripts.mom verify-assets
python -m scripts.mom doctor
python -m scripts.mom start
```

Open http://127.0.0.1:8765. First-run setup creates a local admin with your own password (12+ characters).
There is no production default account/password. The development verification database contains only
synthetic content and is never included in Git. Mailpit is http://127.0.0.1:8025; SMTP port 1025.

Startup installs/downloads nothing and verifies model checksums. Missing or damaged models, prepared
frontend or Mailpit fail clearly; the app never substitutes fixture results or cloud inference.
Models are under `models/`; recordings/database under `.runtime/` unless `MOM_DATA` is set.
Both directories are ignored by Git. Keep host storage encrypted and protected by OS permissions.

## Linux / WSL2

Clone onto the Linux filesystem. Create/activate `.venv` with `python3 -m venv .venv` and
`source .venv/bin/activate`. Install FFmpeg using your OS package manager. Install the locked Python
requirements and build web assets as above. Prepare models and Mailpit with the same CLI.
The prepare-tools command installs pinned llama.cpp b11146 CUDA binaries for Windows x64 and
Linux x64 (Ubuntu CUDA 12.8 build), plus Mailpit. Linux stage processes discover packaged CUDA library paths.
A prepared Ubuntu 24.04 WSL installation passed the full real workflow in a loopback-only namespace.
A fresh remote Windows clone also passed new-environment installation, build and real workflow
using the previously prepared pinned assets (25.257 s browser workflow). NVIDIA runtime packages and
driver compatibility must be checked by doctor and real qualification. Use the Windows browser on localhost
for microphone capture; plain LAN HTTP is not a secure microphone context.

## Test and operate

```text
python -m scripts.mom test
python -m ruff check services scripts tests
npm run build --prefix apps/web
python -m scripts.mom stop
python -m scripts.mom backup --path /new/backup/directory
# Restore requires MOM_DATA to point to a new empty directory:
python -m scripts.mom restore --path /existing/backup/directory
```

For real synthetic qualification, start services, set `MOM_QUALIFY_USER` and `MOM_QUALIFY_PASSWORD`
to a local synthetic-test account, then run:

```text
python -m scripts.mom qualify-target --path /path/to/synthetic.wav
```

Qualification writes `.runtime/proofs/qualification.json` and returns nonzero for incomplete mandatory
checks. This deliberately does not report a pass when target memory/offline measurements are unavailable.
Actual text-model regression outputs: stop services, then `python -m scripts.evaluate_text`.

## Limitations

The baseline is functional, but required hardening remains: full localization, long-meeting reconciliation,
all 30 expected extraction outcomes, optional model qualification, robust live-mic fault rehearsal,
kernel-enforced offline deployment and sustained target-machine measurements.
Model output always requires human review. Unknown values remain unresolved. Approval and sending are
separate transactions; SMTP acceptance is not recipient receipt. See [recovery](docs/RECOVERY.md).

This is not qualified for real hospital use or medical treatment recommendations.

## Prepared Windows offline kit

After online preparation, run `python -m scripts.mom prepare-offline --path /new/kit/directory`.
The platform-specific kit includes models, native tools, compiled UI/fonts, local Chromium and a pinned
wheelhouse. It excludes accounts, meeting data and secrets. On the destination with matching Python 3.12,
run `python install_offline.py` from the kit, then from `application` run
`.venv\Scripts\python -m scripts.mom start`. FFmpeg/ffprobe and a compatible NVIDIA driver are
external host prerequisites. Preparation and no-index installation were exercised; a complete Linux
isolated workflow also passed. The Windows kit has not been rehearsed with host egress blocked. The kit is an internal deployment artifact, not a public binary release.

Synthetic browser microphone check (services running and qualification credentials set):
`python -m scripts.recording_e2e`. It defaults to 305 seconds and exercises real AudioWorklet/chunk capture
using Chromium's synthetic microphone. It does not validate a physical microphone.

Scoped Linux real-inference check, after preparation (use native Linux storage for MOM_DATA):
`python -m scripts.qualify_worker_isolation --path /path/to/synthetic-16khz-mono.wav`.
This runs the production worker with external IPv4/IPv6 blocked in its own namespace. It does not
measure Windows-host networking or include browser/PDF/SMTP. Never open a live Linux SQLite database
from Windows; use the backup API or read the completed report instead.

Fast fixture browser check: stop managed services, prepare Mailpit, then run
`python -m tests.browser_fixture`. Only its test process replaces inference; the report is explicitly
labeled fixture inference. It exercises the real UI/API/queue/evidence/PDF/SMTP plumbing.

Complete Linux app offline rehearsal: `python -m scripts.qualify_isolated_app --path /path/to/synthetic.wav`.
Actual extraction crash/restart rehearsal: `python -m scripts.mom qualify-recovery` (prepared
Linux/WSL, isolated synthetic data, actual model, no active GPU job). See [recovery](docs/RECOVERY.md).
See [scope and evidence](docs/OFFLINE_RUNBOOK.md). Run `python -m scripts.mom doctor` before startup;
it reports missing preparation with repair actions, not product or target-device qualification.

Real silence regression: `python -m scripts.evaluate_silence` (requires prepared GPU models, no active GPU job).
This covers 20 seconds of generated silence only. The fixture browser suite also checks actual 200%
Chromium zoom and viewer controls; it does not replace human accessibility or language review.

Native tools are verified against `manifests/tool-files.lock.json` at startup. Existing prepared
installations must run `prepare-tools` once for that manifest; cached pinned archives can be reused.
Doctor tests data-volume permissions using a temporary file that it closes and removes.
