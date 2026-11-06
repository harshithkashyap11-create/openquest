"""Validate AI quotations against the cited block, without replacing evidence."""

import re

from app.accessbridge.domain import AdaptedLesson, VerificationCheck


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def validate_evidence(
    check: VerificationCheck, adaptation: AdaptedLesson
) -> VerificationCheck:
    if check.status != "PASS":
        return check.model_copy(deep=True)
    block = next(
        (block for block in adaptation.blocks if block.block_id == check.block_id), None
    )
    quote = normalize_whitespace(check.evidence)
    if block is None or not quote or quote not in normalize_whitespace(block.content):
        return check.model_copy(
            update={
                "status": "NEEDS_REVIEW",
                "reason": "evidence_not_found",
                "explanation": check.explanation
                + " The quotation was not found in the cited adapted block; the original evidence is retained.",
            },
            deep=True,
        )
    return check.model_copy(deep=True)
