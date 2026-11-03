"""Local-demo scoped routes. Self-asserted headers are not production authentication."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Class, Quiz, QuizAttempt, QuizReflection
from app.schemas.quiz import (
    ImportInput,
    LessonReviewInput,
    QuizInput,
    ReflectionInput,
    RepairAnswerInput,
    ReviewInput,
    SubmitQuizInput,
)
from app.services import quiz_service as service
from app.services.diagnosis_provider import ProviderError, ProviderRateLimited
from app.services.quiz_tutor import lesson_suggestion, tutor_feedback

router = APIRouter(prefix="/api", tags=["quiz learning loop"])


def teacher_scope(
    role: Literal["teacher"] = Header(alias="X-Demo-Role"),
    selected_class_id: UUID = Header(alias="X-Class-ID"),
    db: Session = Depends(get_db),
):
    if db.get(Class, selected_class_id) is None:
        raise HTTPException(404, "Class not found")
    return selected_class_id


def assert_class(path_class, scope):
    if path_class != scope:
        raise HTTPException(403, "Class does not match the selected teacher context")


@router.post("/quizzes/import")
def preview_import(payload: ImportInput, scope: UUID = Depends(teacher_scope)):
    return service.import_csv(payload.content)


@router.get("/classes/{class_id}/quizzes")
def list_quizzes(
    class_id: UUID, scope: UUID = Depends(teacher_scope), db: Session = Depends(get_db)
):
    assert_class(class_id, scope)
    return [
        service.serialize_quiz(q)
        for q in db.scalars(
            select(Quiz)
            .where(Quiz.class_id == class_id)
            .order_by(Quiz.created_at.desc(), Quiz.id)
        )
    ]


@router.post("/classes/{class_id}/quizzes", status_code=201)
def create_quiz(
    class_id: UUID,
    payload: QuizInput,
    scope: UUID = Depends(teacher_scope),
    db: Session = Depends(get_db),
):
    assert_class(class_id, scope)
    quiz = Quiz(
        class_id=class_id,
        title=payload.title,
        questions=service.saved_questions(payload),
        status="draft",
    )
    db.add(quiz)
    db.commit()
    return service.serialize_quiz(quiz)


@router.get("/quizzes/{quiz_id}")
def get_quiz(
    quiz_id: UUID, scope: UUID = Depends(teacher_scope), db: Session = Depends(get_db)
):
    return service.serialize_quiz(service.teacher_quiz(db, quiz_id, scope))


@router.patch("/quizzes/{quiz_id}")
def edit_quiz(
    quiz_id: UUID,
    payload: QuizInput,
    scope: UUID = Depends(teacher_scope),
    db: Session = Depends(get_db),
):
    quiz = service.teacher_quiz(db, quiz_id, scope)
    if quiz.status != "draft":
        raise HTTPException(
            409, "Published quizzes are fixed. Create a new quiz to change questions."
        )
    quiz.title, quiz.questions = payload.title, service.saved_questions(payload)
    db.commit()
    return service.serialize_quiz(quiz)


@router.post("/quizzes/{quiz_id}/publish")
def publish_quiz(
    quiz_id: UUID, scope: UUID = Depends(teacher_scope), db: Session = Depends(get_db)
):
    quiz = service.teacher_quiz(db, quiz_id, scope)
    quiz.status = "published"
    db.commit()
    return service.serialize_quiz(quiz)


@router.get("/quizzes/{quiz_id}/insights")
def get_insights(
    quiz_id: UUID, scope: UUID = Depends(teacher_scope), db: Session = Depends(get_db)
):
    return service.quiz_insights(db, service.teacher_quiz(db, quiz_id, scope))


@router.patch("/quizzes/{quiz_id}/reflections/{reflection_id}/review")
def review_reflection(
    quiz_id: UUID,
    reflection_id: UUID,
    payload: ReviewInput,
    scope: UUID = Depends(teacher_scope),
    db: Session = Depends(get_db),
):
    quiz = service.teacher_quiz(db, quiz_id, scope)
    reflection = db.get(QuizReflection, reflection_id)
    attempt = db.get(QuizAttempt, reflection.attempt_id) if reflection else None
    if attempt is None or attempt.quiz_id != quiz.id:
        raise HTTPException(404, "Reflection not found in this quiz")
    reflection.flagged = payload.flagged
    db.commit()
    return {"id": str(reflection.id), "flagged": reflection.flagged}


@router.post("/quizzes/{quiz_id}/lesson")
def generate_lesson(
    quiz_id: UUID, scope: UUID = Depends(teacher_scope), db: Session = Depends(get_db)
):
    quiz = service.teacher_quiz(db, quiz_id, scope)
    if quiz.lesson:
        return quiz.lesson
    report = service.quiz_insights(db, quiz)
    if not report["submitted_students"]:
        raise HTTPException(
            409,
            "Wait for at least one quiz submission before creating a lesson suggestion",
        )
    quiz.lesson = lesson_suggestion(report)
    db.commit()
    return quiz.lesson


@router.patch("/quizzes/{quiz_id}/lesson")
def review_lesson(
    quiz_id: UUID,
    payload: LessonReviewInput,
    scope: UUID = Depends(teacher_scope),
    db: Session = Depends(get_db),
):
    quiz = service.teacher_quiz(db, quiz_id, scope)
    if not quiz.lesson:
        raise HTTPException(409, "Create a lesson suggestion first")
    quiz.lesson = {**quiz.lesson, **payload.model_dump()}
    db.commit()
    return quiz.lesson


@router.get("/students/{student_id}/quizzes")
def student_quizzes(
    student_id: UUID,
    asserted: UUID = Header(alias="X-Student-ID"),
    db: Session = Depends(get_db),
):
    student = service.student_record(db, student_id, asserted)
    quizzes = db.scalars(
        select(Quiz)
        .where(Quiz.class_id == student.class_id, Quiz.status == "published")
        .order_by(Quiz.created_at.desc(), Quiz.id)
    )
    return [
        {
            "id": str(q.id),
            "title": q.title,
            "question_count": len(q.questions),
            "submitted": service.get_attempt(db, q, student) is not None,
        }
        for q in quizzes
    ]


@router.get("/students/{student_id}/quizzes/{quiz_id}")
def student_quiz(
    student_id: UUID,
    quiz_id: UUID,
    asserted: UUID = Header(alias="X-Student-ID"),
    db: Session = Depends(get_db),
):
    student = service.student_record(db, student_id, asserted)
    quiz = service.student_quiz(db, student, quiz_id)
    return service.student_view(db, quiz, student)


@router.post("/students/{student_id}/quizzes/{quiz_id}/submit")
def submit_quiz(
    student_id: UUID,
    quiz_id: UUID,
    payload: SubmitQuizInput,
    asserted: UUID = Header(alias="X-Student-ID"),
    db: Session = Depends(get_db),
):
    student = service.student_record(db, student_id, asserted)
    quiz = service.student_quiz(db, student, quiz_id)
    return service.submit_quiz(db, quiz, student, payload)


def reflection_context(db, student_id, quiz_id, question_id, asserted):
    student = service.student_record(db, student_id, asserted)
    quiz = service.student_quiz(db, student, quiz_id)
    question = service.question_by_id(quiz, question_id)
    attempt = service.get_attempt(db, quiz, student)
    if attempt is None:
        raise HTTPException(409, "Submit the quiz before reflecting on an answer")
    if attempt.answers[question["id"]] == question["correct_option"]:
        raise HTTPException(409, "Reflection is available for missed questions")
    return question, attempt, service.reflection_for(db, attempt, question)


@router.post("/students/{student_id}/quizzes/{quiz_id}/questions/{question_id}/reflect")
def reflect(
    student_id: UUID,
    quiz_id: UUID,
    question_id: UUID,
    payload: ReflectionInput,
    asserted: UUID = Header(alias="X-Student-ID"),
    db: Session = Depends(get_db),
):
    question, attempt, reflection = reflection_context(
        db, student_id, quiz_id, question_id, asserted
    )
    messages = list(reflection.messages) if reflection else []
    if len(messages) >= 10:
        raise HTTPException(
            429,
            "This reflection has reached five exchanges. Ask your teacher for further help.",
        )
    messages.append({"role": "student", "content": payload.message})
    try:
        feedback = tutor_feedback(
            question, attempt.answers[question["id"]], messages, payload.language
        )
    except ProviderRateLimited as error:
        raise HTTPException(
            429,
            "The AI service is busy. Your quiz is saved; please retry shortly.",
            headers={"Retry-After": "30"},
        ) from error
    except ProviderError as error:
        raise HTTPException(
            503, "The AI tutor is unavailable. Your quiz is saved; please retry."
        ) from error
    messages.append({"role": "tutor", "content": feedback["reply"]})
    if reflection:
        reflection.messages, reflection.feedback = messages, feedback
        # Preserve a teacher's flag when more messages arrive.
    else:
        reflection = QuizReflection(
            attempt_id=attempt.id,
            question_id=question["id"],
            messages=messages,
            feedback=feedback,
            flagged=False,
        )
        db.add(reflection)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            409, "Another reflection was saved. Refresh before continuing."
        ) from error
    return service.reflection_view(reflection, question)


@router.post("/students/{student_id}/quizzes/{quiz_id}/questions/{question_id}/repair")
def repair(
    student_id: UUID,
    quiz_id: UUID,
    question_id: UUID,
    payload: RepairAnswerInput,
    asserted: UUID = Header(alias="X-Student-ID"),
    db: Session = Depends(get_db),
):
    question, _, reflection = reflection_context(
        db, student_id, quiz_id, question_id, asserted
    )
    if reflection is None or not question.get("repair"):
        raise HTTPException(
            409, "Complete a reflection with an available repair challenge first"
        )
    if payload.selected_option >= len(question["repair"]["options"]):
        raise HTTPException(
            422, "Selected option is not available for this repair question"
        )
    if reflection.repair_answer is None:
        reflection.repair_answer = payload.selected_option
        db.commit()
    return service.repair_view(question, reflection)["result"]
