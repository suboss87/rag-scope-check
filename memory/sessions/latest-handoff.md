# Handoff — 2026-09-29 evidence integrity

Branch: factory/reject-ambiguous-evidence, based on main15d6607.
Reproduced duplicate authorized_doc_ids JSON fields silently overwriting denial
and producing PASS; direct evaluate([]) also returned PASS. Reject duplicate
object fields with line diagnostics, empty and duplicate API case batches,
and nonobject API cases. Valid metrics and iterators unchanged.

12 tests pass, including both CLI formats exiting2 with empty stdout for
ambiguous evidence. Fixture/repro in docs/evidence/input-integrity/README.md.
No dependencies installed. Honcho integration deferred: inspected source
filters and route auth tests do not yet establish independent source oracle.
Jev scout narrow_scope accepted; parent is evaluating this new defect packet.
Pending: independent review, draft PR CI; do not merge without review.
