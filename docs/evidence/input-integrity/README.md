# Reject ambiguous permission evidence

Reproduced on main `15d6607` on 2026-09-29: the duplicate policy field in
`duplicate-policy.jsonl` silently replaced the empty authorized set with
`["secret"]`, producing `PASS`. This was a parser defect, not an observed
production exploit. The fixture is intentionally invalid JSON evidence.

```sh
python3 -m rag_scope_check docs/evidence/input-integrity/duplicate-policy.jsonl
```

After the fix, stderr is:

```text
Invalid input: line 1: duplicate JSON field 'authorized_doc_ids'
```

Exit status is 2; stdout is empty, in either output format. Unique JSON fields
are required throughout an object, including optional exporter metadata.
Direct `evaluate([])` also previously returned PASS; it now raises InputError,
as do duplicate case IDs passed directly to evaluate. Valid iterators remain
supported. Tests exercise the CLI boundary and existing valid examples.

## Integration decision

Defer a Honcho exporter. [Honcho #1048](https://github.com/plastic-labs/honcho/issues/1048)
reports filtered vector-search underfill. The inspected
[query source](https://github.com/plastic-labs/honcho/blob/9d6fe8ca5dc666b99ef04bc00047fea4ca675017/src/crud/document.py#L334)
uses workspace/observer/observed metadata predicates. An exact scan with those
same predicates cannot establish independent permission truth. Current
[route authorization tests](https://github.com/plastic-labs/honcho/blob/main/tests/routes/test_auth_route_policy.py)
separately test peer membership read scopes; the mapping from those scopes to
a complete, independently captured document permission snapshot was not
established. No Honcho fixture or deployment was executed. This is a bounded
inspection, not a claim that an independent oracle is impossible.

[pgvector](https://github.com/pgvector/pgvector#filtering) already documents
iterative scans and filtering tradeoffs. Do not package that established tuning
advice as a novel product. Today's change instead repairs a reproduced defect
in this project's evidence boundary. It adds no database integration or proof
of market adoption.
