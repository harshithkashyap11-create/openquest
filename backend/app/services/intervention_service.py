from dataclasses import dataclass
import logging
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.models import (
    Diagnosis,
    GroupMember,
    Intervention,
    InterventionAssignment,
    LearningGroup,
    Submission,
)
from app.schemas.interventions import InterventionPersonalization
from app.services.diagnosis_provider import (
    ProviderConfigurationError,
    ProviderError,
    ProviderRateLimited,
)
from app.services.intervention_provider import create_intervention_provider
from app.subject_taxonomy import get_taxonomy, is_follow_up_code

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InterventionTemplate:
    title: str
    learning_objective: str
    explanation: str
    introduction: str
    guided_example: dict[str, str]
    practice_questions: tuple[str, ...]
    expected_answers: tuple[str, ...]
    instructions: str
    hints: tuple[str, ...]


INTERVENTION_TEMPLATES: dict[str, InterventionTemplate] = {
    "M01": InterventionTemplate(
        title="Add Fractions with Common Denominators",
        learning_objective="Add fractions by expressing them in equal-sized parts.",
        explanation=(
            "The denominator names the size of the parts. Adding denominators would "
            "change the size of those parts, so first rewrite both fractions with a "
            "common denominator. Then add only the numerators."
        ),
        introduction="Let's make the fraction pieces the same size before we add.",
        guided_example={
            "question": "Add 1/2 + 1/3.",
            "steps": "Use sixths: 1/2 = 3/6 and 1/3 = 2/6. Add 3 + 2, keeping sixths.",
            "answer": "5/6",
        },
        practice_questions=(
            "Add 1/4 + 1/6.",
            "Add 2/5 + 1/10.",
            "Add 3/4 + 1/8.",
        ),
        expected_answers=("5/12", "1/2", "7/8"),
        instructions=(
            "For each problem, find a common denominator, rewrite both fractions, "
            "and add the numerators. Keep the denominator unchanged."
        ),
        hints=(
            "What is a common multiple of the denominators?",
            "Rewrite both fractions as equal-sized parts first.",
            "Add numerators; do not add denominators.",
        ),
    ),
    "M02": InterventionTemplate(
        title="Compare Fraction Sizes",
        learning_objective="Compare fractions by considering the size of their parts and their value.",
        explanation=(
            "A denominator tells how many equal parts make one whole. When the "
            "numerator is the same, more parts mean each part is smaller. A number "
            "line can show which fraction lies farther to the right."
        ),
        introduction="Let's picture each fraction on a number line from zero to one.",
        guided_example={
            "question": "Which is larger, 1/4 or 1/8?",
            "steps": "Both are one part of a whole. Fourths are larger pieces than eighths, so 1/4 is farther right.",
            "answer": "1/4",
        },
        practice_questions=(
            "Which is larger, 5/6 or 5/8?",
            "Which is larger, 2/3 or 3/5?",
            "Which is larger, 3/8 or 1/2?",
        ),
        expected_answers=("5/6", "2/3", "1/2"),
        instructions=(
            "Sketch a number line from 0 to 1. Place each fraction, or rewrite the "
            "pair with a common denominator, then choose the larger value."
        ),
        hints=(
            "For unit fractions, compare the size of one piece.",
            "Try a common denominator to compare the values.",
            "The fraction farther right on the number line is larger.",
        ),
    ),
    "M03": InterventionTemplate(
        title="Build Equivalent Fractions",
        learning_objective="Convert a fraction to an equivalent fraction with a requested denominator.",
        explanation=(
            "To change a denominator without changing a fraction's value, multiply "
            "both its numerator and denominator by the same number."
        ),
        introduction="We'll keep the value the same while changing the name of a fraction.",
        guided_example={
            "question": "Write 2/3 with denominator 12.",
            "steps": "Since 3 × 4 = 12, multiply the numerator by 4 too: 2 × 4 = 8.",
            "answer": "8/12",
        },
        practice_questions=(
            "Write 1/3 with denominator 12.",
            "Write 2/5 with denominator 15.",
            "Write 3/4 with denominator 20.",
        ),
        expected_answers=("4/12", "6/15", "15/20"),
        instructions=(
            "Find the factor that changes the denominator to the requested value. "
            "Multiply the numerator by that same factor."
        ),
        hints=(
            "What number multiplies the old denominator to make the new one?",
            "Use that same multiplier on the numerator.",
            "The new fraction must keep the original value.",
        ),
    ),
    "M04": InterventionTemplate(
        title="See Equivalent Fractions",
        learning_objective="Recognize equivalent fractions using fraction strips and equal partitions.",
        explanation=(
            "Equivalent fractions name the same amount. Fraction strips show that "
            "one half covers the same length as two fourths, even though the numbers differ."
        ),
        introduction="Let's use fraction strips to see when two fraction names cover the same amount.",
        guided_example={
            "question": "Are 1/2 and 2/4 equivalent?",
            "steps": "Split one strip into 2 equal parts and another into 4. Shade 1 part and 2 parts; the shaded lengths match.",
            "answer": "Yes",
        },
        practice_questions=(
            "Is 2/3 equivalent to 4/6? Answer Yes or No.",
            "Is 2/5 equivalent to 4/15? Answer Yes or No.",
            "Is 3/4 equivalent to 9/12? Answer Yes or No.",
        ),
        expected_answers=("Yes", "No", "Yes"),
        instructions=(
            "Draw or imagine two fraction strips with the same whole. Partition each "
            "into the denominators shown, shade the numerators, and compare lengths."
        ),
        hints=(
            "Multiply or divide the numerator and denominator by the same number.",
            "Matching shaded lengths mean the fractions are equivalent.",
            "Try placing both fractions at the same point on a number line.",
        ),
    ),
    "M05": InterventionTemplate(
        title="Check Each Fraction-Arithmetic Step",
        learning_objective="Apply fraction arithmetic carefully and check each calculation step.",
        explanation=(
            "Keep the fraction method organized: make denominators match when needed, "
            "calculate the numerators, keep the denominator, then simplify if possible."
        ),
        introduction="Let's slow down and check one arithmetic step at a time.",
        guided_example={
            "question": "Add 2/3 + 1/6.",
            "steps": "Rewrite 2/3 as 4/6. Add numerators: 4 + 1 = 5. Keep denominator 6.",
            "answer": "5/6",
        },
        practice_questions=(
            "Add 4/7 + 2/7.",
            "Subtract 5/6 - 1/6 and simplify.",
            "Subtract 7/10 - 3/10 and simplify.",
        ),
        expected_answers=("6/7", "2/3", "2/5"),
        instructions=(
            "Write each line separately. Check the denominator rule, the numerator "
            "calculation, and whether the final fraction can be simplified."
        ),
        hints=(
            "If denominators match, keep that denominator.",
            "Check the numerator calculation with a quick estimate.",
            "Simplify by dividing numerator and denominator by the same factor.",
        ),
    ),
}

