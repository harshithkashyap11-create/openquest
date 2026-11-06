"""Fast synthetic identities mapped to existing roster records in demo mode."""
import re
from sqlalchemy import select
from fastapi import HTTPException
from app.models import Class, Student


def demo_courses(db, role, username):
    username = username.strip().casefold()
    subjects = {'math1': 'Mathematics', 'science1': 'Science', 'english1': 'English', 'teacher1': None}
    classes = list(db.scalars(select(Class).order_by(Class.subject, Class.topic, Class.id)))
    if role == 'teacher':
        if username not in subjects:
            raise HTTPException(404, 'Use math1, science1, english1 or teacher1 for the demo.')
        classes = [c for c in classes if subjects[username] is None or c.subject == subjects[username]]
        if classes:
            teacher = classes[0].teacher_id
            classes = [c for c in classes if c.teacher_id == teacher]
        courses = [course_view(c) for c in classes]
    else:
        match = re.fullmatch(r'(?:student|s)\s*0*(\d+)', username)
        courses = []
        # A synthetic demo alias groups the same ordinal across class rosters;
        # required-auth memberships are never inferred this way.
        for c in classes:
            roster = list(db.scalars(select(Student).where(Student.class_id == c.id).order_by(Student.student_code, Student.id)))
            if match:
                ordinal = int(match[1])
                student = roster[ordinal - 1] if 0 < ordinal <= len(roster) else None
            else:
                student = next((s for s in roster if s.student_code.casefold() == username), None)
            if student:
                courses.append({**course_view(c), 'student_id': str(student.id), 'student_code': student.student_code})
    if not courses:
        raise HTTPException(404, 'No demo courses found for this username. Try S1 or import the sample classes.')
    return {'role': role, 'username': username, 'demo': True, 'authenticated': False, 'courses': courses}


def course_view(c):
    return {'id': str(c.id), 'class_name': c.class_name, 'subject': c.subject, 'topic': c.topic}
