# Experimental optional runtime — not a release installation recipe

Pinned candidate packages and two reviewed compatibility changes used for the first successful
Community-1 and Parakeet 45-second excerpt runs. The production app has not adopted this runtime.
See docs/DECISIONS/010-optional-model-preparation.md and docs/PROVIDED_AUDIO_ACCEPTANCE.md.

Apply patches only to exactly matching upstream file SHA-256 values in patches.json; already
patched files must match the after hash. Never apply fuzzily to another release. Model weights
are unmodified and separately pinned. Original copyrights and Apache-2.0 license texts are
retained here. The installed Python SBOM and supplied notices are now retained separately. Additional source
and upstream notice provenance is included. Release linkage/native distribution review and a
reproducible preparation command remain open. bootstrap.txt pins preparation pip separately.

The candidate includes unused packages retained from the initial isolated experiment; it is not
claimed minimal. The version scan reports no matched OSV advisories at audit time, not immunity
to vulnerabilities. Runtime must remain local, telemetry disabled and externally isolated.

Full-recording experiments are documented in docs/PROVIDED_AUDIO_ACCEPTANCE.md. Their
coverage disagreements prevent a claim of linguistic qualification or production readiness.