INTERVENTION_TEMPLATES.update(
    {
        "ALG01": InterventionTemplate(
            "Keep Equations Balanced",
            "Solve one-step and two-step equations using equal operations on both sides.",
            "An equation is like a balance. Undo operations in reverse order, doing the same thing to each side.",
            "Let's keep both sides of an equation balanced as we solve.",
            {"question": "Solve 3x + 2 = 14.", "steps": "Subtract 2 from both sides, then divide both sides by 3.", "answer": "x = 4"},
            ("Solve 4x + 1 = 17.", "Solve x/3 + 2 = 6.", "Solve 5x - 3 = 22."),
            ("4", "12", "5"),
            "Write one equal operation on each side at every step.",
            ("Undo addition or subtraction first.", "Whatever you do to one side, do to the other.", "Check by substituting your value."),
        ),
        "ALG02": InterventionTemplate(
            "Distribute to Every Term",
            "Expand expressions by multiplying the outside factor by every term inside parentheses.",
            "The distributive property multiplies the outside factor by each term inside the parentheses.",
            "Let's open the parentheses one term at a time.",
            {"question": "Expand 2(x + 5).", "steps": "Multiply 2 by x and by 5.", "answer": "2x + 10"},
            ("Expand 4(y + 3).", "Expand 3(a - 2).", "Expand -2(t + 4)."),
            ("4y + 12", "3a - 6", "-2t - 8"),
            "Draw an arrow from the factor outside the parentheses to each term inside.",
            ("Every term inside gets multiplied.", "Keep the sign attached to each term.", "Check by substituting a small value."),
        ),
        "ALG03": InterventionTemplate(
            "Undo the Variable Operation",
            "Isolate a variable by undoing the operation applied to it.",
            "Use the inverse operation to isolate the variable, and keep the equation balanced.",
            "Let's identify what is happening to the variable, then undo it.",
            {"question": "Solve 6x = 42.", "steps": "Divide both sides by 6.", "answer": "x = 7"},
            ("Solve 7x = 56.", "Solve x/5 = 6.", "Solve 9x = 63."),
            ("8", "30", "7"),
            "Name the operation applied to the variable and use its inverse on both sides.",
            ("Multiplication is undone by division.", "Division is undone by multiplication.", "Substitute your result to check."),
        ),
        "FM01": InterventionTemplate(
            "Explore Motion and Inertia",
            "Explain how an object's motion changes when a net force acts on it.",
            "A net force changes motion. Without a net force, an object keeps its velocity; friction is a force that can slow it.",
            "Let's separate the force that starts motion from the forces that change it.",
            {"question": "What happens to a moving object when the net force is zero?", "steps": "With no net force, its velocity does not change.", "answer": "It continues at constant velocity."},
            ("What happens to a moving cart on a level track if friction is negligible and the net force is zero?", "What force can slow a rolling ball across a floor?", "In deep space with no net force, what happens to a moving probe?"),
            ("It continues at constant velocity.", "Friction.", "It continues at constant velocity."),
            "For each situation, identify the net force before deciding whether velocity changes.",
            ("An object does not need a continuing net force to keep constant velocity.", "Friction is a force.", "A net force changes velocity."),
        ),
        "FM02": InterventionTemplate(
            "Calculate Average Speed",
            "Find average speed by dividing distance by elapsed time.",
            "Average speed tells how much distance is covered per unit of time: speed = distance ÷ time.",
            "Let's track distance and time with matching units.",
            {"question": "A runner travels 24 meters in 4 seconds. Find the average speed.", "steps": "Divide 24 meters by 4 seconds.", "answer": "6 m/s"},
            ("A car travels 45 km in 5 hours. Find its average speed.", "A swimmer travels 36 meters in 6 seconds. Find the average speed.", "A cyclist travels 20 meters at 5 m/s. How long does it take?"),
            ("9 km/h", "6 m/s", "4 s"),
            "Write the known distance and time with units before choosing the operation.",
            ("Speed is distance divided by time.", "Keep the distance and time units in the answer.", "Check that speed multiplied by time gives distance."),
        ),
        "FM03": InterventionTemplate(
            "Connect Force, Mass, and Acceleration",
            "Use net force = mass × acceleration to solve for acceleration.",
            "Newton's second law relates net force, mass, and acceleration: F = m × a.",
            "Let's label the quantities and choose the matching relationship.",
            {"question": "A 3 kg cart has a net force of 12 N. Find its acceleration.", "steps": "Divide force by mass: 12 N ÷ 3 kg.", "answer": "4 m/s^2"},
            ("A 4 kg object has a net force of 20 N. Find its acceleration.", "A 5 kg object accelerates at 2 m/s^2. Find the net force.", "A 18 N net force acts on a 3 kg object. Find its acceleration."),
            ("5 m/s^2", "10 N", "6 m/s^2"),
            "Write F = m × a, substitute the known values, then solve for the requested quantity.",
            ("Acceleration is force divided by mass.", "Force is mass times acceleration.", "Check the units in your result."),
        ),
        "EL01": InterventionTemplate(
            "Complete the Circuit Path",
            "Recognize that a simple circuit needs a complete conducting loop.",
            "In a simple circuit, the battery, wires, and component must form one complete path for current to flow.",
            "Let's trace the path from the battery and back again.",
            {"question": "Will a bulb light if there is a gap in its only circuit path?", "steps": "The gap breaks the complete loop.", "answer": "No"},
            ("What kind of path must connect a battery and bulb for the bulb to light?", "If a switch opens the only loop, does the bulb stay lit?", "What happens when a wire reconnects the open gap?"),
            ("A complete closed loop.", "No.", "The complete path is restored."),
            "Trace the wire path around the circuit and check whether it returns to the battery with no gap.",
            ("A gap makes an open circuit.", "A closed path can carry current.", "The switch controls whether the path is open or closed."),
        ),
        "EL02": InterventionTemplate(
            "Track Current in a Series Loop",
            "Describe current consistently at different points in a simple series circuit.",
            "A series circuit has one path. In a steady simple series circuit, the current is the same at each point in that path.",
            "Let's compare the current before and after a component.",
            {"question": "Is the current the same or used up after a bulb in a series loop?", "steps": "There is one path, so charge does not disappear at the bulb.", "answer": "The current is the same."},
            ("If current is 0.4 A before a bulb in series, what is it after the bulb?", "Does a second series bulb use up the remaining current?", "In a steady series loop, compare current entering and leaving a resistor."),
            ("0.4 A.", "No; current is the same through each component.", "They are the same."),
            "Follow one loop and compare current at points before and after each component.",
            ("A series circuit has one path.", "Current is not consumed by a component.", "Use the same current value throughout a steady series loop."),
        ),
        "EL03": InterventionTemplate(
            "Tell Current and Voltage Apart",
            "Distinguish current as charge flow from voltage as energy per charge.",
            "Current describes the rate of charge flow. Voltage is the energy transferred per unit of charge between two points.",
            "Let's match each electrical quantity to what it describes.",
            {"question": "Which quantity is measured in amperes: current or voltage?", "steps": "Amperes measure current; volts measure potential difference.", "answer": "Current"},
            ("Which quantity is measured in volts?", "What does current describe?", "A meter reads 2 A. Is that a current or voltage reading?"),
            ("Voltage.", "The rate of charge flow.", "Current."),
            "Name the quantity and its unit before interpreting each measurement.",
            ("Current is measured in amperes (A).", "Voltage is measured in volts (V).", "Do not use the words current and voltage interchangeably."),
        ),
        "GR01": InterventionTemplate(
            "Match Verb Tense to Time",
            "Choose verb forms that agree with the time described in a sentence.",
            "Time words such as yesterday, now, and tomorrow help determine the verb tense.",
            "Let's use the time clue to choose a verb form.",
            {"question": "Yesterday, Maya (visit/visits) her aunt.", "steps": "Yesterday signals past time.", "answer": "visited"},
            ("Last night, Ravi (cook/cooked) dinner.", "Tomorrow, we (will visit/visited) the library.", "Every day, Lena (walk/walked) to school."),
            ("cooked", "will visit", "walks"),
            "Underline the time clue, then choose the verb form that matches it.",
            ("Yesterday and last night signal past time.", "Tomorrow signals future time.", "Every day describes a repeated present action."),
        ),
        "GR02": InterventionTemplate(
            "Connect Pronouns to Their Nouns",
            "Choose pronouns that agree with and clearly refer to their antecedents.",
            "A pronoun replaces a noun. Its form should fit the noun or nouns it refers to.",
            "Let's find the noun first, then choose a pronoun that matches.",
            {"question": "The children packed ___ lunches.", "steps": "Children is plural, so use their.", "answer": "their"},
            ("Mina brought ___ notebook.", "The players put ___ bags away.", "Ravi and I finished ___ work."),
            ("her", "their", "our"),
            "Point to the noun a pronoun replaces and check whether it is singular or plural.",
            ("Find the antecedent before choosing.", "Plural people can be referred to as they/their.", "Make sure the pronoun reference is clear."),
        ),
        "GR03": InterventionTemplate(
            "Polish Sentence Conventions",
            "Use capitalization and terminal punctuation in a complete sentence.",
            "A sentence begins with a capital letter and ends with punctuation that fits its purpose.",
            "Let's give each sentence a clear beginning and ending.",
            {"question": "Fix this sentence: birds fly south", "steps": "Capitalize the first word and add a period.", "answer": "Birds fly south."},
            ("Fix this sentence: we planted beans", "Fix this sentence: the bell rang", "Fix this sentence: our class read a poem"),
            ("We planted beans.", "The bell rang.", "Our class read a poem."),
            "Read each sentence aloud, then check its first letter and final punctuation.",
            ("Capitalize the first word.", "Use a period for a statement.", "Keep the original sentence meaning."),
        ),
        "SV01": InterventionTemplate(
            "Find the Real Subject",
            "Match the verb to the main subject rather than a nearby noun in a phrase.",
            "A phrase between the subject and verb can contain another noun. Find the main subject before choosing the verb.",
            "Let's set aside describing phrases and find who or what the sentence is about.",
            {"question": "The box of crayons (is/are) open.", "steps": "Set aside 'of crayons'; box is the singular subject.", "answer": "is"},
            ("The jar of buttons (sits/sit) on the shelf.", "The players on the team (practices/practice) daily.", "One of the dogs (barks/bark) loudly."),
            ("sits", "practice", "barks"),
            "Cross out the phrase between the subject and verb, then match the verb to the remaining subject.",
            ("Ask who or what the sentence is about.", "A nearby noun inside a phrase may not be the subject.", "Check whether the subject is singular or plural."),
        ),
        "SV02": InterventionTemplate(
            "Match Singular and Plural Verbs",
            "Choose a verb form that agrees with a singular or plural subject.",
            "A singular subject takes a singular verb form; a plural subject takes a plural verb form.",
            "Let's identify whether each subject names one or more than one.",
            {"question": "The books (is/are) on the desk.", "steps": "Books is plural, so choose are.", "answer": "are"},
            ("A pair of gloves (is/are) missing.", "The children (has/have) a new game.", "Each student (brings/bring) a pencil."),
            ("is", "have", "brings"),
            "Identify the complete subject and decide whether it is singular or plural before selecting the verb.",
            ("Pair is a singular subject.", "Children is plural.", "Each is singular."),
        ),
        "SV03": InterventionTemplate(
            "Agree with Compound Subjects",
            "Use plural verb forms with compound subjects joined by 'and'.",
            "Two subjects joined by and usually name more than one person or thing and take a plural verb.",
            "Let's count the parts of the subject joined by and.",
            {"question": "A pen and a pencil (is/are) on the desk.", "steps": "The compound subject names two items, so use are.", "answer": "are"},
            ("Liam and Ava (walk/walks) to school.", "The teacher and student (plans/plan) the project.", "A cup and a plate (belongs/belong) here."),
            ("walk", "plan", "belong"),
            "Circle each part of the subject joined by and, then choose the plural verb.",
            ("And usually combines two subjects.", "Two subjects take a plural verb.", "Read the subject and verb together."),
        ),
    }
)


