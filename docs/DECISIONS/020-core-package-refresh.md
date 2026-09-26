# Refresh the core package through ordinary copies

The prior builder omitted `config/` and copied all model directories, including optional models
whose Linux runtime it did not package. It also lacked admission checks for the later installation.
The retained old kit is historical and is never modified or used as the current application.

Version 2 uses committed Git source plus a freshly built local frontend. It includes the central
configuration and source notices, copies only pinned core model/native files and the exact browser
revision, and reuses only checksum-verified wheels from a compatible prior kit with an identical
requirements lock. No new dependency, download, hardlink or equivalent link-based workaround is
introduced. This is explicitly a Windows standalone **core** package, not an optional-model kit.
Parakeet/Community-1 continue to require the separately prepared Linux runtime.

Preparation requires clean committed source and a new destination. It budgets the actual copied
bytes plus twice the wheels' uncompressed size and 256 MiB staging overhead, preserving at least
5 GiB free. The installer rechecks complete file inventory, path containment, OS/architecture,
Python minor version and all hashes before creating a new environment. It rejects existing installs,
uses binary wheels with isolated no-index/no-cache pip, and stages on the package volume. Failures
retain partial files for inspection; the operator chooses a fresh directory instead of overwriting
an old installation. Hashes detect corruption, not replacement by an unauthenticated publisher.

Eight focused checks pass for private-state exclusion, central configuration inclusion, corrupt
wheels/locks, extra files, path traversal, existing installations and reserve admission. Actual
new-package preparation/install and workflow evidence are recorded separately after execution.
No target-laptop or Windows host egress claim follows from packaging or `--no-index` alone.
