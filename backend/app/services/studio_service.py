"""Classroom tools built from public workflow patterns and original content."""
import base64
import binascii
import csv
import io
import re
from collections import defaultdict
from fractions import Fraction
from uuid import UUID
from xml.sax.saxutils import escape
from fastapi import HTTPException
from sqlalchemy import select
from app.models import Student
from app.models.studio import StudioActivity, StudioWork, StudioSet


def activity_for(db, class_id, activity_id, published=False):
    a = db.get(StudioActivity, activity_id)
    if not a or a.class_id != class_id or (published and a.status != 'published'):
        raise HTTPException(404, 'Activity not found in this course')
    return a


def work_for(db, class_id, work_id, student_id=None):
    w = db.get(StudioWork, work_id)
    if not w or w.class_id != class_id or (student_id and w.student_id != student_id):
        raise HTTPException(404, 'Student work not found')
    return w


def activity_view(a, student=False):
    questions = a.questions
    if student:
        questions = [{k: v for k, v in q.items() if k not in {'answer', 'explanation', 'distractors'}} for q in questions]
    return {'id': str(a.id), 'class_id': str(a.class_id), 'title': a.title, 'status': a.status, 'questions': questions, 'max_attempts': a.max_attempts}


def work_view(w):
    return {'id': str(w.id), 'activity_id': str(w.activity_id), 'student_id': str(w.student_id), 'attempt': w.attempt,
            'answers': w.answers, 'reasoning': w.reasoning, 'media': w.media, 'results': w.results, 'conversations': w.conversations,
            'score': sum(r['earned'] or 0 for r in w.results.values()), 'possible': sum(r['possible'] for r in w.results.values()),
            'pending_review': sum(r['earned'] is None for r in w.results.values()), 'created_at': w.created_at,
            'lms_status': (w.lms_receipt or {}).get('status', 'not_sent')}


def attempts_for(db, student, a):
    return list(db.scalars(select(StudioWork).where(StudioWork.student_id == student.id, StudioWork.activity_id == a.id).order_by(StudioWork.attempt)))


def unlock_reason(db, student, a):
    for s in db.scalars(select(StudioSet).where(StudioSet.class_id == student.class_id)):
        if str(a.id) not in s.activity_ids:
            continue
        for previous in s.activity_ids[:s.activity_ids.index(str(a.id))]:
            previous_activity = activity_for(db, student.class_id, UUID(previous))
            works = attempts_for(db, student, previous_activity)
            if not works:
                return f'Complete {previous_activity.title} first.'
            if not any(not work_view(w)['pending_review'] and work_view(w)['score'] * 100 >= s.minimum_percent * work_view(w)['possible'] for w in works):
                return f'Reach {s.minimum_percent}% on {previous_activity.title} after teacher review.'
    return None


def grade_answer(q, answer):
    kind = q['kind']; key = q.get('answer')
    if kind == 'writing':
        correct = None
    elif kind == 'numeric':
        try:
            correct = abs(Fraction(str(answer).strip()) - Fraction(key.strip())) <= Fraction(str(q.get('tolerance', 0)))
        except (ValueError, ZeroDivisionError, OverflowError):
            correct = False
    elif kind == 'short_answer':
        correct = isinstance(answer, str) and answer.strip().casefold() == key.strip().casefold()
    elif kind == 'multiple_select':
        correct = isinstance(answer, list) and all(type(i) is int for i in answer) and len(answer) == len(set(answer)) and set(answer) == set(key)
    elif kind in {'matching', 'categorize'}:
        correct = answer == key
    else:
        correct = type(answer) is int and answer == key
    signal = q.get('distractors', {}).get(str(answer), '') if correct is False and kind in {'choice', 'true_false'} else ''
    return {'correct': correct, 'earned': None if correct is None else q.get('points', 1) if correct else 0,
            'possible': q.get('points', 1), 'explanation': q.get('explanation', ''), 'signal': signal,
            'signal_note': 'Choice pattern; confirm with student reasoning.' if signal else '', 'comment': ''}


