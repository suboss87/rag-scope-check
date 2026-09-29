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

## Integration boundary

The current release checks exported cases and includes a synthetic SQLite example. A real retrieval integration still needs permissions from an independent source system and reviewed relevance labels. An exact search using the same index filters cannot establish permission truth.

The input-integrity fix repairs a reproduced defect in this tool's evidence handling. It adds no database connector, production validation or proof of market adoption.