class InterventionNotAllowedError(ValueError):
    pass


def _learning_gap(db: Session, group: LearningGroup) -> list[str]:
    student_ids = [member.student_id for member in group.group_members]
    if not student_ids:
        return []
    diagnoses = db.scalars(
        select(Diagnosis)
        .join(Diagnosis.submission)
        .where(
            Submission.student_id.in_(student_ids),
            Diagnosis.misconception_code == group.misconception_code,
        )
        .order_by(Diagnosis.created_at.desc(), Diagnosis.id)
        .limit(6)
    )
    return [diagnosis.evidence[:240] for diagnosis in diagnoses if diagnosis.evidence]


def _personalize(
    *,
    provider,
    subject: str,
    topic: str,
    code: str,
    template: InterventionTemplate,
    learning_gap: list[str],
) -> InterventionPersonalization:
    return InterventionPersonalization.model_validate(
        provider.personalize(
            misconception_code=code,
            subject=subject,
            topic=topic,
            taxonomy_description=next(
                item.description
                for item in get_taxonomy(subject, topic)
                if item.code == code
            ),
            learning_objective=template.learning_objective,
            learning_gap=learning_gap,
            explanation=template.explanation,
            instructions=template.instructions,
            introduction=template.introduction,
            hints=list(template.hints),
        )
    )


