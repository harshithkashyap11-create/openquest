"""AccessBridge verification regressions retained during migration."""
import pytest
from app.accessbridge.domain import (AccommodationRequirement, AdaptationPlan, AdaptedBlock, AdaptedLesson, LearnerProfile, LearningObjective, LessonAnalysis, PlannedTransformation, SemanticReview, SourceBlock, SourceLesson, VerificationCheck)

def context():
    profile = LearnerProfile(
        profile_id="learner_reading",
        teacher_visible_name="Reading Support",
        description="Synthetic reading support",
        accommodation_requirements=[
            AccommodationRequirement(
                accommodation_id="READ-003",
                title="Vocabulary",
                description="Explain essential terms",
                severity="MUST",
                verification_method="hybrid",
                parameters={"min_glossary_terms": 1},
                rationale="Support understanding",
            ),
            AccommodationRequirement(
                accommodation_id="READ-002",
                title="Clarity",
                description="Clear instructions",
                severity="SHOULD",
                verification_method="llm",
                parameters={},
                rationale="Support reading",
            ),
        ],
    )
    source = SourceLesson(
        title="Plant lesson",
        source_filename="lesson.txt",
        source_format="txt",
        blocks=[
            SourceBlock(
                block_id="s1",
                block_type="paragraph",
                text="Plants use water and carbon dioxide with light. Wait 5 minutes at 20 °C.",
                order_index=0,
            ),
            SourceBlock(
                block_id="s2",
                block_type="safety",
                text="Do not taste the plant material.",
                order_index=1,
            ),
            SourceBlock(
                block_id="s3",
                block_type="question",
                text="Why is light needed?",
                order_index=2,
            ),
        ],
    )
    objective = LearningObjective(
        objective_id="OBJ-001",
        description="Describe the necessary inputs for plant food production.",
        source_block_ids=["s1"],
        essential_concepts=["water", "carbon dioxide", "light"],
        required_vocabulary=["water", "carbon dioxide"],
    )
    analysis = LessonAnalysis(
        summary="Plant process",
        title="Plant lesson",
        subject="Science",
        grade_level="Class 6",
        learning_objectives=[objective],
        key_concepts=["light"],
        important_vocabulary=["carbon dioxide"],
        identified_challenges=[],
        analysis_warnings=[],
        plans=[
            AdaptationPlan(
                profile_id=profile.profile_id,
                accommodation_ids=["READ-003", "READ-002"],
                planned_transformations=[
                    PlannedTransformation(
                        accommodation_id="READ-003",
                        source_block_ids=["s1"],
                        instruction="Explain terminology.",
                    )
                ],
                objective_preservation_strategy="Explain every source objective.",
            )
        ],
    )
    adapted = AdaptedLesson(
        lesson_id=source.lesson_id,
        profile_id=profile.profile_id,
        title="Plants make food",
        blocks=[
            AdaptedBlock(
                block_id="a1",
                source_block_ids=["s1"],
                block_type="paragraph",
                content="Plants use water and carbon dioxide with light. Wait 5 minutes at 20 °C.",
                objective_ids=["OBJ-001"],
                accommodation_ids=["READ-002"],
                order_index=0,
                teacher_review_suggested=False,
            ),
            AdaptedBlock(
                block_id="a2",
                source_block_ids=["s1"],
                block_type="glossary",
                content="Carbon dioxide: a gas in air. Water: a liquid.",
                objective_ids=["OBJ-001"],
                accommodation_ids=["READ-003"],
                order_index=1,
                teacher_review_suggested=False,
            ),
            AdaptedBlock(
                block_id="a3",
                source_block_ids=["s2"],
                block_type="safety",
                content="Do not taste the plant material.",
                objective_ids=[],
                accommodation_ids=[],
                order_index=2,
                teacher_review_suggested=False,
            ),
            AdaptedBlock(
                block_id="a4",
                source_block_ids=["s3"],
                block_type="question",
                content="Why is light needed?",
                objective_ids=["OBJ-001"],
                accommodation_ids=[],
                order_index=3,
                teacher_review_suggested=False,
            ),
        ],
        narration_script="Plants use water and carbon dioxide with light.",
    )
    return source, profile, analysis, adapted


def test_positive_evidence_must_match_cited_block_with_whitespace_normalization():
    from app.accessbridge.services.evidence_validator import validate_evidence

    _source, _profile, _analysis, adapted = context()
    valid = VerificationCheck(
        check_id="SEM-OBJ-001",
        objective_id="OBJ-001",
        method="llm",
        status="PASS",
        block_id="a1",
        evidence="Plants use water and\n carbon dioxide with light.",
        explanation="Explains required inputs.",
    )
    assert validate_evidence(valid, adapted).status == "PASS"
    invalid = valid.model_copy(update={"block_id": "a2"})
    checked = validate_evidence(invalid, adapted)
    assert checked.status == "NEEDS_REVIEW" and checked.reason == "evidence_not_found"
    assert checked.evidence == invalid.evidence
    invented = valid.model_copy(update={"evidence": "Plants eat soil."})
    assert validate_evidence(invented, adapted).reason == "evidence_not_found"
    negative = valid.model_copy(
        update={
            "status": "FAIL",
            "evidence": "",
            "explanation": "The objective omits light.",
        }
    )
    assert validate_evidence(negative, adapted).status == "FAIL"