def validate_media(media, ids):
    if set(media) - ids:
        raise HTTPException(422, 'Unknown media question')
    for m in media.values():
        if set(m) - {'audio', 'mime', 'transcript', 'strokes'}:
            raise HTTPException(422, 'Unsupported media field')
        if m.get('audio'):
            if m.get('mime') not in {'audio/webm', 'audio/ogg', 'audio/mp4'}:
                raise HTTPException(422, 'Unsupported recording format')
            try:
                base64.b64decode(m['audio'], validate=True)
            except (ValueError, TypeError, binascii.Error) as error:
                raise HTTPException(422, 'Invalid audio recording') from error
        if m.get('strokes'):
            strokes = m['strokes']
            if not isinstance(strokes, list) or len(strokes) > 500:
                raise HTTPException(422, 'Drawing is too large')
            for stroke in strokes:
                if not isinstance(stroke, list) or len(stroke) > 3000 or any(not isinstance(p, list) or len(p) != 2 or any(type(v) not in {int, float} or not 0 <= v <= 2000 for v in p) for p in stroke):
                    raise HTTPException(422, 'Invalid drawing coordinates')


def submit_work(db, student, a, payload):
    previous = db.scalar(select(StudioWork).where(StudioWork.student_id == student.id, StudioWork.request_id == str(payload.request_id)))
    if previous:
        if previous.activity_id != a.id or previous.answers != payload.answers or previous.reasoning != payload.reasoning or previous.media != payload.media:
            raise HTTPException(409, 'This request was already used for different work')
        return work_view(previous)
    reason = unlock_reason(db, student, a)
    if reason:
        raise HTTPException(409, reason)
    works = attempts_for(db, student, a)
    if len(works) >= a.max_attempts:
        raise HTTPException(409, 'All attempts used. Ask your teacher to review your work.')
    ids = {q['id'] for q in a.questions}
    if set(payload.answers) != ids or set(payload.reasoning) - ids:
        raise HTTPException(422, 'Answer every question exactly once')
    for q in a.questions:
        answer = payload.answers[q['id']]
        kind = q['kind']
        if kind in {'choice', 'true_false'}:
            valid = type(answer) is int and 0 <= answer < len(q['options'])
        elif kind == 'multiple_select':
            valid = isinstance(answer, list) and bool(answer) and all(type(i) is int and 0 <= i < len(q['options']) for i in answer) and len(answer) == len(set(answer))
        elif kind in {'matching', 'categorize'}:
            valid = isinstance(answer, dict) and set(answer) == set(q['items']) and all(isinstance(v, str) and v in q['options'] for v in answer.values())
        else:
            valid = isinstance(answer, str) and bool(answer.strip()) and len(answer) <= 10000
        if not valid:
            raise HTTPException(422, f'Invalid or missing answer for {q["id"]}')
    validate_media(payload.media, ids)
    w = StudioWork(class_id=a.class_id, activity_id=a.id, student_id=student.id, request_id=str(payload.request_id), attempt=len(works) + 1,
                   answers=payload.answers, reasoning=payload.reasoning, media=payload.media, conversations={},
                   results={q['id']: grade_answer(q, payload.answers[q['id']]) for q in a.questions})
    db.add(w); db.commit()
    from app.services.studio_lms import maybe_passback
    maybe_passback(db, w)
    return work_view(w)


def class_report(db, class_id):
    activities = {a.id: a for a in db.scalars(select(StudioActivity).where(StudioActivity.class_id == class_id))}
    students = {s.id: s.student_code for s in db.scalars(select(Student).where(Student.class_id == class_id))}
    works = list(db.scalars(select(StudioWork).where(StudioWork.class_id == class_id).order_by(StudioWork.created_at, StudioWork.attempt, StudioWork.id)))
    latest = {}
    for w in works:
        latest[(w.student_id, w.activity_id)] = w
    standards = defaultdict(lambda: {'earned': 0, 'possible': 0, 'responses': 0, 'pending': 0})
    for w in latest.values():
        for q in activities[w.activity_id].questions:
            label = q.get('standard') or 'Untagged'
            r = w.results[q['id']]; row = standards[label]
            row['earned'] += r['earned'] or 0; row['possible'] += r['possible']; row['responses'] += 1; row['pending'] += r['earned'] is None
    return {'total_students': len(students), 'submitted_students': len({w.student_id for w in works}),
            'standards': [{'standard': label, **row} for label, row in sorted(standards.items())],
            'work': [{**work_view(w), 'student_code': students[w.student_id], 'title': activities[w.activity_id].title} for w in reversed(works)],
            'note': 'Latest attempt per student and activity is used for standards totals. Points are observed performance, not validated mastery.'}


