# Model lifetime under hard process failure

The supervisor's admission lock and periodic parent watcher did not cover a stage that
itself crashed while llama-server was alive. An orphan could retain GPU memory after the
supervisor admitted another job. The new boundary complements existing cancellation and
identity checks; the API still never imports inference frameworks.

On Windows, each stage places itself in a private Job Object before spawning any children.
Its sole non-inheritable handle uses KILL_ON_JOB_CLOSE. The operating system closes the
handle when the stage dies and terminates associated descendants. Assignment failure is
fatal before loading a model. On Linux, the stage installs PR_SET_PDEATHSIG and checks the
expected supervisor PID after installation. A small exec wrapper repeats this binding for
llama-server, since parent-death signals do not survive fork into the child. No multithreaded
preexec_fn is used. Existing parent identity polling remains as an additional guard.

A separate stage-held local model lock prevents a replacement stage loading while the
previous stage is still alive after supervisor failure. The supervisor remains the admission
authority. Locks are per operating-system temporary directory; this does not coordinate
unrelated applications or simultaneous native-Windows and WSL installations.

Actual synthetic sleeper tests force-killed a stage on Windows and Linux: its child stopped,
and an unrelated sleeper stayed alive. Linux additionally rejects a missing expected parent.
Windows full backend: 141 passed, one Linux-only check skipped. Actual changed-worker CUDA
silence inference passed in 7.00 seconds, with zero segments, candidates and deliveries.
Fresh actual Qwen T10 quantity extraction also passed (run 1790371439051700000, 36.99s),
exercising llama-server inside the Windows job. These do not yet constitute the full application/queue crash-recovery rehearsal.

Primary implementation references:
- https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
- https://man7.org/linux/man-pages/man2/PR_SET_PDEATHSIG.2const.html

The parent-death signal binds to the creating Linux thread; stage and child launches occur
on their main thread. The pinned llama binary is not a setuid/capability-changing executable.
