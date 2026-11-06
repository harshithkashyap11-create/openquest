"""Inclusive lessons must not expose teacher-only information or stale review."""
from app.services.inclusive_learning import check_adaptation, student_content


def test_verification_flags_missing_objectives_and_never_claims_semantic_certainty():
    source = {'objectives': ['Explain photosynthesis'], 'text': 'Plants use light.'}
    draft = {'title': 'Plants', 'objectives': [], 'text': 'Plants use light.', 'questions': []}
    findings = check_adaptation(source, draft)
    assert any(f['status'] == 'needs_review' and 'objective' in f['message'].lower() for f in findings)
    assert any(f['status'] == 'needs_review' and 'teacher' in f['message'].lower() for f in findings)


def test_student_content_never_exposes_answer_keys_or_teacher_metadata():
    draft = {'title': 'Plants', 'objectives': ['Explain'], 'text': 'Plants use light.',
             'questions': [{'prompt': 'What do plants use?', 'answer': 'light', 'hints': ['Look up']}],
             'supports': ['reading'], 'verification': {'secret': True}}
    result = student_content(draft)
    assert result == {'title': 'Plants', 'objectives': ['Explain'], 'text': 'Plants use light.',
                      'questions': [{'prompt': 'What do plants use?', 'hints': ['Look up']}]}


def test_accessbridge_catalog_exposes_selectable_supports():
    from app.accessbridge.services.verification_engine import load_profiles
    profiles = load_profiles()
    assert {p.profile_id for p in profiles} == {'learner_reading', 'learner_attention', 'learner_visual'}
    assert all(p.accommodation_requirements for p in profiles)


def test_selected_supports_can_be_combined_without_assuming_a_diagnosis():
    from app.services.inclusive_learning import selected_profile
    profile = selected_profile(['READ-002', 'ATTN-001'])
    assert {item.accommodation_id for item in profile.accommodation_requirements} == {'READ-002', 'ATTN-001'}


def test_unknown_support_is_rejected():
    import pytest
    from app.services.inclusive_learning import selected_profile
    with pytest.raises(ValueError, match='Unknown support'):
        selected_profile(['not-a-support'])


def test_accessbridge_document_imports_word_and_pdf():
    import io
    import pytest
    pytest.importorskip('docx')
    pytest.importorskip('pymupdf')
    from docx import Document
    from reportlab.pdfgen import canvas
    from app.accessbridge.services.document_parser import parse_document
    doc = Document(); doc.add_heading('Plants', 1); doc.add_paragraph('Plants need light and water to make their food.')
    word = io.BytesIO(); doc.save(word)
    parsed = parse_document('lesson.docx', word.getvalue())
    assert any('light and water' in block.text for block in parsed.blocks)
    pdf = io.BytesIO(); page = canvas.Canvas(pdf); page.drawString(60, 750, 'Plants need light and water to make their food.'); page.save()
    parsed = parse_document('lesson.pdf', pdf.getvalue())
    assert any('light and water' in block.text for block in parsed.blocks)
