# Bounded local reasoning for independent interpretation

Status: implemented with open semantic acceptance. Original 25/25 and development 16/16
pass; first held-out 5/6 fails a tentative Russian date change. See CONTINUATION_RESULTS.md. This refines the existing
Qwen/llama.cpp pipeline; no model, framework, dependency or cloud service is introduced.

Repeated prompt-only changes fixed individual cases but regressed nominal work, resource
decisions, conditions and negated units elsewhere. All attempts and unchanged gold remain
recorded. A separate concrete bug compared an initial bare amount to a later literal
amount plus unit as if they disagreed. Both passes now receive the same conservative literal
enrichment before comparison, and stale derived quantity metadata is rebuilt.

Enable local thinking only for classification, category and field interpretation schemas.
The existing initial extraction remains non-thinking with its bounded output. llama.cpp
b11146 caps enabled reasoning at 768 tokens; interpretation completion budgets increase by
800 tokens to leave room for that bounded reasoning and the existing structured answer.
The exact rendered template, including the per-request thinking setting, must still fit
the 4096-token context. Oversized input fails explicitly; it is not silently truncated.
One generation slot, one GPU process and the existing pinned 4B quantization remain.

Literal numeric options include negated alternatives, and are explicitly not facts. The
model must choose interpretation; every proposed field still needs literal, revision-valid
evidence. A repeated citation or same-model consistency check is not independent truth.
Reasoning output remains a local evaluation artifact, not user-facing proof or confidence.

Measured tradeoff on the development RTX 5080 host: the 25-case original text suite takes
738.05 seconds total (median 22.05, maximum 55.78 per case), versus 210.28 seconds (median
8.41, maximum 12.67) at attempt 4. Each evaluator case reloads the model, so this is not
meeting-end-to-email time. Both runs pass 25/25 original text checks. The earlier attempt-4
implementation passes only 13/16 development variations; the new full development run passes 16/16 (708.46 seconds). Accuracy improvement must justify the substantial latency increase.
No target-laptop latency, long-meeting throughput or memory fit is inferred from these times.

Sources inspected for the existing pinned runtime's capabilities:
[Qwen model card](https://huggingface.co/Qwen/Qwen3.5-4B) and
[llama.cpp b11146 server](https://github.com/ggml-org/llama.cpp/blob/b11146/tools/server/README.md).
Existing model/tool manifests retain their original revisions and license notices. Runtime
identity hashes include changed stage/quantity code so queued work cannot reuse another
implementation silently. Reassess this choice against held-out and long-window behavior;
never reduce transcript coverage or suppress uncertainty to recover speed.
