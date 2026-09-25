# Optional model preparation and dependency review

Parakeet and Community-1 remain disabled until complete local inference, resource and
integration checks pass. Downloads alone do not establish readiness. Existing core
Whisper/Qwen architecture and prepared runtime are unchanged.

Prepared immutable snapshots are recorded in manifests/optional-models.lock.json. NVIDIA's
Parakeet TDT 0.6B v3 and pyannote Community-1 use CC-BY-4.0; original model cards are preserved
under manifests/optional-model-cards and the license text under manifests/licenses. Model
weights are unmodified, ignored by Git, and not included in public artifacts. Community-1
initially denied access; the user accepted the publisher's terms and download then succeeded.
License text was retrieved from Creative Commons' own team-open repository LICENSE because
the canonical legalcode.txt endpoint returned HTTP 403. Model card source/revision is pinned.

An experimental WSL environment installed 208 pinned resolved packages around NeMo 2.7.3,
pyannote.audio 4.0.7 and Torch 2.8.0. Pip check passed. Imports of NeMo ASR and pyannote passed
inside a dedicated network namespace; CUDA is available on the development host. That checks
imports, not model inference. OneLogger reported disabled with no exporters. Runtime telemetry
switches and namespace protection still require full inference qualification.

An OSV version audit of all 208 candidates found advisories against hydra-core 1.3.2,
lightning 2.4.0, Torch 2.8.0 and Transformers 4.57.6. Preserve the scan in
manifests/optional-candidate-security.json; detailed advisory responses remain in local
.runtime/optional-security-details.json. Only package names/versions were sent to OSV,
never recording content. A zero-conflict resolver result is not a security review.

A patched candidate resolved using focused NeMo 3.0 ASR/common extras, Torch 2.14,
torchaudio 2.11, TorchCodec 0.16, Lightning 2.6.6, Hydra 1.3.7 and Transformers 5.17.
The merged candidate environment has 232 pinned packages and no matches in its current OSV
scan; that is not proof of absence of vulnerabilities. Installation and pip check completed in
the isolated experimental environment. No production dependency lock is changed to it. Inspect
licenses, import and execute integrated behavior before adoption. This dependency change is
motivated by observed advisories, not an app architecture migration. Development driver
591.86 was observed; the target laptop's driver remains unmeasured.

The patched candidate failed NeMo import: OneLogger 2.3.1's save_checkpoint override annotates
weights_only as bool, while Lightning 2.6.6 accepts Optional[bool]. Its runtime override checker
rejects the narrower signature. A local experimental one-line patch matches the parent's
Optional[bool] = None signature; original bytes and before/after SHA-256 are retained locally.
This is not yet an adopted dependency patch or proof of working model inference. Do not
silence the global override checker or downgrade to the known-advisory stack to hide the error.

The NVIDIA model's large-GPU attention-duration claim is not an 8 GB laptop guarantee.
Qualification must retain sequential model residency, bounded clips/batches, actual load and
inference peaks, cancellation and full offline behavior. The RTX 3070 Ti Laptop remains
unavailable, and both speaker accuracy and code-switching accuracy lack a human gold reference.

Primary provenance: https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3 ;
https://huggingface.co/pyannote/speaker-diarization-community-1 ;
https://github.com/NVIDIA-NeMo/Speech ; https://github.com/meta-pytorch/torchcodec ;
https://api.osv.dev/v1/querybatch ; https://github.com/creativecommons/team-open/blob/main/LICENSE .

The first patched import passed pyannote and then exposed a second NeMo compatibility issue:
its training manager imports the removed Neptune cloud logger eagerly. A second experimental
patch defers that import until explicit Neptune configuration. Offline inference does not
request it; no cloud logger substitute is installed. Original/hash provenance is retained.

Both patched adapters subsequently completed actual inference on the 45-second supplied-audio
excerpt under unshare network isolation. The compatibility diffs, before/after hashes, resolved
232-package list, OSV scan and affected packages' Apache-2.0 licenses are preserved in
manifests/optional-runtime-experiment. This is experimental provenance, not a production
installation recipe. Full integrated behavior, comprehensive dependency notices, target-driver
compatibility and full-recording qualification remain pending. No core dependency lock changed.
