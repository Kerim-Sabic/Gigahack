# 028 — Romanian default transcription

The user now requests Romanian-only decoding by default, superseding the earlier automatic multilingual default. New jobs freeze asr.language="ro" and multilingual=false. Every primary ASR checkpoint passes that language explicitly, including the shorter OOM retry. No translation task or automatic window language detection is used. Forced-language provenance is labeled as configured rather than detected.

Developers control this in config/inference.toml. A validator rejects a forced language combined with multilingual detection. Old frozen jobs without the new field retain their original policy; existing transcripts are not rewritten. Language settings participate in checkpoint identity, so Romanian runs cannot reuse automatic-language checkpoints. Optional comparison engines remain separate evidence and do not replace the primary transcript.

Validation: 244 backend tests passed, two skipped; Ruff passed. Added multi-chunk language propagation/cache isolation and conflicting-policy validation tests. These verify configuration behavior, not acoustic accuracy or a guarantee that model output contains no foreign word. Managed API and worker restarted after confirming there were no queued/running jobs; API health passed. No new audio inference was requested or run for this change.
