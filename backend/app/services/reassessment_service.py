from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    InterventionAssignment,
    Question,
    Reassessment,
    ReassessmentQuestion,
    ReassessmentResult,
)
from app.services.answer_evaluation import answers_match


REASSESSMENT_QUESTIONS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "M01": (
        ("Add 2/3 + 1/4.", "11/12", "Use twelfths: 8/12 + 3/12 = 11/12."),
        ("Add 3/5 + 1/10.", "7/10", "Rewrite 3/5 as 6/10, then add."),
        ("Add 1/6 + 3/8.", "13/24", "Rewrite as 4/24 + 9/24."),
    ),
    "M02": (
        ("Which is larger, 3/7 or 3/5?", "3/5", "Compare equal numerators or use a number line."),
        ("Which is larger, 4/9 or 1/2?", "1/2", "Compare 8/18 and 9/18."),
        ("Which is larger, 5/8 or 2/3?", "2/3", "Compare 15/24 and 16/24."),
    ),
    "M03": (
        ("Write 2/7 with denominator 21.", "6/21", "Multiply numerator and denominator by 3."),
        ("Write 3/8 with denominator 24.", "9/24", "Multiply numerator and denominator by 3."),
        ("Write 5/6 with denominator 18.", "15/18", "Multiply numerator and denominator by 3."),
    ),
    "M04": (
        ("Is 3/5 equivalent to 6/10? Answer Yes or No.", "Yes", "Multiply numerator and denominator by 2 to get 6/10."),
        ("Is 3/4 equivalent to 7/12? Answer Yes or No.", "No", "In twelfths, 3/4 is equal to 9/12, not 7/12."),
        ("Is 5/6 equivalent to 10/12? Answer Yes or No.", "Yes", "Both fractions name the same amount: 5/6 = 10/12."),
    ),
    "M05": (
        ("Add 5/9 + 2/9 and simplify if needed.", "7/9", "Keep the denominator and add numerators."),
        ("Subtract 7/8 - 3/8 and simplify.", "1/2", "Subtract to get 4/8, then simplify."),
        ("Add 4/5 + 1/10.", "9/10", "Rewrite 4/5 as 8/10 before adding."),
    ),
    "ALG01": (
        ("Solve 5x + 4 = 29.", "5", "Subtract 4 from both sides, then divide by 5."),
        ("Solve x/4 - 2 = 3.", "20", "Add 2 to both sides, then multiply by 4."),
        ("Solve 3x + 7 = 25.", "6", "Subtract 7 from both sides and divide by 3."),
    ),
    "ALG02": (
        ("Expand 5(y + 2).", "5y + 10", "Multiply 5 by each term inside the parentheses."),
        ("Expand -3(a - 2).", "-3a + 6", "Distribute -3 to both terms."),
        ("Expand 2(n + 7).", "2n + 14", "Multiply 2 by n and by 7."),
    ),
    "ALG03": (
        ("Solve 8x = 72.", "9", "Divide both sides by 8."),
        ("Solve x/6 = 7.", "42", "Multiply both sides by 6."),
        ("Solve 9x = 54.", "6", "Divide both sides by 9."),
    ),
    "FM01": (
        ("A moving cart has zero net force. Does its velocity change or stay constant?", "It stays constant.", "Zero net force means no change in velocity."),
        ("What force usually slows a sliding book on a table?", "Friction.", "Friction opposes relative motion between surfaces."),
        ("With no net force, does a moving object stop or keep its velocity?", "It keeps its velocity.", "Without a net force, velocity remains constant."),
    ),
    "FM02": (
        ("A train travels 54 km in 9 hours. Find its average speed.", "6 km/h", "Divide distance by time: 54 ÷ 9 = 6."),
        ("A runner covers 72 meters in 8 seconds. Find average speed.", "9 m/s", "Divide distance by elapsed time."),
        ("How long does a 15 meter trip take at 3 m/s?", "5 s", "Time equals distance divided by speed."),
    ),
    "FM03": (
        ("A 5 kg object has a net force of 15 N. Find acceleration.", "3 m/s^2", "Acceleration equals force divided by mass."),
        ("A 6 kg cart accelerates at 2 m/s^2. Find net force.", "12 N", "Net force equals mass times acceleration."),
        ("A 4 kg object has a net force of 28 N. Find acceleration.", "7 m/s^2", "Divide net force by mass."),
    ),
    "EL01": (
        ("Can current flow through a simple circuit with a break in its only path?", "No", "An open path prevents a complete circuit."),
        ("What does closing a switch do to the path in a simple circuit?", "It completes the path.", "A closed switch connects the loop."),
        ("A wire is disconnected from a battery terminal. Is the circuit open or closed?", "Open", "The conducting path is broken."),
    ),
    "EL02": (
        ("In a steady series loop, compare the current before and after a lamp.", "The current is the same.", "Current is the same at every point in a series path."),
        ("A series circuit has 0.3 A at one point. What is the current elsewhere in the loop?", "0.3 A", "There is one path, so current is the same throughout."),
        ("Is current consumed by a resistor in a simple series circuit?", "No", "Current is not used up as it passes through components."),
    ),
    "EL03": (
        ("Which quantity is measured in amperes?", "Current", "Amperes are the unit of current."),
        ("Which quantity is measured in volts?", "Voltage", "Volts measure potential difference."),
        ("A meter reads 5 A. Is it measuring current or voltage?", "Current", "Amperes measure current."),
    ),
    "GR01": (
        ("Last weekend, Nia (play/played) tennis.", "played", "Last weekend indicates past tense."),
        ("Next week, they (will travel/traveled) by train.", "will travel", "Next week indicates future time."),
        ("Usually, he (reads/read) before bed.", "reads", "Usually describes a repeated present action."),
    ),
    "GR02": (
        ("The girls brought ___ lunches.", "their", "Their agrees with the plural antecedent girls."),
        ("Asha finished ___ drawing.", "her", "Her refers to the singular antecedent Asha."),
        ("My brother and I cleaned ___ room.", "our", "Our refers to the compound antecedent my brother and I."),
    ),
    "GR03": (
        ("Fix this sentence: the river is wide", "The river is wide.", "Capitalize the first word and add a period."),
        ("Fix this sentence: our team won", "Our team won.", "Begin with a capital and end the statement with a period."),
        ("Fix this sentence: the stars are bright", "The stars are bright.", "A statement needs an initial capital and a final period."),
    ),
    "SV01": (
        ("The stack of papers (is/are) ready.", "is", "Stack is the singular subject."),
        ("The cats under the chair (sleeps/sleep).", "sleep", "Cats is the plural subject."),
        ("One of the windows (needs/need) cleaning.", "needs", "One is the singular subject."),
    ),
    "SV02": (
        ("The pair of socks (is/are) clean.", "is", "Pair is a singular subject."),
        ("Several students (has/have) questions.", "have", "Students is plural."),
        ("Every answer (seems/seem) clear.", "seems", "Every answer is singular."),
    ),
    "SV03": (
        ("A fork and a spoon (belongs/belong) in the drawer.", "belong", "The subject joined by and is plural."),
        ("Nora and Eli (takes/take) the bus.", "take", "Two people joined by and take a plural verb."),
        ("The coach and captain (was/were) present.", "were", "The compound subject names two people."),
    ),
}


