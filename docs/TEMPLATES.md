# Document templates

Open **Templates** to inspect Administrative, Executive and Medical configurations. A meeting's
classification chooses the template when its preview is created. Administrators can save a
heading in each interface/output language, a plain-text introduction, and a suggested existing
recipient group. Empty headings use the standard localized title. Introduction text is not
silently translated. Native review of Romanian/Russian interface translations remains pending.

Every save checks the template version. A failed or stale save keeps the edited form. If another
administrator changed the template, explicitly replace the form with the saved version before
editing that version. The server rejects non-admin edits and unknown recipient groups.

A preview freezes its complete template configuration and version together with its reviewed
meeting data. Later template changes affect new previews only; older HTML/JSON/PDF content is
not rewritten. The minutes screen shows the template version in addition to review revision.
Required decisions/actions, unresolved matters and amendment history cannot be disabled.
Titles/introduction are escaped plain text, never executable templates, remote assets or HTML.

The saved recipient group is a **suggestion**. The preview displays the currently allowed exact
addresses and group version. The secretary still chooses the group and explicitly sends the
approved snapshot. Template/classification changes never grant meeting access or enqueue mail.
Delivery retains its existing atomic snapshot/group-version check and frozen recipient list.

## Verification

- API tests: three default classifications; admin-only mutation; stale-version rejection;
  unknown-group rejection; HTML escaping; frozen old JSON/HTML; distinct preview after a change.
- Frontend: failed save retains input; concurrent refresh does not overwrite edits; non-admin
  controls are read-only; eight component/capture tests pass in the current worktree.
- Windows actual browser replay: configured heading/introduction/group, selected a meeting,
  reviewed captured synthetic T10 events and exported actual JSON/PDF with frozen template.
  Replay `quantity-replay-46be174d1fee4652b32fe98b1867778c` is not a new inference run.
- Full fixture browser/Mailpit checks were extended to cover templates and suggested recipients.
  An initial local attempt hit the live evaluator's GPU-admission lock and exposed a missing
  exact accessible select label; that label is fixed. Rerun the full fixture when GPU admission
  is free. Do not count this first attempt as a pass.

Final typography, branding and short/long/multilingual PDF inspection remain separate work.
