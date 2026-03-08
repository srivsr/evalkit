"""
Layer C: Claim & Citation Verification — from EVALKIT_MASTER_SPEC_v2.md Section 6.

Process:
1. Split response into atomic claims (sentence-level)
2. For each claim, search contexts for supporting evidence spans
3. Classify: supported | partially_supported | unsupported
4. Record evidence spans with character offsets

This is deterministic — no LLM calls. Works even without API keys.
"""
import re
from difflib import SequenceMatcher


_SENTENCE_SPLIT = re.compile(
    r'(?<=[.!?])\s+(?=[A-Z])'  # primary: ". X"
    r'|(?<=\.)\s*\n+'           # line-break after period
    r'|(?:^|\n)\s*[-•*]\s+'    # bullet items
    r'|(?:^|\n)\s*\d+[.)]\s+'  # numbered items on new line
    r'|(?<=[.!?:;])\s+(?=\d+[.)]\s)'  # inline numbered items: "...code. 2) Gather..."
)

_MIN_CLAIM_LENGTH = 10

_NUMBER_WITH_UNIT_RE = re.compile(
    r'\$\s*\d+(?:,\d{3})*(?:\.\d+)?'           # dollar amounts: $500, $1,000
    r'|\b\d+(?:\.\d+)?%'                        # percentages without space: 25%, 15%
    r'|\b\d+(?:\.\d+)?\s+(?:\w+\s+)?(?:%|days?|weeks?|months?|years?|hours?)\b'  # number + optional adjective + unit
)


def _extract_numbers_with_units(text: str) -> list[tuple[str, str]]:
    """Extract (value, unit) pairs. Only returns numbers that have an explicit unit.

    Handles patterns like "15 business days" → ("15", "days"), "$500" → ("500", "$").
    """
    results = []
    for m in _NUMBER_WITH_UNIT_RE.finditer(text):
        token = m.group().strip().lower()
        val = re.sub(r'[^\d.]', '', token).strip()
        # Extract only the actual unit keyword (days, hours, $, etc.), drop adjectives
        unit_match = re.search(r'(%|days?|weeks?|months?|years?|hours?)(?:\b|$)', token)
        if unit_match:
            unit = unit_match.group()
        else:
            unit = re.sub(r'[\d.\s,]', '', token).strip()  # fallback for $ amounts
        if val and unit:
            # Normalize: "day" → "days" for consistent comparison
            if unit in ("day",):
                unit = "days"
            elif unit in ("week",):
                unit = "weeks"
            elif unit in ("month",):
                unit = "months"
            elif unit in ("year",):
                unit = "years"
            elif unit in ("hour",):
                unit = "hours"
            results.append((val, unit))
    return results


def _find_contradicted_numbers(claim_text: str, all_contexts: list[dict], query: str = "") -> list[tuple[str, str]]:
    """Find claim numbers that don't appear in any context but the same unit does.

    Returns list of (value, unit) pairs that are contradicted.
    E.g., claim says "$500" but all contexts only have "$300" and "$1,000" → ("500", "$").
    Numbers that appear in the query are excluded (they are user-provided, not fabricated).
    """
    claim_nums = _extract_numbers_with_units(claim_text)
    if not claim_nums:
        return []

    # Collect all numbers from all contexts
    all_ctx_nums: list[tuple[str, str]] = []
    for ctx in all_contexts:
        all_ctx_nums.extend(_extract_numbers_with_units(ctx.get("text", "").lower()))

    if not all_ctx_nums:
        return []

    # Exclude numbers that come from the query (user-provided, not fabricated)
    query_nums = set(_extract_numbers_with_units(query.lower())) if query else set()

    contradicted = []
    for c_val, c_unit in claim_nums:
        if (c_val, c_unit) in query_nums:
            continue
        # Does this exact value+unit exist in any context?
        has_match = any(x_val == c_val and x_unit == c_unit for x_val, x_unit in all_ctx_nums)
        # Does the same unit exist in any context (confirming related topic)?
        has_same_unit = any(x_unit == c_unit for _, x_unit in all_ctx_nums)
        if has_same_unit and not has_match:
            contradicted.append((c_val, c_unit))

    return contradicted

_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "of", "in", "to",
    "for", "with", "on", "at", "from", "by", "as", "into", "through",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
    "it", "its", "this", "that", "these", "those",
})


def _tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r'\b\w+\b', text.lower()) if w not in _STOP_WORDS and len(w) > 1}


def decompose_claims(response_text: str) -> list[dict]:
    if not response_text or not response_text.strip():
        return []

    sentences = _SENTENCE_SPLIT.split(response_text.strip())
    claims = []

    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if len(sentence) >= _MIN_CLAIM_LENGTH:
            claims.append({
                "claim_id": f"c{i + 1}",
                "text": sentence,
            })

    return claims


