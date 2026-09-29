"""Emit a retrieval case before or after synchronizing a missed ACL grant."""

import argparse
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone


def create_database():
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE documents(id TEXT PRIMARY KEY, tenant TEXT NOT NULL, body TEXT NOT NULL);
        CREATE TABLE source_permissions(principal TEXT NOT NULL, doc_id TEXT NOT NULL);
        CREATE TABLE index_permissions(principal TEXT NOT NULL, doc_id TEXT NOT NULL);
        CREATE VIRTUAL TABLE search_index USING fts5(doc_id UNINDEXED, body);

        INSERT INTO documents VALUES
          ('policy-v3', 'acme', 'expense approval policy for finance'),
          ('handbook', 'acme', 'expense travel handbook'),
          ('contract', 'acme', 'supplier contract terms'),
          ('other-tenant-faq', 'rival', 'expense policy FAQ');
        INSERT INTO search_index SELECT id, body FROM documents;

        INSERT INTO source_permissions VALUES
          ('alice', 'policy-v3'), ('alice', 'handbook'), ('alice', 'contract');

        -- The index ACL copy missed a grant. Retrieval stays private but loses the answer.
        INSERT INTO index_permissions VALUES
          ('alice', 'handbook'), ('alice', 'contract');
    """)
    return db


def sync_permissions(db):
    """Replace only the demo index ACL copy from the independent source table."""
    with db:
        db.execute("DELETE FROM index_permissions")
        db.execute("INSERT INTO index_permissions SELECT principal, doc_id FROM source_permissions")


def retrieve_case(db):
    principal, k = "alice", 2
    candidates = [row[0] for row in db.execute("""
        SELECT s.doc_id FROM search_index AS s
        JOIN index_permissions AS p ON p.doc_id = s.doc_id
        WHERE s.body MATCH ? AND p.principal = ?
        ORDER BY bm25(search_index) LIMIT ?
    """, ("expense", principal, k))]
    relevant = ["policy-v3"]  # A reviewed label for this query.
    observed = set(candidates) | set(relevant)
    authorized = [doc_id for doc_id in sorted(observed) if db.execute(
        "SELECT 1 FROM source_permissions WHERE principal = ? AND doc_id = ?",
        (principal, doc_id),
    ).fetchone()]
    eligible_count = db.execute("""
        SELECT count(*) FROM source_permissions AS p
        JOIN documents AS d ON d.id = p.doc_id
        WHERE p.principal = ?
    """, (principal,)).fetchone()[0]
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": "acme-finance-expense", "tenant": "acme", "cohort": "finance",
        "k": k, "eligible_doc_count": eligible_count,
        "authorized_doc_ids": authorized, "relevant_doc_ids": relevant,
        "candidate_doc_ids": candidates, "returned_doc_ids": candidates,
        "policy_as_of": now, "retrieved_at": now,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sync-permissions", action="store_true",
        help="copy source grants into the index ACL table before retrieving",
    )
    args = parser.parse_args()
    with closing(create_database()) as db:
        if args.sync_permissions:
            sync_permissions(db)
        print(json.dumps(retrieve_case(db)))


if __name__ == "__main__":
    main()
