# Separate resource attribution from device totals

Date: 2026-09-25. No new dependency or model.

Previous receipts recorded device-0 total GPU and whole-host used RAM. Those remain useful
operational readings but cannot explain application allocations on a shared workstation.
Use existing psutil plus local nvidia-smi to capture a pre-load baseline, every device,
owned subprocess IDs and process memory where the driver supplies it. Preserve N/A as null.
Keep peak-minus-idle labeled an approximation; it never substitutes for process attribution.
Do not add an allocator cap and claim it reproduces an 8 GB laptop.

The supervisor remains the only model-process owner. Sampling adds no GPU residency or
network access. Receipts become version 2, retain legacy total fields, include scope/health
and save best-effort diagnostics on failure. Runtime identity includes the sampler so
changed monitoring cannot silently reuse a prior queue configuration. Existing qualification
reports expose the new distinction; unobserved target fit remains unverified.

Validation: parser and N/A/unrelated-process tests, real child cancellation, and an actual
CUDA silence run with five samples. Windows per-process GPU memory was unavailable; host
and device totals were measured. See RESOURCE_OBSERVATION.md. Long/full-workflow and target
resource checks remain pending.
