"""Objective candidate mapping is evidence routing, never semantic certification."""

from app.accessbridge.domain import AdaptedLesson, LessonAnalysis, VerificationCheck


def objective_candidates(
    analysis: LessonAnalysis, adaptation: AdaptedLesson
) -> dict[str, list[str]]:
    return {
        objective.objective_id: [
            block.block_id
            for block in adaptation.blocks
            if objective.objective_id in block.objective_ids
        ]
        for objective in analysis.learning_objectives
    }


def objective_mapping_checks(
    analysis: LessonAnalysis, adaptation: AdaptedLesson
) -> list[VerificationCheck]:
    return [
        VerificationCheck(
            check_id="DET-OBJ-MAPPING",
            objective_id=objective_id,
            method="deterministic",
            severity="MUST",
            status="PASS" if candidates else "FAIL",
            block_id=candidates[0] if candidates else None,
            evidence=", ".join(candidates),
            explanation=(
                "Candidate adapted blocks are mapped; independent semantic evaluation must establish substantive coverage."
                if candidates
                else "No adapted lesson block is mapped to this objective."
            ),
        )
        for objective_id, candidates in objective_candidates(
            analysis, adaptation
        ).items()
    ]
