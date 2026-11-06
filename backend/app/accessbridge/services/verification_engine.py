"""Combine measurable checks and independent, evidence-backed AI judgments."""

import json
import re
from pathlib import Path

from app.accessbridge.domain import LearnerProfile, VerificationCheck, VerificationReport
from app.accessbridge.services.assessment import assessment_checks
from app.accessbridge.services.deterministic_checks import deterministic_checks, load_catalog
from app.accessbridge.services.evidence_validator import validate_evidence
from app.accessbridge.services.objective_checker import (
    objective_candidates,
    objective_mapping_checks,
)


def _unique(values, name):
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {name} identifiers")


def load_profiles(path: Path | None = None) -> list[LearnerProfile]:
    catalog_path = path or Path(__file__).resolve().parents[1] / "rules/profiles.json"
    profiles = [
        LearnerProfile.model_validate(item)
        for item in json.loads(catalog_path.read_text(encoding="utf-8"))
    ]
    if not profiles:
        raise ValueError("The accommodation profile catalog is empty")
    _unique([profile.profile_id for profile in profiles], "profile")
    _unique(
        [
            requirement.accommodation_id
            for profile in profiles
            for requirement in profile.accommodation_requirements
        ],
        "accommodation",
    )
    load_catalog()
    return profiles


def validate_analysis(lesson, profiles, analysis) -> None:
    source_ids = {block.block_id for block in lesson.blocks}
    source_text = " ".join(block.text for block in lesson.blocks).casefold()
    for entity in analysis.named_entities or []:
        if not entity.strip() or entity.casefold() not in source_text:
            raise ValueError(
                "Analysis named entity is not present in the source lesson"
            )
    objectives = [objective.objective_id for objective in analysis.learning_objectives]
    _unique(objectives, "objective")
    _unique([profile.profile_id for profile in profiles], "profile")
    for objective in analysis.learning_objectives:
        _unique(objective.source_block_ids, "objective source block")
        if not set(objective.source_block_ids).issubset(source_ids):
            raise ValueError(
                f"Objective {objective.objective_id} references an unknown source block"
            )
    plans = {plan.profile_id: plan for plan in analysis.plans}
    if len(plans) != len(analysis.plans) or set(plans) != {
        profile.profile_id for profile in profiles
    }:
        raise ValueError(
            "Analysis must contain exactly one plan for every selected profile"
        )
    for profile in profiles:
        requirements = [
            item.accommodation_id for item in profile.accommodation_requirements
        ]
        _unique(requirements, "accommodation")
        plan = plans[profile.profile_id]
        _unique(plan.accommodation_ids, "planned accommodation")
        if set(plan.accommodation_ids) != set(requirements):
            raise ValueError(
                "Plan accommodation IDs must match the selected profile requirements"
            )
        for transformation in plan.planned_transformations:
            if transformation.accommodation_id not in requirements:
                raise ValueError(
                    "Planned transformation has an unknown accommodation reference"
                )
            if not set(transformation.source_block_ids).issubset(source_ids):
                raise ValueError(
                    "Planned transformation has an unknown source block reference"
                )


def validate_draft(lesson, profile, analysis, draft) -> None:
    source_ids = {block.block_id for block in lesson.blocks}
    objective_ids = {
        objective.objective_id for objective in analysis.learning_objectives
    }
    accommodation_ids = {
        item.accommodation_id for item in profile.accommodation_requirements
    }
    translations = getattr(draft, "objective_translations", [])
    if translations or getattr(draft, "output_language", "en") != "en":
        translated_ids = [item.objective_id for item in translations]
        if (
            len(translated_ids) != len(set(translated_ids))
            or set(translated_ids) != objective_ids
        ):
            raise ValueError(
                "Translated objective IDs must exactly match the source objectives"
            )
    _unique([block.block_id for block in draft.blocks], "adapted block")
    indices = [block.order_index for block in draft.blocks]
    if indices != sorted(set(indices)):
        raise ValueError("Adapted block order indices must be unique and increasing")
    for block in draft.blocks:
        if not block.source_block_ids or not set(block.source_block_ids).issubset(
            source_ids
        ):
            raise ValueError(
                f"Adapted block {block.block_id} has an invalid source reference"
            )
        if not set(block.objective_ids).issubset(objective_ids):
            raise ValueError(
                f"Adapted block {block.block_id} has an invalid objective reference"
            )
        if not set(block.accommodation_ids).issubset(accommodation_ids):
            raise ValueError(
                f"Adapted block {block.block_id} has an invalid accommodation reference"
            )
        for values in (
            block.source_block_ids,
            block.objective_ids,
            block.accommodation_ids,
        ):
            _unique(values, "block reference")
    if hasattr(draft, "lesson_id") and draft.lesson_id != lesson.lesson_id:
        raise ValueError("Adaptation belongs to a different source lesson")
    if hasattr(draft, "profile_id") and draft.profile_id != profile.profile_id:
        raise ValueError("Adaptation belongs to a different accommodation profile")