def verify_claims(
    claims: list[dict],
    contexts: list[dict],
    query: str = "",
) -> dict:
    if not claims:
        return {"claims": [], "supported_pct": 0.0, "unsupported_claims": [], "has_number_contradictions": False}

    verified_claims = []
    unsupported_ids = []
    supported_count = 0
    partial_count = 0
    any_number_contradiction = False

    for claim in claims:
        claim_text = claim["text"].lower()
        best_match = _find_best_evidence(claim_text, contexts)

        # Check for number contradictions even when text similarity is high
        has_contradiction = len(_find_contradicted_numbers(claim_text, contexts, query)) > 0
        if has_contradiction:
            any_number_contradiction = True

        if has_contradiction:
            support = "unsupported"
            unsupported_ids.append(claim["claim_id"])
        elif best_match["ratio"] >= 0.6:
            support = "supported"
            supported_count += 1
        elif best_match["ratio"] >= 0.4:
            support = "partially_supported"
            partial_count += 1
        else:
            support = "unsupported"
            unsupported_ids.append(claim["claim_id"])

        evidence = []
        if best_match["context_id"] is not None and best_match["ratio"] >= 0.4:
            evidence.append({
                "context_id": best_match["context_id"],
                "span_start": best_match["span_start"],
                "span_end": best_match["span_end"],
                "quote": best_match["quote"],
            })

        verified_claims.append({
            "claim_id": claim["claim_id"],
            "text": claim["text"],
            "support": support,
            "evidence": evidence,
        })

    total = len(claims)
    supported_pct = (supported_count + 0.5 * partial_count) / total if total > 0 else 0.0

    return {
        "claims": verified_claims,
        "supported_pct": round(supported_pct, 4),
        "unsupported_claims": unsupported_ids,
        "has_number_contradictions": any_number_contradiction,
    }


def compute_context_coverage(claim_results: dict, total_contexts: int) -> float:
    if not claim_results or total_contexts == 0:
        return 0.0

    used_context_ids = set()
    for claim in claim_results.get("claims", []):
        for evidence in claim.get("evidence", []):
            used_context_ids.add(evidence["context_id"])

    return len(used_context_ids) / total_contexts


def _token_overlap(claim_text: str, ctx_text: str) -> float:
    claim_tokens = _tokenize(claim_text)
    ctx_tokens = _tokenize(ctx_text)
    if not claim_tokens:
        return 0.0
    return len(claim_tokens & ctx_tokens) / len(claim_tokens)


def _find_best_evidence(claim_text: str, contexts: list[dict]) -> dict:
    best = {
        "context_id": None,
        "span_start": 0,
        "span_end": 0,
        "quote": "",
        "ratio": 0.0,
    }

    for ctx in contexts:
        ctx_id = ctx.get("id", "unknown")
        ctx_text = ctx.get("text", "").lower()

        if not ctx_text:
            continue

        token_score = _token_overlap(claim_text, ctx_text)
        if token_score < 0.2:
            continue

        if claim_text in ctx_text:
            start = ctx_text.index(claim_text)
            original_text = ctx.get("text", "")
            quote = original_text[start:start + len(claim_text)]
            if 1.0 > best["ratio"]:
                best = {
                    "context_id": ctx_id,
                    "span_start": start,
                    "span_end": start + len(claim_text),
                    "quote": quote,
                    "ratio": 1.0,
                }
            continue

        span_start, span_end, quote, seq_ratio = _find_best_span(claim_text, ctx.get("text", ""))
        combined = 0.6 * seq_ratio + 0.4 * token_score
        if combined > best["ratio"]:
            best = {
                "context_id": ctx_id,
                "span_start": span_start,
                "span_end": span_end,
                "quote": quote,
                "ratio": combined,
            }

    return best


def _find_best_span(claim_text: str, context_text: str) -> tuple[int, int, str, float]:
    claim_lower = claim_text.lower()
    ctx_lower = context_text.lower()

    window_size = len(claim_lower)
    if window_size == 0 or len(ctx_lower) == 0:
        return 0, 0, "", 0.0

    best_ratio = 0.0
    best_start = 0
    best_end = 0

    step = max(1, window_size // 4)

    for start in range(0, max(1, len(ctx_lower) - window_size // 2), step):
        end = min(start + window_size + window_size // 2, len(ctx_lower))
        window = ctx_lower[start:end]
        ratio = SequenceMatcher(None, claim_lower, window).ratio()

        if ratio > best_ratio:
            best_ratio = ratio
            best_start = start
            best_end = end

    quote = context_text[best_start:best_end]
    return best_start, best_end, quote, best_ratio
