# 027 — Isolated transcription speed experiment

2026-09-27. Added an explicit standalone speed benchmark using the existing supervised Whisper stage, GPU admission lock, model lock and pinned local model. Production transcript extraction and configuration are unchanged. Results use an isolated database and runtime directory; audio, raw transcript outputs and weights are not committed. Future runs archive each profile before the next profile reuses the job directory.

The 702.549-second Medpark recording was fed in contiguous windows with no VAD removal. Three fully consumed runs were measured per profile. On one RTX 5080, FP16 batch 32 achieved a 6.212-second median core transcription time (113.10x playback); decoding, model loading and the first inference together took 9.404 seconds. The dual-GPU profile had a 7.873-second median and was slower for this recording. Settings force Romanian with greedy decoding and disable word alignment, LLM extraction and diarization. Accuracy was not measured. This result does not establish code-switching quality, cold filesystem-cache performance, or the challenge's 60-minute upload-to-email target.

Provenance: existing manifests/models.lock.json Whisper revision edaa852ec7e145841d8ffdb056a99866b5f0a478, faster-whisper 1.2.1. No new models or dependencies adopted. Raw measurements are in the private runtime speed-benchmarks/1790504900516716400/report.json and the presentation's exported technical report. No production speed settings were changed.

The competing packaging LLM process was stopped at the user's request. The idle Notavra worker was temporarily paused for exclusive benchmark admission and restored afterwards.
