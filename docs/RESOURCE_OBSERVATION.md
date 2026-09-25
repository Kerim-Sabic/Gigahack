# Resource observation and target qualification

The target remains RTX 3070 Ti Laptop, 8 GB VRAM, 24 GB RAM. Current development hardware
is two RTX 5080 devices, each 16 GB, and 128 GiB host RAM. No target qualification is claimed.

Stage receipts now separate:

- Per-device capacity, idle total, sampled peak total and temperature.
- The stage subprocess/descendants' sampled RSS sum (shared pages may be double-counted).
- GPU memory attributed by the driver to observed owned process IDs, if available.
- Sample count, monitor errors and missing values.
- Peak-minus-idle estimate, explicitly approximate and excluded as an authoritative fit gate.
- Allocator allocations, explicitly unavailable until a trusted runtime interface supplies them.

The resource report is also attempted after failed/cancelled stages, without masking their
original failure or cleanup when diagnostics cannot be written. No content, source quotes,
credentials or process command lines are included. Device names/indices and aggregate usage
are local diagnostics. Querying local NVIDIA telemetry does not create a network dependency.

Current Windows driver reports process IDs but returns N/A for their memory. This remains
`null` / `not measured`; a total device reading is never relabeled as application usage.
The Linux/WSL and Windows boundaries may expose different monitoring support. Check actual
reports instead of assuming support based on OS alone.

## Observed continuation check

On this development Windows host, the real 20-second silence branch passed with zero
transcript segments, candidates or deliveries in 5.547 seconds. Five resource samples:
GPU 0 idle 1843 MiB; sampled total peak 3992 MiB; approximate increase 2149 MiB;
owned-process GPU memory unavailable; process-tree RSS peak 3,245,715,456 bytes.
One owned GPU process was observed. Peak host used RAM 28,019,191,808 bytes includes
unrelated activity and is not this application's RAM requirement. This silence run does
not qualify active speech, extraction, sustained load or the target laptop.

`python -m scripts.mom qualify-target --path /path/to/synthetic.wav` remains the integrated
entry point. It retains the target hardware check, real browser workflow and conservative
sampled total-memory headroom check. Reports now expose resource attribution separately.
An over-budget shared-host total is an operational observation, not proof that model
allocations exceed 8 GB. Missing process monitoring stays explicit. Human multilingual
accuracy, host egress boundaries and sustained thermals remain separate open gates.