def generate_intervention_for_group(
    db: Session,
    group_id: UUID,
    *,
    personalizer=None,
) -> tuple[Intervention, list[InterventionAssignment], int]:
    group = db.scalar(
        select(LearningGroup)
        .where(LearningGroup.id == group_id)
        .options(
            joinedload(LearningGroup.group_members).joinedload(GroupMember.student)
        )
    )
    if group is None:
        raise LookupError("Learning group not found")
    if not group.teacher_approved or group.review_status != "approved":
        raise PermissionError("Teacher approval is required before generating interventions")
    if any(member.student.class_id != group.class_id for member in group.group_members):
        raise PermissionError("Group membership must belong to the selected class")
    code = group.misconception_code.upper()
    if is_follow_up_code(code):
        raise InterventionNotAllowedError(
            "Insufficient evidence requires a diagnostic follow-up question, not a remedial activity"
        )
    template = INTERVENTION_TEMPLATES.get(code)
    if template is None:
        raise InterventionNotAllowedError(
            f"No intervention template exists for misconception {code}"
        )
    if code not in {
        item.code for item in get_taxonomy(group.classroom.subject, group.topic)
    }:
        raise InterventionNotAllowedError(
            "Misconception code does not belong to this subject and topic"
        )

    intervention = db.scalar(
        select(Intervention).where(Intervention.group_id == group.id)
    )
    if intervention is None:
        provider_name = "template"
        generation_note = None
        explanation = template.explanation
        instructions = template.instructions
        introduction = template.introduction
        hints = list(template.hints)
        settings = get_settings()

        if personalizer is None and settings.ai_provider in {"openrouter", "gemini"}:
            try:
                personalizer = create_intervention_provider(settings)
            except ProviderConfigurationError:
                raise
            except ProviderError:
                generation_note = f"{settings.ai_provider} unavailable; predefined template used."

        provider_label = "Gemini" if settings.ai_provider == "gemini" else "OpenRouter"
        if personalizer is not None:
            try:
                personalized = _personalize(
                    provider=personalizer,
                    subject=group.classroom.subject,
                    topic=group.topic,
                    code=code,
                    template=template,
                    learning_gap=_learning_gap(db, group),
                )
            except ProviderConfigurationError:
                raise
            except ProviderRateLimited:
                generation_note = (
                    f"{provider_label} rate limit exceeded; predefined template used."
                )
            except (ProviderError, ValidationError, ValueError):
                logger.warning(
                    "OpenRouter intervention personalization failed; using template fallback"
                )
                generation_note = (
                    f"{provider_label} failed validation or was unavailable; "
                    "predefined template used."
                )
            else:
                explanation = personalized.explanation.strip()
                instructions = personalized.instructions.strip()
                introduction = personalized.introduction.strip()
                hints = [hint.strip() for hint in personalized.hints]
                provider_name = getattr(personalizer, "name", "openrouter")
                generation_note = None

        intervention = Intervention(
            group_id=group.id,
            subject=group.classroom.subject,
            topic=group.topic,
            misconception_code=code,
            title=template.title,
            learning_objective=template.learning_objective,
            explanation=explanation,
            introduction=introduction,
            guided_example=template.guided_example,
            practice_questions=list(template.practice_questions),
            expected_answers=list(template.expected_answers),
            instructions=instructions,
            hints=hints,
            provider=provider_name,
            generation_note=generation_note,
        )
        db.add(intervention)
        db.flush()

    assignments: list[InterventionAssignment] = []
    created = 0
    for member in group.group_members:
        assignment = db.scalar(
            select(InterventionAssignment).where(
                InterventionAssignment.intervention_id == intervention.id,
                InterventionAssignment.student_id == member.student_id,
            )
        )
        if assignment is None:
            assignment = InterventionAssignment(
                intervention_id=intervention.id,
                student_id=member.student_id,
            )
            db.add(assignment)
            assignments.append(assignment)
            created += 1
        else:
            assignments.append(assignment)
    try:
        db.flush()
        from app.services.learning_service import record_evidence
        for assignment in assignments:
            record_evidence(db, assignment.student, intervention.subject, intervention.topic,
                "approved_assignment", f"approved-assignment:{assignment.id}", {
                    "assignment_id": str(assignment.id), "group_id": str(group.id),
                    "teacher_id": str(group.classroom.teacher_id), "code": code,
                    "review_status": group.review_status})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(intervention)
    for assignment in assignments:
        db.refresh(assignment)
    return intervention, assignments, created
