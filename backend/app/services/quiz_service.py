import csv
import io
from collections import Counter
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Quiz, QuizAttempt, QuizReflection, Student
from app.schemas.quiz import QuestionInput


def teacher_quiz(db, quiz_id, class_id):
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(404, "Quiz not found")
    if quiz.class_id != class_id:
        raise HTTPException(403, "Quiz does not belong to the selected class")
    return quiz


def student_record(db, student_id, asserted_id):
    if student_id != asserted_id:
        raise HTTPException(
            403, "Student identity does not match the requested resource"
        )
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(404, "Student not found")
    return student


def student_quiz(db, student, quiz_id):
    quiz = db.get(Quiz, quiz_id)
    if quiz is None or quiz.class_id != student.class_id or quiz.status != "published":
        raise HTTPException(404, "Published quiz not found in this class")
    return quiz


def serialize_quiz(quiz):
    return {
        "id": str(quiz.id),
        "class_id": str(quiz.class_id),
        "title": quiz.title,
        "status": quiz.status,
        "created_at": quiz.created_at,
        "questions": quiz.questions,
    }


def saved_questions(payload):
    return [
        {**question.model_dump(), "id": str(uuid4())} for question in payload.questions
    ]


def get_attempt(db, quiz, student):
    return db.scalar(
        select(QuizAttempt).where(
            QuizAttempt.quiz_id == quiz.id, QuizAttempt.student_id == student.id
        )
    )


def question_by_id(quiz, question_id):
    question = next((q for q in quiz.questions if q["id"] == str(question_id)), None)
    if question is None:
        raise HTTPException(404, "Question not found in this quiz")
    return question


def reflection_for(db, attempt, question):
    return db.scalar(
        select(QuizReflection).where(
            QuizReflection.attempt_id == attempt.id,
            QuizReflection.question_id == question["id"],
        )
    )


def repair_view(question, reflection):
    repair = question.get("repair")
    if not repair:
        return None
    result = None
    if reflection.repair_answer is not None:
        result = {
            "selected_option": reflection.repair_answer,
            "is_correct": reflection.repair_answer == repair["correct_option"],
            "correct_option": repair["correct_option"],
            "explanation": repair["explanation"],
        }
    return {
        "text": repair["text"],
        "options": repair["options"],
        "hint": repair["hint"],
        "result": result,
    }


def reflection_view(reflection, question):
    return {
        "id": str(reflection.id),
        "messages": reflection.messages,
        "feedback": reflection.feedback,
        "flagged": reflection.flagged,
        "repair": repair_view(question, reflection),
    }


def attempt_view(db, quiz, attempt):
    reflections = {
        r.question_id: r
        for r in db.scalars(
            select(QuizReflection).where(QuizReflection.attempt_id == attempt.id)
        )
    }
    return {
        "id": str(attempt.id),
        "score": attempt.score,
        "total": len(quiz.questions),
        "submitted_at": attempt.submitted_at,
        "results": [
            {
                "question_id": q["id"],
                "selected_option": attempt.answers[q["id"]],
                "is_correct": attempt.answers[q["id"]] == q["correct_option"],
                "correct_option": q["correct_option"],
                "explanation": q["explanation"],
                "reflection": reflection_view(reflections[q["id"]], q)
                if q["id"] in reflections
                else None,
            }
            for q in quiz.questions
        ],
    }


def student_view(db, quiz, student):
    attempt = get_attempt(db, quiz, student)
    return {
        "id": str(quiz.id),
        "title": quiz.title,
        "questions": [
            {
                "id": q["id"],
                "text": q["text"],
                "options": q["options"],
                "concept": q["concept"],
            }
            for q in quiz.questions
        ],
        "attempt": attempt_view(db, quiz, attempt) if attempt else None,
    }


