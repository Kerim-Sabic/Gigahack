# Secure MOM

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

Startup installs/downloads nothing. Missing prepared frontend or Mailpit fails clearly. Missing models
appear in diagnostics and processing errors; the app never substitutes fixture results or cloud inference.
Models are under `models/`; recordings/database under `.runtime/` unless `MOM_DATA` is set.
Both directories are ignored by Git. Keep host storage encrypted and protected by OS permissions.

## Linux / WSL2

Clone onto the Linux filesystem. Create/activate `.venv` with `python3 -m venv .venv` and
`source .venv/bin/activate`. Install FFmpeg using your OS package manager. Install the locked Python
requirements and build web assets as above. Prepare models and Mailpit with the same CLI.
The current prepare-tools automatically installs llama.cpp on Windows only. On Linux, build pinned
llama.cpp b11146 with CUDA and set `MOM_LLAMA_SERVER` to the resulting `llama-server` binary.
This Linux installation path has not yet been rehearsed end-to-end. NVIDIA runtime packages and
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
external host prerequisites. Preparation and no-index installation were exercised; a disconnected full
workflow has not been verified. The kit is an internal deployment artifact, not a public binary release.

Synthetic browser microphone check (services running and qualification credentials set):
`python -m scripts.recording_e2e`. It defaults to 305 seconds and exercises real AudioWorklet/chunk capture
using Chromium's synthetic microphone. It does not validate a physical microphone.
