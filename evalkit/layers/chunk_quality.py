"""
Layer D.1: Proactive Chunk Quality Evaluation — from EVALKIT_MASTER_SPEC_v2.md Section 6.
Evaluates chunk quality BEFORE indexing. Runs via POST /v1/evaluate/chunks.
"""
import re
import random
from evalkit.config import settings
from evalkit.models.enums import ChunkQuality

_SENTENCE_END = re.compile(r'[.!?][\s]|[.!?]$')
_BROKEN_START = re.compile(r'^[a-z]')
_BROKEN_END = re.compile(r'[a-zA-Z,;:]$')


def evaluate_chunks(
    chunks: list[dict],
    sample_size: int = 20,
    domain: str | None = None,
    seed: int = 42,
) -> dict:
    """Evaluate chunk quality with boundary, density, and coherence checks."""
    if not chunks:
        return _empty_result(0)

    rng = random.Random(seed)
    sample = rng.sample(chunks, sample_size) if len(chunks) > sample_size else chunks
    issues = []

    for chunk in sample:
        chunk_id = chunk.get("id", "unknown")
        text = chunk.get("text", "")

        boundary_issue = _check_sentence_boundaries(chunk_id, text)
        if boundary_issue:
            issues.append(boundary_issue)

        density_issue = _check_information_density(chunk_id, text)
        if density_issue:
            issues.append(density_issue)

        coherence_issue = _check_coherence_heuristic(chunk_id, text)
        if coherence_issue:
            issues.append(coherence_issue)

    boundary_issues = sum(1 for i in issues if i["issue"] == "CHUNK_BOUNDARY_BROKEN")
    coherence_issues = sum(1 for i in issues if i["issue"] == "CHUNK_INCOHERENT")
    density_issues = sum(1 for i in issues if i["issue"] in ("CHUNK_TOO_SPARSE", "CHUNK_TOO_DENSE"))

    issue_rate = len(issues) / len(sample) if sample else 0
    score = max(0.0, 1.0 - issue_rate)

    if score >= 0.8:
        quality = ChunkQuality.GOOD
    elif score >= 0.5:
        quality = ChunkQuality.ACCEPTABLE
    else:
        quality = ChunkQuality.POOR

    return {
        "overall_quality": quality.value,
        "score": round(score, 2),
        "issues": issues,
        "summary": {
            "chunks_evaluated": len(sample),
            "boundary_issues": boundary_issues,
            "coherence_issues": coherence_issues,
            "density_issues": density_issues,
        },
    }


def _check_sentence_boundaries(chunk_id: str, text: str) -> dict | None:
    text = text.strip()
    if not text:
        return None

    starts_broken = bool(_BROKEN_START.match(text))
    ends_broken = bool(_BROKEN_END.search(text)) and not _SENTENCE_END.search(text[-2:] if len(text) >= 2 else text)

    if starts_broken or ends_broken:
        detail_parts = []
        if starts_broken:
            preview = text[:40] + "..." if len(text) > 40 else text
            detail_parts.append(f"starts mid-sentence: '{preview}'")
        if ends_broken:
            preview = "..." + text[-40:] if len(text) > 40 else text
            detail_parts.append(f"ends mid-sentence: '{preview}'")

        return {
            "chunk_id": chunk_id,
            "issue": "CHUNK_BOUNDARY_BROKEN",
            "detail": "Sentence boundary broken: " + "; ".join(detail_parts),
            "severity": "major",
            "fix": "Adjust chunk boundary to nearest sentence end",
        }

    return None


def _check_information_density(chunk_id: str, text: str) -> dict | None:
    text = text.strip()
    word_count = len(text.split())

    if word_count < settings.chunk_min_words:
        return {
            "chunk_id": chunk_id,
            "issue": "CHUNK_TOO_SPARSE",
            "detail": f"Chunk has only {word_count} words (min: {settings.chunk_min_words}). Too little information for effective retrieval.",
            "severity": "minor",
            "fix": "Merge with adjacent chunk or increase chunk size",
        }

    if word_count > settings.chunk_max_words:
        return {
            "chunk_id": chunk_id,
            "issue": "CHUNK_TOO_DENSE",
            "detail": f"Chunk has {word_count} words. Too much information may reduce retrieval precision.",
            "severity": "minor",
            "fix": "Split into smaller chunks at natural boundaries",
        }

    return None


def _check_coherence_heuristic(chunk_id: str, text: str) -> dict | None:
    text = text.strip()
    if not text:
        return None

    dangling_starters = [
        "this ", "these ", "those ", "that ", "it ", "its ",
        "he ", "she ", "they ", "them ", "his ", "her ", "their ",
        "the above", "the following", "as mentioned",
        "furthermore,", "moreover,", "additionally,",
        "however,", "therefore,", "consequently,",
    ]

    lower = text.lower()
    starts_with_reference = any(lower.startswith(starter) for starter in dangling_starters)

    if starts_with_reference and len(text.split()) < 50:
        return {
            "chunk_id": chunk_id,
            "issue": "CHUNK_INCOHERENT",
            "detail": f"Chunk starts with a dangling reference ('{text.split()[0]}...') that requires prior context to understand",
            "severity": "minor",
            "fix": "Include preceding context or rephrase the chunk opening",
        }

    return None


def _empty_result(count: int) -> dict:
    return {
        "overall_quality": ChunkQuality.GOOD.value,
        "score": 1.0,
        "issues": [],
        "summary": {
            "chunks_evaluated": count,
            "boundary_issues": 0,
            "coherence_issues": 0,
            "density_issues": 0,
        },
    }
