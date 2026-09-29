# Permission-sync evidence — 2026-09-29

Captured from the executable SQLite FTS5 demo with Python 3.10.9 / SQLite 3.39.4.
The JSONL files are actual exports; `*-report.json` and `*.txt` retain both the
expected failure and the corrected result. Timestamps change on each new export.

From the repository root:

```sh
python3 examples/sqlite_acl_demo.py > /tmp/rag-scope-stale.jsonl
python3 -m rag_scope_check /tmp/rag-scope-stale.jsonl --min-cohort-recall 0.8 --max-underfill-rate 0
# Expected exit 1: recall 0, underfill 1, zero leaks.
python3 examples/sqlite_acl_demo.py --sync-permissions > /tmp/rag-scope-corrected.jsonl
python3 -m rag_scope_check /tmp/rag-scope-corrected.jsonl --min-cohort-recall 0.8 --max-underfill-rate 0
# Expected exit 0: recall 1, underfill 0, zero leaks.
python3 -m unittest discover -s tests -v
# 10 tests pass, including both CLI paths and unchanged source-table assertions.
```

Use `--format json` on either gate for the detailed report. Replay the checked-in
exports by passing `docs/evidence/permission-sync/stale.jsonl` or `corrected.jsonl`
instead. These contain only synthetic identifiers. No evaluator thresholds changed.

## Opportunity and alternatives checked

User: an engineer evaluating permission-aware retrieval. Problem: safe output can
still omit the authorized answer. The [original practitioner report](https://www.reddit.com/r/Rag/comments/1w3q78p/our_rag_permissions_filter_is_safe_and_still/)
describes stale ACL copies and restrictive prefilters starving useful private
candidates while generic public results remain. The [public JSON](https://www.reddit.com/r/Rag/comments/1w3q78p/our_rag_permissions_filter_is_safe_and_still/.json)
dates it to 2026-08-31 (created_utc 1788208689). This demo isolates a missed grant;
it does not reproduce the author's system or every reported failure.

- [raggate product documentation](https://raggate.net/product.html) and
  [quickstart](https://raggate.net/quickstart.html) already cover independent policy
  snapshots, leaks, near-misses, remediation and access-surface comparisons. The
  inspected docs do not describe authorized-recall or underfill thresholds. No
  public source/issues URL was identified; downloads require sign-in. Source and
  open issues could not be audited, so absence of this capability is unproven.
- [Qdrant filtering](https://qdrant.tech/documentation/search/filtering/) already
  supports payload/ID constraints. Open [issue #7147](https://github.com/qdrant/qdrant/issues/7147)
  (2025-08-26) reports poor tenant-filter recall compared with exact search, with
  rebuilding HNSW as a workaround. This is adjacent evidence, not a stale-grant
  reproduction. Filtered-recall measurement is not new.

Decision: improve the existing bounded example, not create another product or
generic skill. Its useful result is a reproducible before/after check combining
authorized recall, underfill and leaked context. An upstream contribution to
raggate remains worth considering, but its source access and contribution fit
could not be established. No code was reused from these alternatives.

Limits: one planted query, synthetic source oracle, no ANN behavior, no production
sync, no adoption or novelty claim. Public Reddit, Qdrant docs/issues and raggate
docs were checked; Hacker News and Stack Overflow were not searched in this build.
Next: review this draft, then separately scope a real retrieval exporter with an
independent source permission oracle and explicit empty/invalid evidence checks.
