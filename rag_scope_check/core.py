"""Deterministic checks for permission-scoped retrieval results."""

import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class InputError(ValueError):
    """A case cannot be interpreted safely."""


def _ids(case, field, required=True):
    value = case.get(field)
    if value is None and not required:
        return None
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise InputError(f"{field} must be an array of nonempty document IDs")
    if len(value) != len(set(value)):
        raise InputError(f"{field} contains duplicate document IDs")
    return set(value)


def _time(value, field):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise InputError(f"{field} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InputError(f"{field} must include a timezone")
    return parsed


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON field {key!r}")
        result[key] = value
    return result


def load_cases(path):
    cases, seen = [], set()
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            case = json.loads(line, object_pairs_hook=_unique_object)
        except json.JSONDecodeError as exc:
            raise InputError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
        except InputError as exc:
            raise InputError(f"line {line_number}: {exc}") from exc
        if not isinstance(case, dict):
            raise InputError(f"line {line_number}: each line must be an object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise InputError(f"line {line_number}: id must be a nonempty string")
        if case_id in seen:
            raise InputError(f"line {line_number}: duplicate case id {case_id}")
        seen.add(case_id)
        cases.append(case)
    if not cases:
        raise InputError("input has no cases")
    return cases


def evaluate_case(case):
    if not isinstance(case, dict):
        raise InputError("each case must be an object")
    case_id, tenant, cohort, k = case.get("id"), case.get("tenant"), case.get("cohort"), case.get("k")
    if not isinstance(case_id, str) or not case_id.strip():
        raise InputError("id must be a nonempty string")
    if not isinstance(tenant, str) or not tenant.strip():
        raise InputError(f"{case_id}: tenant must be a nonempty string")
    if not isinstance(cohort, str) or not cohort.strip():
        raise InputError(f"{case_id}: cohort must be a nonempty string")
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise InputError(f"{case_id}: k must be a positive integer")

    authorized = _ids(case, "authorized_doc_ids")
    relevant = _ids(case, "relevant_doc_ids")
    returned = _ids(case, "returned_doc_ids")
    candidates = _ids(case, "candidate_doc_ids", required=False)
    eligible_count = case.get("eligible_doc_count")
    if isinstance(eligible_count, bool) or not isinstance(eligible_count, int) or eligible_count < 0:
        raise InputError(f"{case_id}: eligible_doc_count must be a nonnegative integer")
    if len(returned) > k:
        raise InputError(f"{case_id}: returned_doc_ids has more than k items")
    if candidates is not None and not returned <= candidates:
        raise InputError(f"{case_id}: returned_doc_ids must come from candidate_doc_ids")
    observed_authorized = (candidates if candidates is not None else returned) & authorized
    if len(observed_authorized) > eligible_count:
        raise InputError(f"{case_id}: eligible_doc_count is smaller than observed authorized documents")

    as_of, retrieved_at = case.get("policy_as_of"), case.get("retrieved_at")
    if (as_of is None) != (retrieved_at is None):
        raise InputError(f"{case_id}: policy_as_of and retrieved_at must be provided together")
    age_hours = None
    if as_of is not None:
        age_hours = (_time(retrieved_at, "retrieved_at") - _time(as_of, "policy_as_of")).total_seconds() / 3600
        if age_hours < 0:
            raise InputError(f"{case_id}: policy_as_of is after retrieved_at")

    permitted_relevant = relevant & authorized
    target = min(k, eligible_count)
    permitted_candidates = candidates & authorized if candidates is not None else None
    recall = len(returned & permitted_relevant) / len(permitted_relevant) if permitted_relevant else None
    return {
        "id": case_id,
        "tenant": tenant,
        "cohort": cohort,
        "authorized_recall": recall,
        "authorized_relevant_count": len(permitted_relevant),
        "leaked_doc_ids": sorted(returned - authorized),
        "unauthorized_candidate_ids": sorted(candidates - authorized) if candidates is not None else None,
        "underfilled_top_k": len(returned) < target,
        "candidate_underfill": len(permitted_candidates) < target if permitted_candidates is not None else None,
        "ranker_underfill": len(returned) < target and len(permitted_candidates) >= target if permitted_candidates is not None else None,
        "policy_age_hours": age_hours,
    }


def evaluate(cases, min_cohort_recall=None, max_underfill_rate=None, max_policy_age_hours=None):
    for name, value in (("min_cohort_recall", min_cohort_recall), ("max_underfill_rate", max_underfill_rate)):
        if value is not None and (not math.isfinite(value) or not 0 <= value <= 1):
            raise InputError(f"{name} must be between 0 and 1")
    if max_policy_age_hours is not None and (not math.isfinite(max_policy_age_hours) or max_policy_age_hours < 0):
        raise InputError("max_policy_age_hours must be nonnegative")

    results, seen = [], set()
    for case in cases:
        result = evaluate_case(case)
        if result["id"] in seen:
            raise InputError(f'duplicate case id {result["id"]}')
        seen.add(result["id"])
        results.append(result)
    if not results:
        raise InputError("input has no cases")
    groups = defaultdict(list)
    for result in results:
        groups[(result["tenant"], result["cohort"])].append(result)

    cohorts, failures = [], []
    for (tenant, name), rows in sorted(groups.items()):
        recalls = [row["authorized_recall"] for row in rows if row["authorized_recall"] is not None]
        mean_recall = sum(recalls) / len(recalls) if recalls else None
        underfill_rate = sum(row["underfilled_top_k"] for row in rows) / len(rows)
        cohorts.append({
            "tenant": tenant, "cohort": name, "cases": len(rows), "scored_cases": len(recalls),
            "mean_authorized_recall": round(mean_recall, 4) if mean_recall is not None else None,
            "underfill_rate": round(underfill_rate, 4),
            "leaking_cases": sum(bool(row["leaked_doc_ids"]) for row in rows),
        })
        if min_cohort_recall is not None and (mean_recall is None or mean_recall < min_cohort_recall):
            failures.append(f"{tenant}/{name}: authorized recall below {min_cohort_recall:g} or unscored")
        if max_underfill_rate is not None and underfill_rate > max_underfill_rate:
            failures.append(f"{tenant}/{name}: underfill rate above {max_underfill_rate:g}")

    for row in results:
        if row["leaked_doc_ids"]:
            failures.append(f'{row["id"]}: unauthorized documents reached returned context')
        if max_policy_age_hours is not None:
            age = row["policy_age_hours"]
            if age is None or age > max_policy_age_hours:
                failures.append(f'{row["id"]}: policy snapshot missing or older than {max_policy_age_hours:g} hours')

    return {
        "verdict": "FAIL" if failures else "PASS",
        "case_count": len(results),
        "cohorts": cohorts,
        "failures": failures,
        "cases": results,
        "limits": {
            "min_cohort_recall": min_cohort_recall,
            "max_underfill_rate": max_underfill_rate,
            "max_policy_age_hours": max_policy_age_hours,
        },
    }