def test_deterministic_checks_catch_loss_numbers_safety_labels_and_references():
    from app.accessbridge.services.verification_engine import deterministic

    source, profile, analysis, adapted = context()
    adapted.blocks[
        0
    ].content = "Plants use light. Wait 7 minutes at 25 °C. This version is for dyslexic students."
    adapted.blocks[0].objective_ids = ["OBJ-MADEUP"]
    adapted.blocks[0].accommodation_ids = ["READ-MADEUP"]
    adapted.blocks = [b for b in adapted.blocks if b.block_id not in {"a2", "a3"}]
    checks = {c.check_id: c for c in deterministic(source, profile, analysis, adapted)}
    for check_id in [
        "DET-CONTENT-001",
        "DET-CONTENT-002",
        "DET-CONTENT-003",
        "DET-CONTENT-004",
        "DET-CONTENT-006",
        "DET-CONTENT-007",
    ]:
        assert checks[check_id].status == "FAIL", check_id
    assert checks["DET-CONTENT-003"].severity == "MUST"


def test_semantic_cannot_overwrite_failures_or_pass_with_missing_evidence():
    from app.accessbridge.services.verification_engine import combine_report, semantic_specs

    source, profile, analysis, adapted = context()
    adapted.blocks[0].content = "Plants use light."
    adapted.blocks = [b for b in adapted.blocks if b.block_id != "a2"]
    specs = semantic_specs(profile, analysis)
    assert any(s["objective_id"] == "OBJ-001" for s in specs)
    assert any(s["accommodation_id"] == "READ-002" for s in specs)
    assert {"SEM-OBJ-002", "SEM-OBJ-004", "SEM-SAFE-001"}.issubset(
        {s["check_id"] for s in specs}
    )
    semantic = SemanticReview(
        checks=[
            VerificationCheck(
                **s,
                method="llm",
                status="PASS",
                block_id="a1",
                evidence="This quotation was invented.",
                explanation="Claimed pass.",
            )
            for s in specs
        ]
    )
    report = combine_report(source, profile, analysis, adapted, semantic)
    assert "DET-CONTENT-002" in report.mandatory_failures
    assert all(c.status == "NEEDS_REVIEW" for c in report.checks if c.method == "llm")
    assert report.requires_teacher_review
    assert not report.semantic_complete
    assert report.adaptation_version == adapted.version
    missing = combine_report(source, profile, analysis, adapted, None)
    assert any(c.reason == "semantic_not_performed" for c in missing.checks)


def test_reference_validation_rejects_invented_source_and_unknown_plan_requirements():
    from app.accessbridge.services.verification_engine import validate_analysis, validate_draft

    source, profile, analysis, adapted = context()
    validate_analysis(source, [profile], analysis)
    validate_draft(source, profile, analysis, adapted)
    adapted.blocks[0].source_block_ids = ["invented"]
    with pytest.raises(ValueError, match="source"):
        validate_draft(source, profile, analysis, adapted)
    analysis.plans[0].accommodation_ids.append("invented")
    with pytest.raises(ValueError, match="accommodation"):
        validate_analysis(source, [profile], analysis)




def test_generation_runs_separate_analysis_transform_and_verification_stages(monkeypatch):
    from app.accessbridge.services.verification_engine import semantic_specs
    from app.services import inclusive_learning, lesson_service
    source, profile, analysis, adaptation = context()
    checks = [dict(spec, method='llm', status='NEEDS_REVIEW', explanation='Teacher review required') for spec in semantic_specs(profile, analysis, adaptation)]
    outputs = [analysis.model_dump_json(), adaptation.model_dump_json(include={'title', 'blocks', 'narration_script'}), SemanticReview(checks=checks).model_dump_json()]
    calls = []
    class FakeClient:
        def complete_json(self, *, prompt, temperature):
            calls.append(prompt)
            return outputs.pop(0)
    monkeypatch.setattr(lesson_service, 'configured_chat', lambda: (FakeClient(), 'test', 'fixture'))
    result = inclusive_learning.generate_adaptation(source.model_dump(mode='json'), profile)
    assert len(calls) == 3
    assert result['bridge_draft']['blocks'][0]['source_block_ids'] == ['s1']
    assert any(f['status'] == 'NEEDS_REVIEW' for f in result['findings'])