def deterministic(lesson, profile, analysis, adaptation) -> list[VerificationCheck]:
    return deterministic_checks(
        lesson, profile, analysis, adaptation
    ) + objective_mapping_checks(analysis, adaptation)


SEMANTIC_REQUIREMENTS = {
    "READ-001": "SEM-READ-001",
    "READ-002": "SEM-READ-001",
    "READ-003": "SEM-READ-002",
    "READ-005": "SEM-OBJ-003",
    "ATTN-001": "SEM-ATTN-001",
    "ATTN-002": "SEM-ATTN-002",
    "ATTN-003": "SEM-ATTN-001",
    "ATTN-004": "SEM-SAFE-001",
    "ATTN-005": "SEM-OBJ-003",
    "VIS-001": "SEM-VIS-001",
    "VIS-002": "SEM-VIS-002",
    "VIS-003": "SEM-VIS-001",
    "VIS-004": "SEM-VIS-001",
}


def semantic_specs(profile, analysis, adaptation=None) -> list[dict]:
    specs = [
        {
            "check_id": "SEM-OBJ-001",
            "objective_id": objective.objective_id,
            "accommodation_id": None,
            "severity": "MUST",
        }
        for objective in analysis.learning_objectives
    ]
    specs.extend(
        {
            "check_id": identifier,
            "objective_id": None,
            "accommodation_id": None,
            "severity": "MUST",
        }
        for identifier in ("SEM-OBJ-002", "SEM-OBJ-003", "SEM-OBJ-004", "SEM-SAFE-001")
    )
    specs.extend(
        {
            "check_id": SEMANTIC_REQUIREMENTS.get(
                requirement.accommodation_id, "SEM-ACCOM-001"
            ),
            "objective_id": None,
            "accommodation_id": requirement.accommodation_id,
            "severity": requirement.severity,
        }
        for requirement in profile.accommodation_requirements
        if requirement.verification_method in {"llm", "hybrid"}
    )
    if adaptation is not None and adaptation.assessment is not None:
        specs.extend(
            {
                "check_id": f"SEM-ASSESS-{qid}",
                "objective_id": None,
                "accommodation_id": None,
                "severity": "MUST",
            }
            for qid in adaptation.assessment.answer_keys
        )
    return specs


def _identity(value):
    return (value.check_id, value.objective_id, value.accommodation_id)


