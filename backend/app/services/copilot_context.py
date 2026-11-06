from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Class,
    Diagnosis,
    InterventionAssignment,
    LearningGroup,
    Question,
    Quiz,
    Student,
    Submission,
)
from app.schemas.copilot import ClassContextSummary, MisconceptionStat
from app.services.classroom_service import get_assessment_summary
from app.services.quiz_service import quiz_insights
from app.services.progress_service import get_class_progress
from app.subject_taxonomy import SUBJECT_TAXONOMY, get_taxonomy, is_follow_up_code


def extract_classroom_context(
    db: Session, class_id: UUID
) -> tuple[ClassContextSummary, str]:
    """Allowlisted, read-only extraction of classroom records for grounding AI Copilot.

    Guarantees:
    - Scoped strictly to the provided class_id.
    - Uses real database records via existing services.
    - No arbitrary SQL generation.
    - Returns both a structured summary and a verbatim grounding text block.
    """
    classroom = db.get(Class, class_id)
    if classroom is None:
        raise LookupError(f"Class '{class_id}' was not found")

    students = list(
        db.scalars(
            select(Student)
            .where(Student.class_id == class_id)
            .order_by(Student.student_code)
        )
    )
    student_codes = [s.student_code for s in students]

    # 1. Assessment submission and diagnosis summary
    assessment_summary = get_assessment_summary(db, class_id)

    # 2. Progress and reassessment metrics
    progress = get_class_progress(db, class_id)
    initial_info = progress.get("initial_assessment") or {}
    followup_info = progress.get("followup_assessment") or {}

    baseline_acc = initial_info.get("accuracy_percentage")
    baseline_sample = initial_info.get("sample_size", 0)
    reassess_acc = followup_info.get("accuracy_percentage")
    reassess_sample = followup_info.get("sample_size", 0)
    delta = progress.get("accuracy_change_percentage_points")
    students_needing_support_codes = [
        s.get("student_code")
        for s in progress.get("students_needing_support", [])
        if isinstance(s, dict) and s.get("student_code")
    ]

    # 3. Diagnoses and misconception frequencies
    diagnoses = list(
        db.scalars(
            select(Diagnosis)
            .join(Diagnosis.submission)
            .join(Submission.student)
            .where(Student.class_id == class_id)
            .options(
                joinedload(Diagnosis.submission).joinedload(Submission.student),
                joinedload(Diagnosis.submission).joinedload(Submission.question),
            )
        )
    )

    # Group diagnoses by misconception code
    tax_items = {item.code: item for item in get_taxonomy(classroom.subject, classroom.topic)} if (classroom.subject, classroom.topic) in SUBJECT_TAXONOMY else {}

    misc_students = defaultdict(set)
    misc_evidence = defaultdict(list)
    followup_students = set()

    for diag in diagnoses:
        code = diag.misconception_code
        student_code = diag.submission.student.student_code
        misc_students[code].add(student_code)
        if diag.evidence and diag.evidence.strip() and len(misc_evidence[code]) < 3:
            misc_evidence[code].append(diag.evidence.strip())
        if is_follow_up_code(code) or diag.status == "needs_followup":
            followup_students.add(student_code)

    top_misconceptions: list[MisconceptionStat] = []
    for code, stus in sorted(misc_students.items(), key=lambda x: len(x[1]), reverse=True):
        tax = tax_items.get(code)
        cat = tax.category if tax else "General misunderstanding"
        desc = tax.description if tax else ""
        top_misconceptions.append(
            MisconceptionStat(
                code=code,
                category=cat,
                description=desc,
                student_count=len(stus),
                affected_students=sorted(stus),
                sample_evidence=misc_evidence.get(code, []),
            )
        )

    # Identify students needing attention:
    # - Low baseline accuracy or needing support
    # - Diagnosed with insufficient evidence / needs follow-up
    # - Incomplete or missing assessment
    students_needing_attention = set(students_needing_support_codes) | followup_students
    for st in assessment_summary.students:
        if st.answered_questions == 0 or st.pending_diagnoses > 0:
            students_needing_attention.add(st.student_code)

    # 4. Groups and Interventions
    groups = list(
        db.scalars(
            select(LearningGroup)
            .where(LearningGroup.class_id == class_id)
        )
    )
    approved_groups = [g for g in groups if g.review_status == "approved"]

    assigned_interventions_count = db.scalar(
        select(func.count(InterventionAssignment.id))
        .join(InterventionAssignment.student)
        .where(Student.class_id == class_id)
    ) or 0

    # Keep published quizzes distinct from legacy topic assessments. Only the
    # three newest are sent to bound prompt size; private conversations stay out.
    quiz_reports = []
    for quiz in db.scalars(select(Quiz).where(Quiz.class_id == class_id, Quiz.status == 'published').order_by(Quiz.created_at.desc(), Quiz.id).limit(3)):
        report = quiz_insights(db, quiz)
        quiz_reports.append({'title': quiz.title, 'submitted_students': report['submitted_students'],
            'questions': [{'ordinal': q['ordinal'], 'text': q['text'],
                           'wrong_answers': q['answered_students'] - q['correct_students'],
                           'reflected_students': q['reflected_students'], 'uncertain_students': q['uncertain_students'],
                           'themes': q['themes']} for q in report['questions']]})

    from app.services.studio_service import class_report
    studio = class_report(db, class_id)
    studio_summary = {'submitted_students': studio['submitted_students'], 'saved_attempts': len(studio['work']),
                      'standards': studio['standards'][:80], 'note': studio['note']}

    summary = ClassContextSummary(
        class_id=classroom.id,
        class_name=classroom.class_name,
        subject=classroom.subject,
        topic=classroom.topic,
        total_students=len(students),
        submitted_students=assessment_summary.submitted_students,
        answered_questions=assessment_summary.answered_questions,
        diagnosed_answers=assessment_summary.diagnosed_answers,
        pending_diagnoses=assessment_summary.pending_diagnoses,
        baseline_accuracy=baseline_acc,
        baseline_sample_size=baseline_sample,
        reassessment_accuracy=reassess_acc,
        reassessment_sample_size=reassess_sample,
        accuracy_delta=delta,
        top_misconceptions=top_misconceptions,
        students_needing_attention=sorted(students_needing_attention),
        groups_count=len(groups),
        approved_groups_count=len(approved_groups),
        assigned_interventions_count=assigned_interventions_count,
        quiz_reports=quiz_reports,
        studio_report=studio_summary,
    )

    # Build grounded text block for model consumption
    grounding_lines = [
        f"VERIFIED CLASSROOM GROUND TRUTH:",
        "- Class: selected authorized classroom",
        f"- Subject: {classroom.subject}",
        f"- Topic: {classroom.topic}",
        f"- Total Enrolled Students: {len(students)}",
        f"- Assessment Submissions: {assessment_summary.submitted_students} of {len(students)} students submitted ({assessment_summary.answered_questions} total responses, {assessment_summary.diagnosed_answers} diagnosed, {assessment_summary.pending_diagnoses} pending diagnosis)",
    ]

    if baseline_acc is not None:
        grounding_lines.append(
            f"- Baseline Accuracy: {baseline_acc:.1f}% (Sample: {baseline_sample} submissions)"
        )
    else:
        grounding_lines.append("- Baseline Accuracy: Not yet available")

    if reassess_acc is not None:
        delta_str = f" ({'+' if delta >= 0 else ''}{delta:.1f} percentage points)" if delta is not None else ""
        grounding_lines.append(
            f"- Reassessment Accuracy: {reassess_acc:.1f}% (Sample: {reassess_sample} reassessments){delta_str}"
        )
    else:
        grounding_lines.append("- Reassessment Accuracy: No reassessments completed yet")

    if top_misconceptions:
        grounding_lines.append("- Frequently Occurring Misconceptions:")
        for m in top_misconceptions:
            ev_str = f" | Evidence quote: \"{m.sample_evidence[0]}\"" if m.sample_evidence else ""
            grounding_lines.append(
                f"  * {m.code} ({m.category}): {m.student_count} student(s) . {m.description}"
            )
    else:
        grounding_lines.append("- Misconceptions: None diagnosed yet")

    if students_needing_attention:
        grounding_lines.append(
            f"- Students Needing Immediate Attention: {len(students_needing_attention)} (identities withheld from provider)"
        )

    grounding_lines.append(
        f"- Grouping & Interventions: {len(groups)} group(s) proposed, {len(approved_groups)} approved, {assigned_interventions_count} student intervention assignment(s) created."
    )

    if quiz_reports:
        import json
        grounding_lines.append("PUBLISHED QUIZ EVIDENCE (separate from baseline assessments; themes are tentative, not diagnoses):")
        grounding_lines.append(json.dumps(quiz_reports, ensure_ascii=False))
    if studio_summary['saved_attempts']:
        import json
        grounding_lines.append('CLASSROOM STUDIO: observed latest-attempt points; pending reviews do not establish mastery. No audio or drawing has been analyzed.')
        grounding_lines.append(json.dumps(studio_summary, ensure_ascii=False))
    return summary, "\n".join(grounding_lines)