def csv_cell(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value


def grade_csv(report):
    out = io.StringIO(); writer = csv.writer(out)
    writer.writerow(['student_code', 'activity', 'attempt', 'earned', 'possible', 'pending_review'])
    seen = set()
    for w in report['work']:
        key = (w['student_id'], w['activity_id'])
        if key in seen:
            continue
        seen.add(key)
        writer.writerow([csv_cell(w[k]) for k in ['student_code', 'title', 'attempt', 'score', 'possible', 'pending_review']])
    return out.getvalue()


def work_pdf(db, w):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    a = db.get(StudioActivity, w.activity_id); s = db.get(Student, w.student_id)
    out = io.BytesIO(); styles = getSampleStyleSheet(); flow = []
    # Use a Unicode font when installed; PDF glyph coverage is still font-dependent.
    from pathlib import Path
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    font = next((p for p in [Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'), Path('/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf'), Path('/usr/share/fonts/google-noto/NotoSans-Regular.ttf')] if p.exists()), None)
    if font and 'StudioSans' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('StudioSans', str(font)))
    if 'StudioSans' in pdfmetrics.getRegisteredFontNames():
        for style in styles.byName.values():
            style.fontName = 'StudioSans'
    def para(text, style='BodyText'):
        flow.append(Paragraph(escape(str(text)).replace('\n', '<br/>'), styles[style])); flow.append(Spacer(1, 8))
    para(a.title, 'Title'); para(f'{s.student_code} · Attempt {w.attempt} · {work_view(w)["score"]}/{work_view(w)["possible"]}')
    for q in a.questions:
        r = w.results[q['id']]; para(q['text'], 'Heading2')
        answer = w.answers.get(q['id'], '')
        if q['kind'] in {'choice', 'true_false'} and type(answer) is int and 0 <= answer < len(q['options']):
            answer = q['options'][answer]
        elif q['kind'] == 'multiple_select' and isinstance(answer, list):
            answer = ', '.join(q['options'][i] for i in answer if type(i) is int and 0 <= i < len(q['options']))
        elif isinstance(answer, dict):
            answer = '; '.join(f'{k}: {v}' for k, v in answer.items())
        para(f'Answer: {answer}')
        para(f'Reasoning: {w.reasoning.get(q["id"], "")}'); para(f'Points: {r["earned"] if r["earned"] is not None else "Pending review"}/{r["possible"]}')
        if r.get('explanation'): para(r['explanation'])
        if r.get('comment'): para('Teacher: ' + r['comment'])
        media = w.media.get(q['id'], {})
        if media.get('transcript'): para('Transcript: ' + media['transcript'])
        if media.get('strokes'):
            from reportlab.graphics.shapes import Drawing, PolyLine
            drawing = Drawing(440, 185)
            for stroke in media['strokes']:
                if len(stroke) >= 2:
                    drawing.add(PolyLine([v for x, y in stroke for v in (x * 0.55, 185 - y * 0.55)]))
            flow.append(drawing)
        if media.get('audio'): para('An audio recording is retained with this work in Classroom Studio.')
        for message in w.conversations.get(q['id'], []): para(f'{message["role"]}: {message["content"]}')
    SimpleDocTemplate(out, rightMargin=44, leftMargin=44, title=a.title, author='ClassPulse AI').build(flow)
    return out.getvalue()


def import_pdf(payload):
    from pypdf import PdfReader
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
        if not content.startswith(b'%PDF'):
            raise ValueError('Not a PDF')
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted or len(reader.pages) > 30:
            raise HTTPException(422, 'Use an unencrypted PDF with at most 30 pages')
        text = '\n'.join(page.extract_text() or '' for page in reader.pages)[:100000]
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(422, 'This PDF could not be read') from error
    if not text.strip():
        raise HTTPException(422, 'This PDF has no selectable text. Use OCR first or paste the questions.')
    questions = []
    for block in re.split(r'(?m)^\s*\d+[.)]\s+', text)[1:41]:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        options = [m.group(1) for line in lines if (m := re.match(r'^[A-L][.)]\s+(.+)', line))]
        key = re.search(r'(?im)^\s*(?:answer|correct)\s*:\s*([A-L])\b', block)
        explanation = re.search(r'(?im)^\s*explanation\s*:\s*(.+)', block)
        questions.append({'id': f'import-{len(questions)+1}', 'kind': 'choice' if options else 'writing', 'text': lines[0], 'options': options,
                          'answer': ord(key[1].upper()) - ord('A') if key and options else None, 'explanation': explanation[1] if explanation else '', 'standard': '', 'points': 1})
    return {'questions': questions, 'text': text, 'provider': 'local_pdf_text',
            'note': 'Review extracted wording, answer keys and standards before saving. Missing keys must be supplied by the teacher.'}
