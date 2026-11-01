from fractions import Fraction
import re

DENOMINATOR_PATTERN = re.compile(
    r"denominator(?:\s+of)?\s+(\d+)", re.IGNORECASE
)
FRACTION_PATTERN = re.compile(r"^([+-]?\d+)\s*/\s*([+-]?\d+)$")


def extract_required_denominator(question_text: str | None) -> int | None:
    if not question_text:
        return None
    match = DENOMINATOR_PATTERN.search(question_text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def answers_match(
    answer: str | None,
    expected_answer: str,
    *,
    question_text: str | None = None,
    required_denominator: int | None = None,
) -> bool:
    if answer is None:
        return False
    actual_text = answer.strip().casefold()
    expected_text = expected_answer.strip().casefold()
    if not actual_text:
        return False

    target_denominator = required_denominator
    if target_denominator is None and question_text:
        target_denominator = extract_required_denominator(question_text)

    if target_denominator is not None:
        match = FRACTION_PATTERN.match(actual_text)
        if not match:
            return False
        try:
            num = int(match.group(1))
            den = int(match.group(2))
            if den <= 0 or den != target_denominator:
                return False
            actual_fraction = Fraction(num, den)
            expected_fraction = Fraction(expected_text.replace(" ", ""))
            return actual_fraction == expected_fraction
        except (ValueError, ZeroDivisionError):
            return False

    if actual_text == expected_text:
        return True
    try:
        actual_fraction = Fraction(actual_text.replace(" ", ""))
        expected_fraction = Fraction(expected_text.replace(" ", ""))
    except (ValueError, ZeroDivisionError):
        return False
    return actual_fraction == expected_fraction
