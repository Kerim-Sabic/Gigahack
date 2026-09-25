# Measurements, not forecasts

Windows development host: RTX 5080 16 GB (GPU 0), driver 591.86, 128 GiB RAM.
Target RTX 3070 Ti laptop 8 GB and 24 GB RAM: NOT RUN — TARGET MACHINE REQUIRED.

Synthetic speech generated with installed Windows speech synthesis; no human speaker or clinical
validation. Content: Elena sends maintenance report September 30; confirmed; reject ventilator purchase.
Input duration 9.6671875 s. Original audio and outputs retained locally, excluded from Git.

- Whisper large-v3 CT2 int8_float16: cold stage 15.251 s, including model loading.
- Qwen3.5-4B Q4_K_M initial cold extraction: 67.304 s; semantic/citation failure.
- Revised warm extraction smoke: successful; not a held-out accuracy estimate.
- Browser workflow including processing, automated synthetic review, PDF and mail: 21.584 s.
- Human review time, action precision/recall, RO/RU/code-switch accuracy: not measured.
- Latest full qualification command: 36.452 s; real browser workflow passed, memory gate failed.
- Latest Whisper stage: 18.820 s; process-tree RAM 4,370,640,896 bytes; total host RAM
  31,270,518,784 bytes; total GPU 0 memory 4880 MiB; maximum sampled GPU temperature 66 C.
- Latest extraction stage: 6.691 s; process-tree RAM 3,152,551,936 bytes; total host RAM
  29,938,745,344 bytes; total GPU 0 memory 4276 MiB; maximum sampled temperature 55 C.
- Samples include host/desktop activity and are not isolated process VRAM attribution.
- Sustained thermals, 10-minute and 60-minute runs: not measured.

The worker records process-tree RAM samples and stage elapsed times in receipts. Monitoring limitations
remain null, never zero. No under-15-minute one-hour claim is made.

WSL isolated production worker (synthetic input, no external route): 51.038 s total;
Whisper 27.723 s and Qwen 22.977 s. Peak sampled total GPU 0 memory 9769 MiB and
9076 MiB respectively; WSL memory samples 6.668/8.274 GB. This total-VRAM result exceeds the
requested 7 GiB gate. It includes Windows activity and does not qualify an 8 GB laptop.
