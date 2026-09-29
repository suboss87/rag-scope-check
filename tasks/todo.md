# Permission-sync demo

Goal: reproduce a missed index grant, then correct only the index ACL copy and
demonstrate useful authorized retrieval with the same source permissions, query,
relevance labels, k, and evaluation thresholds.

Scope: standard-library SQLite FTS5 example, regression tests, and actual output.
No evaluator changes, new dependencies, integration, or production claims.

- [x] Baseline: eight tests pass; stale demo fails recall and underfill with no leaks.
- [x] Stale CLI evidence fails recall >= 0.8 and underfill <= 0, with zero leaks.
- [x] Corrected CLI evidence passes those identical thresholds, with zero leaks.
- [x] Test that sync changes only the index ACL table and preserves the oracle/labels.
- [x] Document actual output and complete separate review (no findings).
- [x] Open [draft PR #1](https://github.com/suboss87/rag-scope-check/pull/1).
- [x] Remote push and PR CI pass for implementation commit `95aec5c`.

## Evidence integrity (2026-09-29)

Goal: reject ambiguous or empty evidence instead of reporting PASS.
Context: reproduced empty direct API batch and duplicate permission JSON fields
returning PASS on main. Honcho source-oracle integration remains unproven.
Constraints: standard library, preserve existing valid exports/metrics.

- [x] Reproduce false PASS before editing.
- [x] Reject duplicate JSON object fields with line-number diagnostics.
- [x] Reject empty/duplicate direct API case batches and invalid case objects.
- [x] Verify CLI exit 2 without PASS output, existing examples, and 12 tests.
- [ ] Independent review and draft PR.
