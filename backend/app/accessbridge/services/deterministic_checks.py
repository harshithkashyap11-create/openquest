"""Catalog-driven executable checks over the actual saved adaptation content.

These checks establish measurable properties. Metadata coverage, vocabulary,
word counts and quotation presence do not establish educational equivalence.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.accessbridge.domain import (
    AdaptedLesson,
    LearnerProfile,
    LessonAnalysis,
    SourceLesson,
    VerificationCheck,
)

CATALOG_PATH = Path(__file__).resolve().parents[1] / "rules/check_catalog.json"
REGISTRY = {}


def register(*identifiers):
    def decorator(function):
        for identifier in identifiers:
            if identifier in REGISTRY:
                raise ValueError(
                    f"Duplicate deterministic check registration: {identifier}"
                )
            REGISTRY[identifier] = function
        return function

    return decorator


def normalize(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


def has_term(text, term):
    return bool(
        re.search(
            r"(?<!\w)" + re.escape(normalize(term)).replace(r"\ ", r"\s+") + r"(?!\w)",
            normalize(text),
        )
    )


@dataclass
class Context:
    source: SourceLesson
    profile: LearnerProfile
    analysis: LessonAnalysis
    adaptation: AdaptedLesson

    @property
    def text(self):
        return "\n".join(block.content for block in self.adaptation.blocks)

    @property
    def student_text(self):
        return (
            self.adaptation.title
            + "\n"
            + self.text
            + "\n"
            + self.adaptation.narration_script
        )

    def blocks(self, *kinds):
        return [block for block in self.adaptation.blocks if block.block_type in kinds]

    def parameter(self, name, default):
        values = [
            requirement.parameters[name]
            for requirement in self.profile.accommodation_requirements
            if name in requirement.parameters
        ]
        return values[0] if values else default

    def vocab(self):
        return list(
            dict.fromkeys(
                self.analysis.important_vocabulary
                + [
                    term
                    for objective in self.analysis.learning_objectives
                    for term in objective.required_vocabulary
                ]
            )
        )


def outcome(passed, explanation, evidence="", block_id=None, failure="FAIL"):
    return ("PASS" if passed else failure, explanation, evidence, block_id)


@register("DET-STRUCT-001", "DET-READ-001")
def headings(ctx):
    blocks = ctx.blocks("heading")
    minimum = int(ctx.parameter("min_headings", 1))
    return outcome(
        len(blocks) >= minimum,
        f"Found {len(blocks)} heading blocks; configured minimum {minimum}. Descriptiveness requires semantic review.",
        "; ".join(block.content for block in blocks),
        blocks[0].block_id if blocks else None,
    )


@register("DET-STRUCT-002", "DET-READ-005", "DET-VIS-001", "DET-VIS-002", "DET-VIS-007")
def exported_presentation(ctx):
    # These are exporter properties, not properties of plain text DTOs. Do not
    # invent a PASS before the HTML renderer has produced an actual artifact.
    return (
        "NEEDS_REVIEW",
        "This check requires the rendered HTML artifact. Export templates enforce semantic structure and readable type; inspect the actual export and assistive technology reading order.",
        "Not evaluated against an HTML artifact in this content report.",
        None,
    )


@register("DET-STRUCT-003", "DET-READ-004")
def segmentation(ctx):
    limit = int(ctx.parameter("max_paragraph_words", 90))
    counts = [
        (block.block_id, len(block.content.split()))
        for block in ctx.blocks("paragraph")
    ]
    over = [(identifier, count) for identifier, count in counts if count > limit]
    return outcome(
        not over,
        f"Configured paragraph limit {limit} words; word count is a reading-structure signal, not a readability guarantee.",
        "; ".join(f"{identifier}: {count} words" for identifier, count in counts),
        over[0][0] if over else None,
        "WARN",
    )


@register("DET-STRUCT-004", "DET-VIS-008")
def sequence(ctx):
    indices = [block.order_index for block in ctx.adaptation.blocks]
    identifiers = [block.block_id for block in ctx.adaptation.blocks]
    valid = (
        len(identifiers) == len(set(identifiers))
        and indices == sorted(set(indices))
        and all(index >= 0 for index in indices)
    )
    return outcome(
        valid,
        "Block identifiers must be unique and their nonnegative order indices strictly increasing.",
        str(indices),
    )


@register("DET-STRUCT-005")
def nonempty(ctx):
    invalid = [
        block.block_id for block in ctx.adaptation.blocks if not block.content.strip()
    ]
    return outcome(
        bool(ctx.adaptation.blocks)
        and not invalid
        and bool(ctx.adaptation.title.strip()),
        "All essential blocks and the lesson title must contain text.",
        ", ".join(invalid),
    )


@register("DET-STRUCT-006")
def source_references(ctx):
    known = {block.block_id for block in ctx.source.blocks}
    invalid = [
        block.block_id
        for block in ctx.adaptation.blocks
        if not block.source_block_ids or not set(block.source_block_ids).issubset(known)
    ]
    return outcome(
        not invalid,
        "Every generated block must cite valid original source blocks.",
        ", ".join(invalid),
        invalid[0] if invalid else None,
    )


@register("DET-STRUCT-007")
def duplicates(ctx):
    groups = [
        [block.block_id for block in ctx.source.blocks],
        [block.block_id for block in ctx.adaptation.blocks],
        [objective.objective_id for objective in ctx.analysis.learning_objectives],
    ]
    return outcome(
        all(len(group) == len(set(group)) for group in groups),
        "Source blocks, adapted blocks and learning objectives must have unique identifiers in their own scopes.",
    )


@register("DET-READ-002")
def glossary(ctx):
    blocks = ctx.blocks("glossary")
    minimum = min(int(ctx.parameter("min_glossary_terms", 1)), max(len(ctx.vocab()), 1))
    found = [
        term
        for term in ctx.vocab()
        if any(has_term(block.content, term) for block in blocks)
    ]
    return outcome(
        bool(blocks) and len(found) >= minimum,
        f"Glossary represents {len(found)} required terms; configured minimum {minimum}. Definition quality needs semantic review.",
        "; ".join(found),
        blocks[0].block_id if blocks else None,
    )


@register("DET-READ-003", "DET-CONTENT-002")
def vocabulary(ctx):
    missing = [term for term in ctx.vocab() if not has_term(ctx.text, term)]
    return outcome(
        not missing,
        "Essential vocabulary is matched as whole terms in instructional blocks; narration alone cannot hide an omission.",
        "Missing: " + ", ".join(missing)
        if missing
        else "Retained: " + ", ".join(ctx.vocab()),
    )


@register("DET-READ-006")
def objectives_mapped(ctx):
    missing = [
        objective.objective_id
        for objective in ctx.analysis.learning_objectives
        if not any(
            objective.objective_id in block.objective_ids
            for block in ctx.adaptation.blocks
        )
    ]
    return outcome(
        not missing,
        "Each objective needs at least one candidate instructional block. Mapping alone does not prove objective preservation.",
        "Unmapped: " + ", ".join(missing)
        if missing
        else "All objectives have candidate blocks.",
    )


@register("DET-ATTN-001", "DET-ATTN-005")
def numbered_activities(ctx):
    blocks = ctx.blocks("activity")
    source_activities = [
        block for block in ctx.source.blocks if block.block_type == "activity"
    ]
    if not source_activities and not blocks:
        return outcome(
            True, "The source contains no activity requiring a numbered sequence."
        )
    minimum = min(
        int(ctx.parameter("min_activity_steps", 2)), max(len(source_activities), 2)
    )
    numbers = []
    for block in blocks:
        numbers.extend(
            int(match)
            for match in re.findall(
                r"(?:^|\n)\s*(?:step\s+)?(\d+)[.)\s:-]+", block.content, re.IGNORECASE
            )
        )
    valid = len(numbers) >= minimum and numbers == list(range(1, len(numbers) + 1))
    return outcome(
        valid,
        f"Activity instructions must form consecutive numbered steps; configured minimum {minimum}. Semantic review assesses meaningful order.",
        f"Recognized step numbers: {numbers}",
        blocks[0].block_id if blocks else None,
    )


@register("DET-ATTN-002")
def checkpoints(ctx):
    blocks = ctx.blocks("checkpoint")
    needed = int(ctx.parameter("min_checkpoints", 1))
    return outcome(
        len(blocks) >= needed,
        f"Found {len(blocks)} explicit progress-checkpoint blocks; configured minimum {needed}.",
        "; ".join(block.content for block in blocks),
        blocks[0].block_id if blocks else None,
    )


@register("DET-ATTN-003")
def task_instructions(ctx):
    blocks = ctx.blocks("activity")
    invalid = [block.block_id for block in blocks if len(block.content.split()) < 3]
    required = any(block.block_type == "activity" for block in ctx.source.blocks)
    return outcome(
        (bool(blocks) or not required) and not invalid,
        "Required activity blocks must contain explicit nonempty instructions; educational clarity needs semantic review.",
        ", ".join(invalid),
    )


@register("DET-ATTN-004")
def materials(ctx):
    required = any(block.block_type == "materials" for block in ctx.source.blocks)
    blocks = ctx.blocks("materials")
    return outcome(
        not required or bool(blocks),
        "An explicit materials block is required when materials are listed in the source.",
        "; ".join(block.content for block in blocks),
        blocks[0].block_id if blocks else None,
    )


@register("DET-ATTN-006")
def task_length(ctx):
    limit = int(ctx.parameter("max_activity_words", 45))
    too_long = [
        block for block in ctx.blocks("activity") if len(block.content.split()) > limit
    ]
    return outcome(
        not too_long,
        f"Activity chunks are checked against the profile's {limit}-word limit; short text alone does not establish quality.",
        "; ".join(
            f"{block.block_id}: {len(block.content.split())} words"
            for block in too_long
        ),
        too_long[0].block_id if too_long else None,
        "WARN",
    )


@register("DET-ATTN-007")
def task_objectives(ctx):
    invalid = [block for block in ctx.blocks("activity") if not block.objective_ids]
    return outcome(
        not invalid,
        "Each adapted activity needs a mapped original learning objective.",
        ", ".join(block.block_id for block in invalid),
        invalid[0].block_id if invalid else None,
    )


@register("DET-VIS-003")
def diagram_alternatives(ctx):
    source = [
        block
        for block in ctx.source.blocks
        if block.block_type == "diagram" or "diagram" in block.text.casefold()
    ]
    if not source:
        return outcome(
            True,
            "The parsed source contains no diagram references. Source images are not interpreted.",
        )
    mapped = [
        block
        for block in ctx.blocks("diagram")
        if set(block.source_block_ids).intersection({item.block_id for item in source})
    ]
    if not mapped:
        return outcome(
            False,
            "A source diagram reference requires a mapped textual alternative or explicit teacher review.",
        )
    flagged = [block for block in mapped if block.teacher_review_suggested]
    if flagged:
        return (
            "NEEDS_REVIEW",
            "The source diagram cannot be interpreted automatically; the generated description is explicitly flagged for teacher review.",
            flagged[0].content,
            flagged[0].block_id,
        )
    minimum = int(ctx.parameter("min_diagram_words", 20))
    return outcome(
        all(len(block.content.split()) >= minimum for block in mapped),
        f"Diagram alternatives meet the configured {minimum}-word structural minimum. Scientific relationships require semantic review.",
        mapped[0].content,
        mapped[0].block_id,
    )


@register("DET-VIS-004")
def narration(ctx):
    minimum = int(ctx.parameter("min_narration_words", 30))
    count = len(ctx.adaptation.narration_script.split())
    return outcome(
        count >= minimum,
        f"Narration contains {count} words; configured minimum {minimum}. This is a script, not recorded audio.",
        f"{count} words",
    )


@register("DET-VIS-005")
def narration_coverage(ctx):
    missing = [
        term
        for term in ctx.vocab()
        if not has_term(ctx.adaptation.narration_script, term)
    ]
    return outcome(
        not missing,
        "Narration must retain essential terminology. Full section and objective coverage requires independent semantic review.",
        "Missing from narration: " + ", ".join(missing)
        if missing
        else "Essential terminology is present in the narration.",
    )


@register("DET-VIS-006")
def visual_instructions(ctx):
    pattern = r"\b(?:look at|follow|click|see|refer to|use|choose|select)\b[^.!?\n]{0,50}\b(?:red|blue|green|yellow|left|right|above|below)\s+(?:arrow|box|circle|picture|diagram|button|line)\b"
    found = re.search(pattern, ctx.text, re.IGNORECASE)
    return outcome(
        not found,
        "Obvious color-only or positional instructions require human review; this pattern cannot determine every nonvisual dependency.",
        found.group(0) if found else "No configured color-only pattern detected.",
        failure="NEEDS_REVIEW",
    )


# Quantities are paired with meaningful units/nouns, so list numbering is ignored.
QUANTITY = re.compile(
    r"(?<![\w.])(?P<number>\d+(?:\.\d+)?)\s*(?P<unit>°\s*[CF]|degrees?\s*(?:celsius|fahrenheit)|(?:milli|centi|kilo)?met(?:er|re)s?|mm|cm|km|mL|ml|lit(?:er|re)s?|kg|grams?|mg|minutes?|mins?|hours?|hrs?|seconds?|secs?|days?|weeks?|plants?|drops?|cups?|%)(?!\w)",
    re.IGNORECASE,
)


def quantities(text):
    aliases = {
        "mins": "minute",
        "min": "minute",
        "minutes": "minute",
        "secs": "second",
        "sec": "second",
        "seconds": "second",
        "hrs": "hour",
        "hr": "hour",
        "hours": "hour",
        "days": "day",
        "weeks": "week",
        "plants": "plant",
        "drops": "drop",
        "cups": "cup",
        "degrees celsius": "°c",
        "degree celsius": "°c",
        "degrees fahrenheit": "°f",
        "degree fahrenheit": "°f",
        "milliliters": "ml",
        "millilitres": "ml",
    }
    result = set()
    for match in QUANTITY.finditer(text):
        unit = normalize(match["unit"]).replace("° ", "°")
        result.add((float(match["number"]), aliases.get(unit, unit)))
    return result


@register("DET-CONTENT-001")
def numeric_integrity(ctx):
    original = quantities("\n".join(block.text for block in ctx.source.blocks))
    current = quantities(ctx.text)
    missing = original - current
    added = current - original
    return outcome(
        not missing,
        "Meaningful source quantities with units must be retained; activity numbering is excluded. New quantities require semantic accuracy review.",
        f"Missing or changed quantities: {sorted(missing)}. Additional quantities for review: {sorted(added)}.",
    )


@register("DET-CONTENT-003")
def safety(ctx):
    original, ambiguous = [], []
    for block in ctx.source.blocks:
        negative = bool(
            re.search(r"\b(?:do not|don't|never)\b", block.text, re.IGNORECASE)
        )
        explicit = block.block_type == "safety" or bool(
            re.search(
                r"\b(?:caution|warning|safety|hazard|toxic|poison|flammable|fumes|burns?|sharp|goggles|protective gloves)\b",
                block.text,
                re.IGNORECASE,
            )
        )
        hazardous_action = negative and bool(
            re.search(
                r"\b(?:taste|eat|drink|inhale|touch|mix|heat|cut|chemical|electric|flame|directly at the sun)\b",
                block.text,
                re.IGNORECASE,
            )
        )
        editorial = bool(
            re.search(
                r"\b(?:invent|fabricate|source description|supplied details)\b",
                block.text,
                re.IGNORECASE,
            )
        )
        if explicit or hazardous_action:
            original.append(block)
        elif negative and not editorial:
            ambiguous.append(block.block_id)
    missing, paraphrased = [], []
    for block in original:
        if normalize(block.text) in normalize(ctx.text):
            continue
        candidates = [
            item
            for item in ctx.adaptation.blocks
            if block.block_id in item.source_block_ids and item.block_type == "safety"
        ]
        if candidates:
            paraphrased.append(block.block_id)
        else:
            missing.append(block.block_id)
    if missing:
        return outcome(
            False,
            "Original safety guidance has no preserved text or mapped safety block.",
            "Missing safety: " + ", ".join(missing),
        )
    if paraphrased or ambiguous:
        return (
            "NEEDS_REVIEW",
            "Safety guidance is paraphrased or a negative source instruction has ambiguous safety relevance; confirm the intended precaution through independent semantic or teacher review.",
            ", ".join(paraphrased + ambiguous),
            None,
        )
    return outcome(
        True,
        "All identified source safety instructions are preserved verbatim; new activity safety requires semantic review.",
        f"{len(original)} original safety instruction blocks",
    )


@register("DET-CONTENT-004")
def label_leakage(ctx):
    labels = r"\b(?:dyslex(?:ia|ic)|adhd|disabilit(?:y|ies)|iep|special[ -]needs|screen[ -]reader support|reading (?:and literacy )?support|attention (?:and executive.function )?support|visual.access support|learner_(?:reading|attention|visual))\b"
    match = re.search(labels, ctx.student_text, re.IGNORECASE)
    # Catalog names are also teacher metadata and must not appear in student material.
    leaked_name = bool(
        ctx.profile.teacher_visible_name
        and normalize(ctx.profile.teacher_visible_name) in normalize(ctx.student_text)
    )
    return outcome(
        not match and not leaked_name,
        "Student-facing lesson, title and narration must not disclose diagnosis, IEP or profile labels. Teacher metadata is excluded.",
        match.group(0)
        if match
        else ctx.profile.teacher_visible_name
        if leaked_name
        else "No configured label detected.",
    )


@register("DET-CONTENT-005")
def section_coverage(ctx):
    needed = [
        block
        for block in ctx.source.blocks
        if block.block_type
        in {"paragraph", "activity", "question", "safety", "diagram", "materials"}
        and normalize(block.source_heading or "").rstrip(":") != "learning objectives"
    ]
    mapped = {
        identifier
        for block in ctx.adaptation.blocks
        for identifier in block.source_block_ids
    }
    missing = [block.block_id for block in needed if block.block_id not in mapped]
    return outcome(
        not missing,
        "Original explanations, activities, assessments, materials, safety notes and diagram descriptions need candidate source mappings. Mappings do not establish substantive coverage.",
        "Unmapped original sections: " + ", ".join(missing)
        if missing
        else "All essential source blocks have candidate mappings.",
    )


@register("DET-CONTENT-006")
def objective_references(ctx):
    known = {objective.objective_id for objective in ctx.analysis.learning_objectives}
    invalid = [
        (block.block_id, identifier)
        for block in ctx.adaptation.blocks
        for identifier in block.objective_ids
        if identifier not in known
    ]
    return outcome(
        not invalid,
        "Every adapted objective reference must exist in the original analysis.",
        str(invalid),
        invalid[0][0] if invalid else None,
    )


@register("DET-CONTENT-007")
def accommodation_references(ctx):
    known = {item.accommodation_id for item in ctx.profile.accommodation_requirements}
    invalid = [
        (block.block_id, identifier)
        for block in ctx.adaptation.blocks
        for identifier in block.accommodation_ids
        if identifier not in known
    ]
    return outcome(
        not invalid,
        "Every accommodation reference must belong to the selected profile.",
        str(invalid),
        invalid[0][0] if invalid else None,
    )


@register("DET-CONTENT-008")
def named_entities(ctx):
    if ctx.analysis.named_entities is None:
        return (
            "NEEDS_REVIEW",
            "Named-entity extraction was not available for this analysis; review the source names manually.",
            "",
            None,
        )
    missing = [
        name for name in ctx.analysis.named_entities if not has_term(ctx.text, name)
    ]
    return outcome(
        not missing,
        "Checks source-grounded names identified by analysis; human review is still needed because extraction can miss names.",
        "Missing: " + ", ".join(missing)
        if missing
        else "All identified names are present.",
    )


@register("DET-SECURITY-001")
def markup(ctx):
    found = re.search(
        r"<\s*/?\s*(?:script|iframe|object|embed|style|svg|img|a|div|h[1-6])\b|javascript\s*:",
        ctx.student_text,
        re.IGNORECASE,
    )
    return outcome(
        not found,
        "Student content is plain text; active markup and script URLs require removal. Exporters separately escape all untrusted text.",
        found.group(0) if found else "No configured active markup detected.",
    )


def load_catalog():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    identifiers = [item["check_id"] for item in catalog]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate check IDs in deterministic catalog")
    unknown = set(identifiers) - REGISTRY.keys()
    if unknown:
        raise ValueError(
            f"Catalog checks have no registered evaluator: {sorted(unknown)}"
        )
    if any(
        item["severity"] not in {"MUST", "SHOULD"} or item["method"] != "deterministic"
        for item in catalog
    ):
        raise ValueError("Invalid deterministic catalog severity or method")
    return catalog


def deterministic_checks(source, profile, analysis, adaptation):
    ctx = Context(source, profile, analysis, adaptation)
    requirements = {
        item.accommodation_id: item for item in profile.accommodation_requirements
    }
    checks = []
    for rule in load_catalog():
        applicable = [
            identifier
            for identifier in rule["accommodation_ids"]
            if identifier in requirements
        ]
        if rule["accommodation_ids"] and not applicable:
            continue
        status, explanation, evidence, block_id = REGISTRY[rule["check_id"]](ctx)
        severity = rule["severity"]
        # A catalog stylistic SHOULD stays SHOULD. Profiles may soften a MUST.
        if applicable and all(
            requirements[identifier].severity == "SHOULD" for identifier in applicable
        ):
            severity = "SHOULD"
        if status == "FAIL" and severity == "SHOULD":
            status = "WARN"
        checks.append(
            VerificationCheck(
                check_id=rule["check_id"],
                accommodation_id=applicable[0] if applicable else None,
                method="deterministic",
                severity=severity,
                status=status,
                block_id=block_id,
                evidence=evidence,
                explanation=rule["title"] + ": " + explanation,
            )
        )
    return checks