def submit_quiz(db, quiz, student, payload):
    attempt = get_attempt(db, quiz, student)
    if attempt:
        return attempt_view(db, quiz, attempt)
    answers = {str(a.question_id): a.selected_option for a in payload.answers}
    if len(answers) != len(payload.answers) or set(answers) != {
        q["id"] for q in quiz.questions
    }:
        raise HTTPException(
            422, "Submit exactly one answer for every question in this quiz"
        )
    for q in quiz.questions:
        if answers[q["id"]] >= len(q["options"]):
            raise HTTPException(
                422, "Selected option is not available for this question"
            )
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        student_id=student.id,
        answers=answers,
        score=sum(answers[q["id"]] == q["correct_option"] for q in quiz.questions),
    )
    db.add(attempt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        attempt = get_attempt(db, quiz, student)
        if attempt is None:
            raise
    return attempt_view(db, quiz, attempt)


def quiz_insights(db, quiz):
    students = dict(
        db.execute(
            select(Student.id, Student.student_code).where(
                Student.class_id == quiz.class_id
            )
        ).all()
    )
    attempts = list(
        db.scalars(select(QuizAttempt).where(QuizAttempt.quiz_id == quiz.id))
    )
    reflections = list(
        db.scalars(
            select(QuizReflection)
            .join(QuizAttempt, QuizReflection.attempt_id == QuizAttempt.id)
            .where(QuizAttempt.quiz_id == quiz.id)
        )
    )
    by_attempt = {a.id: a for a in attempts}
    questions = []
    for ordinal, q in enumerate(quiz.questions, 1):
        counts = [
            sum(a.answers[q["id"]] == i for a in attempts)
            for i in range(len(q["options"]))
        ]
        relevant = [r for r in reflections if r.question_id == q["id"]]
        themes = Counter(
            r.feedback["error_type"]
            for r in relevant
            if not r.flagged and r.feedback["error_type"] != "uncertain"
        )
        evidence = [
            {
                "id": str(r.id),
                "student_code": students.get(
                    by_attempt[r.attempt_id].student_id, "Unknown"
                ),
                "error_type": r.feedback["error_type"],
                "quote": r.feedback["evidence"],
                "reply": r.feedback["reply"],
                "flagged": r.flagged,
                "provider": r.feedback["provider"],
            }
            for r in relevant
        ]
        questions.append(
            {
                **{
                    key: q[key]
                    for key in (
                        "id",
                        "text",
                        "options",
                        "correct_option",
                        "explanation",
                        "concept",
                    )
                },
                "ordinal": ordinal,
                "answered_students": len(attempts),
                "option_counts": counts,
                "correct_students": counts[q["correct_option"]],
                "reflected_students": len(relevant),
                "uncertain_students": sum(
                    r.feedback["error_type"] == "uncertain" and not r.flagged
                    for r in relevant
                ),
                "flagged_students": sum(r.flagged for r in relevant),
                "themes": [
                    {"error_type": key, "students": value}
                    for key, value in themes.most_common()
                ],
                "evidence": evidence,
                "repair_attempted": sum(r.repair_answer is not None for r in relevant),
                "repair_correct": sum(
                    r.repair_answer == q["repair"]["correct_option"]
                    for r in relevant
                    if q.get("repair") and r.repair_answer is not None
                ),
            }
        )
    return {
        "id": str(quiz.id),
        "title": quiz.title,
        "total_students": len(students),
        "submitted_students": len(attempts),
        "questions": questions,
        "lesson": quiz.lesson,
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
    }


def import_csv(content):
    required = [
        "question",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "correct_option",
        "explanation",
    ]
    questions, errors = [], []
    try:
        reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")), strict=True)
        headers = reader.fieldnames or []
        if any(name not in headers for name in required) or len(set(headers)) != len(
            headers
        ):
            return {
                "questions": [],
                "errors": ["Required unique columns: " + ", ".join(required)],
            }
        for row_number, row in enumerate(reader, 2):
            if not any((v or "").strip() for v in row.values() if isinstance(v, str)):
                continue
            if len(questions) + len(errors) >= 20:
                return {
                    "questions": [],
                    "errors": ["Import at most 20 questions per quiz."],
                }
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("Column count does not match the header")
                letter = row["correct_option"].strip().upper()
                if letter not in "ABCD" or len(letter) != 1:
                    raise ValueError("correct_option must be A, B, C, or D")
                options = [row[f"option_{key}"] for key in "abcd"]
                payload = {
                    "text": row["question"],
                    "options": options,
                    "correct_option": "ABCD".index(letter),
                    "explanation": row["explanation"],
                    "concept": row.get("concept") or "",
                }
                if row.get("repair_question", "").strip():
                    repair_letter = (
                        (row.get("repair_correct_option") or "").strip().upper()
                    )
                    if repair_letter not in "ABCD" or len(repair_letter) != 1:
                        raise ValueError("repair_correct_option must be A, B, C, or D")
                    payload["repair"] = {
                        "text": row["repair_question"],
                        "options": [
                            row.get(f"repair_option_{k}") or "" for k in "abcd"
                        ],
                        "correct_option": "ABCD".index(repair_letter),
                        "explanation": row.get("repair_explanation") or "",
                        "hint": row.get("repair_hint") or "",
                    }
                questions.append(QuestionInput.model_validate(payload).model_dump())
            except (ValueError, ValidationError) as error:
                errors.append(f"Row {row_number}: {str(error)[:350]}")
    except csv.Error:
        errors.append("Invalid CSV quoting. Use the downloadable template.")
    if not questions and not errors:
        errors.append("The CSV contains no questions.")
    # Partial imports are never silently accepted.
    return {"questions": [] if errors else questions, "errors": errors}
