# Source constraints and complete offline rehearsal

Preserve the existing stack and exact models; no new dependency/model or copied reference code.
Constrain quotes and optional field values to source literals. This proves traceability, not correct
interpretation. Persist raw responses before parsing and bound every rendered generation to 4096 tokens.
Retrieve bounded preceding context and prior topic candidates; lexical overlap only ranks retrieval,
never automatically merges facts. Human links/splits require reasons and preserve original history.

Same-model consistency is not independent verification. Fixed corpus results are development evidence;
two failures remain. Canonical citation ordering handles overlap duplicates but does not claim broad
semantic equivalence. Keep distinct raw dates and changed fields in event identity.

Freeze implementation hashes in jobs and fail explicitly if code changed before execution/publication.
Re-preparation checks existing pinned hashes before replacing manifests. Model files/raw data stay ignored.
Linux process start ticks avoid wall-clock-derived ownership drift; Windows uses creation time.
Only positively identified processes may be stopped. Rehearsal cleanup is itself an asserted outcome.

The complete app runs within one user/network namespace, no host firewall mutation or cloud dependency.
Use /var/tmp for durable local qualification artifacts. This scope excludes Windows host networking.
Existing FFmpeg OS prerequisite (Ubuntu package 6.1.1-3ubuntu5) is not redistributed; browser revision
1243 corresponds to pinned Playwright 1.63.0. Existing licenses/locks remain authoritative.
Resource tradeoff: shared development GPU total exceeds 7 GiB; target 8 GB laptop remains unqualified.
