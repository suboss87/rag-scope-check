# Product contract

**Problem.** Permission filtering can stop unauthorized documents from reaching a model while also starving retrieval of useful, authorized evidence. A clean answer and tidy citations can hide the loss. Teams need a repeatable, local check that reports both safety and usefulness for each permission cohort.

**Evidence.** A practitioner described authorized-recall collapse after ACL prefiltering and asked for recall@k by cohort in [r/Rag, August 2026](https://www.reddit.com/r/Rag/comments/1w3q78p/our_rag_permissions_filter_is_safe_and_still/). A [Milvus permission-check issue](https://github.com/milvus-io/milvus/issues/53721) shows that authorization boundaries also need direct tests. [raggate](https://raggate.net/) already provides a substantial permission-leak regression gate; this project focuses on the quality lost after access is correctly enforced. These links are signals, not proof of market size.

**First user.** An engineer with a multi-tenant retrieval pipeline who can export retrieved document IDs, a source-of-truth permission snapshot, and relevance labels for a small query set.

**First result.** Run one command against JSONL cases and get a failing CI verdict if unauthorized context was returned or a configured cohort recall threshold was missed. See underfilled top-k and which pipeline stage lacked enough permitted candidates. No model, cloud account, or vector database required.

**Acceptance.** Deterministic examples pass and fail for the intended reasons; each cohort's authorized recall denominator excludes documents it cannot read; missing or stale policy evidence cannot silently pass a requested freshness gate; tests and CI cover these boundaries; limitations are explicit.
