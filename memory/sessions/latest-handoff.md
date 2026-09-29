# Build handoff — 2026-09-29

Branch: `factory/permission-sync-demo`, based on `2eb75ee`.

Completed: `examples/sqlite_acl_demo.py --sync-permissions` corrects only the index
ACL table. Added two tests in `tests/test_sqlite_demo.py`, documented actual output
in README, and preserved both failure/success exports and reports under
`docs/evidence/permission-sync/`. That directory also records source coverage,
alternatives and limits. No evaluator, dependencies, scheduler or profile changes.

Validation: `python3 -m unittest discover -s tests -v` passes 10 tests. Real CLI
demo at recall >=0.8 and underfill <=0: stale exits 1 (recall 0, underfill 1,
zero leaks); corrected exits 0 (recall 1, underfill 0, zero leaks). Existing clean
fixture gate passes. `git diff --check` passes. Independent reviewer found no
issues and reproduced both paths. Initial discovery from workspace root failed
because `tests/` lives inside the product clone; all reported test results use
the correct repository root.

Pending: push, draft PR and remote CI verification. Do not merge automatically.
Next smallest product step after review: scope one real retrieval export backed
by a source permission oracle; explicitly test empty/invalid evidence. No generic
skill. Current demo remains synthetic and establishes no production readiness.

Access: GitHub requires elevated network access in this sandbox; authenticated gh
worked after escalation. raggate public source/issues could not be located, so
the comparison is documentation-only and absence of a capability is unproven.