def _find_or_create_question(
    db: Session,
    *,
    subject: str,
    topic: str,
    question_text: str,
    correct_answer: str,
    explanation: str,
) -> Question:
    question = db.scalar(
        select(Question).where(
            Question.subject == subject,
            Question.topic == topic,
            Question.question_text == question_text,
        )
    )
    if question is None:
        question = Question(
            subject=subject,
            topic=topic,
            question_text=question_text,
            correct_answer=correct_answer,
            explanation_expected=explanation,
        )
        db.add(question)
        db.flush()
    elif not answers_match(
        question.correct_answer, correct_answer, question_text=question_text
    ):
        raise ValueError(
            "Stored question key conflicts with the verified reassessment answer"
        )
    return question


def generate_reassessment(
    db: Session, assignment_id: UUID
) -> Reassessment:
    assignment = db.scalar(
        select(InterventionAssignment)
        .where(InterventionAssignment.id == assignment_id)
        .options(joinedload(InterventionAssignment.intervention))
    )
    if assignment is None:
        raise LookupError("Intervention assignment not found")
    if assignment.status != "completed":
        raise PermissionError("Complete the intervention before reassessment")
    existing = db.scalar(
        select(Reassessment)
        .where(Reassessment.assignment_id == assignment.id)
        .options(
            joinedload(Reassessment.questions).joinedload(
                ReassessmentQuestion.question
            ),
            selectinload(Reassessment.results),
        )
    )
    if existing is not None:
        return existing

    code = assignment.intervention.misconception_code
    subject = assignment.intervention.subject
    topic = assignment.intervention.topic
    question_templates = REASSESSMENT_QUESTIONS.get(code)
    if question_templates is None:
        raise ValueError(f"No reassessment question set exists for {code}")

    reassessment = Reassessment(
        assignment_id=assignment.id,
        misconception_code=code,
        total_questions=len(question_templates),
    )
    db.add(reassessment)
    db.flush()
    for ordinal, (prompt, answer, explanation) in enumerate(question_templates):
        question = _find_or_create_question(
            db,
            subject=subject,
            topic=topic,
            question_text=prompt,
            correct_answer=answer,
            explanation=explanation,
        )
        db.add(
            ReassessmentQuestion(
                reassessment_id=reassessment.id,
                question_id=question.id,
                ordinal=ordinal,
            )
        )
    db.commit()
    return db.scalar(
        select(Reassessment)
        .where(Reassessment.id == reassessment.id)
        .options(
            joinedload(Reassessment.questions).joinedload(
                ReassessmentQuestion.question
            )
        )
    )


