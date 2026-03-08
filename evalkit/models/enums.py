"""EvalKit enums — from EVALKIT_MASTER_SPEC_v2.md Section 6."""
from enum import Enum


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"


class Severity(str, Enum):
    BLOCKER = "blocker"
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    NONE = "none"


class RootCauseCode(str, Enum):
    # Input issues
    INPUT_INVALID = "INPUT_INVALID"
    NO_CONTEXT_PROVIDED = "NO_CONTEXT_PROVIDED"
    NO_RESPONSE_GENERATED = "NO_RESPONSE_GENERATED"
    # Answerability
    SHOULD_HAVE_REFUSED = "SHOULD_HAVE_REFUSED"
    FALSE_REFUSAL = "FALSE_REFUSAL"
    # Retrieval
    RETRIEVAL_MISS = "RETRIEVAL_MISS"
    NO_RELEVANT_DOCS_RETRIEVED = "NO_RELEVANT_DOCS_RETRIEVED"
    EXCESSIVE_NOISE = "EXCESSIVE_NOISE"
    # Evidence
    EVIDENCE_NOT_USED = "EVIDENCE_NOT_USED"
    HALLUCINATION = "HALLUCINATION"
    # Generation
    GENERATION_UNFAITHFUL = "GENERATION_UNFAITHFUL"
    OFF_TOPIC_RESPONSE = "OFF_TOPIC_RESPONSE"
    # Chunk-level (Phase 1 proactive)
    CHUNK_BOUNDARY_BROKEN = "CHUNK_BOUNDARY_BROKEN"
    CHUNK_INCOHERENT = "CHUNK_INCOHERENT"
    CHUNK_TOO_SPARSE = "CHUNK_TOO_SPARSE"
    CHUNK_TOO_DENSE = "CHUNK_TOO_DENSE"
    # Phase 2 placeholders (define enum now, implement later)
    EMBEDDING_DOMAIN_MISMATCH = "EMBEDDING_DOMAIN_MISMATCH"
    EMBEDDING_DRIFT = "EMBEDDING_DRIFT"
    RERANKER_DROPPED_EVIDENCE = "RERANKER_DROPPED_EVIDENCE"
    # All good
    PASS = "PASS"


class AnswerabilityClass(str, Enum):
    ANSWERABLE = "answerable"
    PARTIALLY_ANSWERABLE = "partially_answerable"
    UNANSWERABLE = "unanswerable"


class JudgeMode(str, Enum):
    SINGLE = "single"
    MULTI = "multi"


class ChunkQuality(str, Enum):
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"


class ErrorCode(str, Enum):
    INVALID_INPUT = "INVALID_INPUT"
    JUDGE_TIMEOUT = "JUDGE_TIMEOUT"
    JUDGE_COST_CAP = "JUDGE_COST_CAP"
    STORAGE_ERROR = "STORAGE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Severity mapping — spec Section 6 (Layer D)
SEVERITY_MAP: dict[str, str] = {
    "INPUT_INVALID": "blocker",
    "NO_CONTEXT_PROVIDED": "blocker",
    "NO_RESPONSE_GENERATED": "blocker",
    "SHOULD_HAVE_REFUSED": "critical",
    "HALLUCINATION": "critical",
    "RETRIEVAL_MISS": "critical",
    "NO_RELEVANT_DOCS_RETRIEVED": "critical",
    "GENERATION_UNFAITHFUL": "major",
    "EVIDENCE_NOT_USED": "major",
    "OFF_TOPIC_RESPONSE": "major",
    "EXCESSIVE_NOISE": "major",
    "FALSE_REFUSAL": "major",
    "CHUNK_BOUNDARY_BROKEN": "major",
    "CHUNK_INCOHERENT": "minor",
    "CHUNK_TOO_SPARSE": "minor",
    "CHUNK_TOO_DENSE": "minor",
    "EMBEDDING_DOMAIN_MISMATCH": "major",
    "EMBEDDING_DRIFT": "major",
    "PASS": "none",
}


def get_severity(root_cause_code: str) -> Severity:
    """Get severity for a root cause code. Returns Severity.MAJOR for unknown codes."""
    return Severity(SEVERITY_MAP.get(root_cause_code, "major"))
