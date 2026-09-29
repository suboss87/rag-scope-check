# RAG Scope Check

Check whether a permission-aware retrieval path is both safe **and** useful to the people allowed to use it. A filter can prevent a cross-tenant leak while leaving a finance user with only generic public documents. RAG Scope Check reports unauthorized context, authorized recall by permission cohort, and underfilled top-k results from exported retrieval cases. It runs locally with Python's standard library; no model or vector database is needed for the check.

## Try it

```sh
python3 -m rag_scope_check examples/clean.jsonl --min-cohort-recall 1 --max-underfill-rate 0
```

Expected result:

```text
RAG scope check: PASS (2 cases)
acme/finance: authorized recall=1.00 (1 scored), underfill=0.00, leaking cases=0
acme/support: authorized recall=1.00 (1 scored), underfill=0.00, leaking cases=0
```

See a real failure shape:

```sh
python3 -m rag_scope_check examples/regression.jsonl --min-cohort-recall 0.8 --max-underfill-rate 0
```

This exits `1`: one case returns an unauthorized document, and the finance cohort also misses the authorized answer. Invalid or incomplete input exits `2`. Use `--format json` for a machine-readable report.

The [SQLite demo](examples/sqlite_acl_demo.py) runs an actual full-text retrieval query against a stale index ACL copy while checking permissions against a separate source table. It shows a **safe but unhelpful** result without relying on a static fixture:

```sh
python3 examples/sqlite_acl_demo.py > /tmp/rag-scope-case.jsonl
python3 -m rag_scope_check /tmp/rag-scope-case.jsonl --min-cohort-recall 0.8 --max-underfill-rate 0
```

The second command exits `1` for low authorized recall and top-k underfill, with zero leaked documents. Actual output:

```text
RAG scope check: FAIL (1 case)
acme/finance: authorized recall=0.00 (1 scored), underfill=1.00, leaking cases=0
! acme-finance-expense: top-k underfilled at candidate generation
! acme-finance-expense: authorized recall=0.00
- acme/finance: authorized recall below 0.8 or unscored
- acme/finance: underfill rate above 0
```

Now synchronize the index permission copy from the source table and retrieve again:

```sh
python3 examples/sqlite_acl_demo.py --sync-permissions > /tmp/rag-scope-corrected.jsonl
python3 -m rag_scope_check /tmp/rag-scope-corrected.jsonl --min-cohort-recall 0.8 --max-underfill-rate 0
```

This gate exits `0`, using **identical thresholds**:

```text
RAG scope check: PASS (1 case)
acme/finance: authorized recall=1.00 (1 scored), underfill=0.00, leaking cases=0
```

The stale query returns only `handbook`; the corrected query returns `handbook`
and `policy-v3`. Only the index ACL copy changes. Both modes build the same corpus,
source grants, query, reviewed relevance label (`policy-v3`), and k=2. Source checks
remain independent of the index ACL. Run the gates separately: they describe two
states of the same case, not two queries to average into a single cohort score.

This is a planted missed-grant example in an in-memory SQLite FTS5 database, not a
production permission-sync implementation or a vector-search benchmark. Its source
table is a simulated oracle; a real integration must obtain permissions independently
from the source system. Underfill alone cannot diagnose a stale grant. Python must
include SQLite FTS5; no packages or services are installed by the demo.

## Feed it from your pipeline

Export one JSON object per query to a `.jsonl` file. Capture `returned_doc_ids` at the **last retrieval boundary before model context assembly**. Obtain `authorized_doc_ids` from the source permission system for the same user and time, independently of the retrieval index. Create `relevant_doc_ids` from a reviewed query set. Document IDs can be opaque stable identifiers; no document text or query text is required.

```json
{"id":"finance-q1","tenant":"acme","cohort":"finance","k":2,"eligible_doc_count":3,"authorized_doc_ids":["policy-v3","handbook"],"relevant_doc_ids":["policy-v3"],"candidate_doc_ids":["policy-v3","handbook"],"returned_doc_ids":["policy-v3","handbook"],"policy_as_of":"2026-09-29T09:00:00+05:30","retrieved_at":"2026-09-29T09:05:00+05:30"}
```

`tenant` and `cohort` are both required; the report groups by the pair so a healthy tenant cannot mask a failing one. `authorized_doc_ids` lists the IDs that the source policy allows **among all IDs appearing in candidates, returned context, or relevance labels**. It does not require listing the whole corpus, but your exporter must ask the independent policy oracle about every one of those IDs. `eligible_doc_count` is the count of policy-allowed documents present in the retrieval corpus at query time; it lets the check distinguish a genuinely small authorized corpus from a starved top-k result.

`candidate_doc_ids` and the timestamps are optional. Candidates are the set available immediately before final ranking; when supplied, every returned ID must be in that set. Use `--max-policy-age-hours 24` to fail when snapshot timing is missing or too old. Use a current policy oracle in production, not the ACL copy stored in your vector index.

The report calculates recall for each query against **relevant documents that this user is authorized to read**, then averages scored queries within each cohort. A case with no authorized relevant document is unscored rather than assigned zero recall. A top-k result is underfilled when fewer than `min(k, eligible_doc_count)` IDs are returned. When candidate IDs are provided, the report distinguishes candidate underfill from loss after candidate generation. An unauthorized candidate is a warning; an unauthorized returned document always fails the gate.

Set `--min-cohort-recall` and `--max-underfill-rate` to thresholds appropriate to your workflow. Without those flags, only returned-document leaks fail. Run the same labeled cases before and after retriever, index, embedding, or ACL changes in CI.

## What this proves, and what it does not

The check proves what the exported cases show under the supplied policy snapshot and relevance labels. It cannot prove that every user or document is safe, that the permission oracle is correct, or that a model did not receive text through another path. An underfilled result identifies a symptom, not its root cause. Opaque IDs, cohort names, and reports may still be sensitive; keep them within your normal access controls.

This tool complements permission-leak gates such as [raggate](https://raggate.net/). The immediate problem came from a [practitioner's account of ACL-safe retrieval losing useful private sources](https://www.reddit.com/r/Rag/comments/1w3q78p/our_rag_permissions_filter_is_safe_and_still/). A [Milvus permission-check issue](https://github.com/milvus-io/milvus/issues/53721) is a separate reminder to test the authorization boundary itself. These are product signals, not adoption claims.

## Development

```sh
python3 -m unittest discover -s tests -v
```

No external services or API keys are needed. See [PRODUCT.md](PRODUCT.md) for the first-user and acceptance contract. Security reports can be sent through [private vulnerability reporting](https://github.com/suboss87/rag-scope-check/security/advisories/new).