def submit_reassessment(
    db: Session,
    reassessment_id: UUID,
    answers: dict[UUID, str | None],
    *,
    student_id: UUID,
) -> tuple[Reassessment, list[ReassessmentResult]]:
    reassessment = db.scalar(
        select(Reassessment)
        .where(Reassessment.id == reassessment_id)
        .options(
            joinedload(Reassessment.intervention_assignment),
            joinedload(Reassessment.questions).joinedload(
                ReassessmentQuestion.question
            ),
        )
    )
    if reassessment is None:
        raise LookupError("Reassessment not found")
    if reassessment.intervention_assignment.student_id != student_id:
        raise PermissionError("This reassessment does not belong to this student")
    if reassessment.status == "completed":
        raise PermissionError("This reassessment has already been submitted")

    question_ids = {item.question_id for item in reassessment.questions}
    if not set(answers).issubset(question_ids):
        raise ValueError("Answer includes a question outside this reassessment")
    results: list[ReassessmentResult] = []
    correct_count = 0
    for item in reassessment.questions:
        question = item.question
        answer = answers.get(item.question_id)
        correct = answers_match(
            answer, question.correct_answer, question_text=question.question_text
        )
        correct_count += int(correct)
        result = ReassessmentResult(
            student_id=student_id,
            question_id=question.id,
            intervention_assignment_id=reassessment.assignment_id,
            reassessment_id=reassessment.id,
            answer=answer,
            is_correct=correct,
        )
        db.add(result)
        results.append(result)

    total = reassessment.total_questions
    reassessment.correct_answers = correct_count
    reassessment.incorrect_answers = total - correct_count
    reassessment.accuracy_percentage = round(correct_count * 100 / total, 1)
    reassessment.status = "completed"
    reassessment.submitted_at = datetime.now(timezone.utc)
    db.commit()
    for result in results:
        db.refresh(result)
    return reassessment, results