def combine_report(
    lesson, profile, analysis, adaptation, semantic=None
) -> VerificationReport:
    checks = deterministic(lesson, profile, analysis, adaptation) + assessment_checks(
        lesson, adaptation
    )
    if adaptation.output_language != "en":
        pattern = (
            r"[\u0c00-\u0c7f]"
            if adaptation.output_language == "te"
            else r"[\u0900-\u097f]"
        )
        has_script = bool(
            re.search(pattern, " ".join(b.content for b in adaptation.blocks))
        )
        checks.append(
            VerificationCheck(
                check_id="DET-LANGUAGE-001",
                method="deterministic",
                status="PASS" if has_script else "FAIL",
                explanation="The requested script occurs in lesson blocks. This does not establish fluency or educational accuracy."
                if has_script
                else "The lesson blocks do not contain the requested language script.",
            )
        )
        notes = [
            note
            for item in adaptation.objective_translations
            for note in item.uncertainty_notes
        ]
        checks.append(
            VerificationCheck(
                check_id="MANUAL-TRANSLATION",
                method="hybrid",
                status="NEEDS_REVIEW",
                explanation="A native speaker or qualified educator must review translated terminology, concepts, numbers and units. Back-translation is diagnostic only. "
                + " ".join(notes),
            )
        )
    specs = semantic_specs(profile, analysis, adaptation)
    expected = {
        (spec["check_id"], spec["objective_id"], spec["accommodation_id"])
        for spec in specs
    }
    returned = {}
    duplicates = set()
    unexpected = []
    if semantic is not None:
        for item in semantic.checks:
            identity = _identity(item)
            if identity not in expected:
                unexpected.append(item.check_id)
                continue
            if identity in returned:
                duplicates.add(identity)
            returned[identity] = item
    candidates = objective_candidates(analysis, adaptation)
    semantic_results = []
    for spec in specs:
        identity = (spec["check_id"], spec["objective_id"], spec["accommodation_id"])
        item = returned.get(identity)
        if item is None or identity in duplicates:
            item = VerificationCheck(
                **spec,
                method="llm",
                status="NEEDS_REVIEW",
                reason="semantic_duplicate"
                if identity in duplicates
                else "semantic_not_performed",
                explanation="Independent semantic result was duplicated."
                if identity in duplicates
                else "Independent semantic verification has not supplied this required finding.",
            )
        else:
            # The model cannot lower a required severity or claim deterministic authority.
            item = item.model_copy(
                update={"severity": spec["severity"], "method": "llm"}, deep=True
            )
            item = validate_evidence(item, adaptation)
            known = {block.block_id for block in adaptation.blocks}
            if (
                item.block_id is not None
                and item.block_id not in known
                and item.reason != "evidence_not_found"
            ):
                item = item.model_copy(
                    update={
                        "status": "NEEDS_REVIEW",
                        "reason": "invalid_block_reference",
                        "explanation": item.explanation
                        + " The cited block does not exist.",
                    }
                )
            if (
                item.status == "PASS"
                and item.objective_id
                and item.block_id not in candidates[item.objective_id]
            ):
                item = item.model_copy(
                    update={
                        "status": "NEEDS_REVIEW",
                        "reason": "objective_evidence_unmapped",
                        "explanation": item.explanation
                        + " The evidence block is not mapped to this objective.",
                    }
                )
            if item.status == "PASS" and item.accommodation_id:
                block = next(
                    (
                        block
                        for block in adaptation.blocks
                        if block.block_id == item.block_id
                    ),
                    None,
                )
                if (
                    block is None
                    or item.accommodation_id not in block.accommodation_ids
                ):
                    item = item.model_copy(
                        update={
                            "status": "NEEDS_REVIEW",
                            "reason": "accommodation_evidence_unmapped",
                            "explanation": item.explanation
                            + " The evidence block is not mapped to this accommodation.",
                        }
                    )
            if item.status == "FAIL" and not item.explanation.strip():
                item = item.model_copy(
                    update={
                        "status": "NEEDS_REVIEW",
                        "reason": "missing_failure_explanation",
                        "explanation": "A negative semantic finding requires a precise description of the missing or incorrect content.",
                    }
                )
            if item.severity == "SHOULD" and item.status == "FAIL":
                item = item.model_copy(update={"status": "WARN"})
        semantic_results.append(item)
    checks.extend(semantic_results)
    if unexpected:
        checks.append(
            VerificationCheck(
                check_id="SEM-RESPONSE-001",
                method="llm",
                status="NEEDS_REVIEW",
                reason="unexpected_semantic_check",
                explanation="The verifier returned unexpected check IDs or references; those claims were not accepted.",
                evidence=", ".join(unexpected),
            )
        )
    for requirement in profile.accommodation_requirements:
        if not any(
            block.accommodation_ids
            and requirement.accommodation_id in block.accommodation_ids
            for block in adaptation.blocks
        ):
            checks.append(
                VerificationCheck(
                    check_id="DET-ACCOM-MAPPING",
                    accommodation_id=requirement.accommodation_id,
                    method="deterministic",
                    severity=requirement.severity,
                    status="FAIL" if requirement.severity == "MUST" else "WARN",
                    explanation="No adapted instructional block is mapped to this accommodation.",
                )
            )
    if any(block.teacher_review_suggested for block in adaptation.blocks):
        checks.append(
            VerificationCheck(
                check_id="MANUAL-BLOCK-REVIEW",
                method="hybrid",
                severity="SHOULD",
                status="NEEDS_REVIEW",
                block_id=next(
                    block.block_id
                    for block in adaptation.blocks
                    if block.teacher_review_suggested
                ),
                explanation="One or more adapted blocks explicitly request teacher review, including uncertain source descriptions.",
            )
        )
    return VerificationReport(
        adaptation_id=adaptation.adaptation_id,
        adaptation_version=adaptation.version,
        checks=checks,
        original_semantic_checks=[
            item.model_copy(deep=True) for item in semantic.checks
        ]
        if semantic
        else [],
        objectives_evaluated=[
            objective.objective_id for objective in analysis.learning_objectives
        ],
        accommodations_evaluated=[
            requirement.accommodation_id
            for requirement in profile.accommodation_requirements
        ],
        mandatory_failures=list(
            dict.fromkeys(
                check.check_id
                for check in checks
                if check.severity == "MUST" and check.status == "FAIL"
            )
        ),
        warnings=list(
            dict.fromkeys(
                f"{check.check_id}: {check.explanation}"
                for check in checks
                if check.status in {"WARN", "NEEDS_REVIEW"}
            )
        ),
        requires_teacher_review=any(
            check.status in {"FAIL", "WARN", "NEEDS_REVIEW"} for check in checks
        ),
        semantic_complete=semantic is not None
        and not unexpected
        and not duplicates
        and all(item.status != "NEEDS_REVIEW" for item in semantic_results),
    )
