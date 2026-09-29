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
