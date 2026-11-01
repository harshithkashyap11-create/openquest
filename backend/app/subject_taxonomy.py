from dataclasses import dataclass


FOLLOW_UP_CODE = "FOLLOW_UP"
FOLLOW_UP_CODES = {"M06", FOLLOW_UP_CODE}


@dataclass(frozen=True)
class Misconception:
    code: str
    category: str
    description: str
    followup_question: str


SUBJECT_TAXONOMY: dict[tuple[str, str], tuple[Misconception, ...]] = {
    ("Mathematics", "Fractions"): (
        Misconception(
            "M01",
            "Additive numerator/denominator error",
            "Adds numerators and denominators directly instead of using equal-sized parts.",
            "Why must the parts have the same size before you add them?",
        ),
        Misconception(
            "M02",
            "Whole-number bias in comparison",
            "Uses whole-number reasoning about denominators when comparing fraction size.",
            "Which fraction is farther to the right on a number line, and why?",
        ),
        Misconception(
            "M03",
            "Common-denominator difficulty",
            "Has difficulty rewriting fractions with a common denominator.",
            "How could you rename both fractions using equal-sized parts?",
        ),
        Misconception(
            "M04",
            "Equivalence misconception",
            "Does not recognize fractions that represent the same value.",
            "Could a picture or number line show whether these fractions name the same amount?",
        ),
        Misconception(
            "M05",
            "Procedural/arithmetic slip",
            "Uses a sound fraction method but makes a procedural or arithmetic slip.",
            "Can you check each arithmetic step while keeping the same fraction method?",
        ),
        Misconception(
            "M06",
            "Insufficient evidence / uncertain",
            "The response does not provide enough evidence to identify a stable reasoning pattern.",
            "Can you show or explain how you decided on your answer?",
        ),
    ),
    ("Mathematics", "Basic algebra"): (
        Misconception(
            "ALG01",
            "Inverse-operation confusion",
            "Applies an operation to one side of an equation without preserving equality.",
            "What operation would undo the addition while keeping both sides equal?",
        ),
        Misconception(
            "ALG02",
            "Distribution error",
            "Multiplies only one term inside parentheses instead of every term.",
            "Which terms inside the parentheses must be multiplied?",
        ),
        Misconception(
            "ALG03",
            "Variable operation confusion",
            "Treats the variable as a label or reverses the operation used on it.",
            "What operation is being applied to the variable, and how can you undo it?",
        ),
    ),
    ("Science", "Force and motion"): (
        Misconception(
            "FM01",
            "Motion requires continuing force",
            "Believes an object must keep experiencing a forward force to maintain motion.",
            "What would happen to the object's motion if friction were nearly absent?",
        ),
        Misconception(
            "FM02",
            "Speed relationship confusion",
            "Does not relate average speed to distance divided by elapsed time.",
            "How can distance and elapsed time be used to calculate average speed?",
        ),
        Misconception(
            "FM03",
            "Force and acceleration confusion",
            "Confuses net force, mass, and acceleration in Newton's second law.",
            "How are net force, mass, and acceleration related?",
        ),
    ),
    ("Science", "Basic electricity"): (
        Misconception(
            "EL01",
            "Open-circuit misconception",
            "Does not recognize that a simple circuit needs a complete conducting path.",
            "Can charge travel through a circuit if there is a gap in the path?",
        ),
        Misconception(
            "EL02",
            "Current-used-up misconception",
            "Believes current is used up as it passes through components in series.",
            "How does current at different points in one simple series loop compare?",
        ),
        Misconception(
            "EL03",
            "Current and voltage confusion",
            "Treats current and voltage as interchangeable quantities.",
            "Which quantity describes charge flow, and which describes energy per charge?",
        ),
    ),
    ("English", "Grammar"): (
        Misconception(
            "GR01",
            "Tense consistency error",
            "Does not use verb tense consistently with the stated time.",
            "Which time word tells you the tense the sentence needs?",
        ),
        Misconception(
            "GR02",
            "Pronoun-antecedent agreement",
            "Chooses a pronoun that does not agree with or clearly refer to its antecedent.",
            "Which noun does the pronoun replace, and does it agree with that noun?",
        ),
        Misconception(
            "GR03",
            "Sentence conventions",
            "Misses capitalization or terminal punctuation needed for a complete sentence.",
            "What should a reader see at the start and end of a complete sentence?",
        ),
    ),
    ("English", "Subject-verb agreement"): (
        Misconception(
            "SV01",
            "Intervening-noun distraction",
            "Matches the verb to a nearby noun instead of the sentence's subject.",
            "What is the subject of the sentence if you set the describing phrase aside?",
        ),
        Misconception(
            "SV02",
            "Singular/plural agreement",
            "Does not match the verb form to a singular or plural subject.",
            "Is the subject singular or plural, and which verb form agrees?",
        ),
        Misconception(
            "SV03",
            "Compound-subject agreement",
            "Treats a compound subject joined by 'and' as singular.",
            "How many people or things are included in the subject joined by 'and'?",
        ),
    ),
}


def get_taxonomy(subject: str, topic: str) -> tuple[Misconception, ...]:
    try:
        return SUBJECT_TAXONOMY[(subject.strip(), topic.strip())]
    except KeyError as error:
        raise ValueError(f"Unsupported subject and topic: {subject}/{topic}") from error


def taxonomy_codes(subject: str, topic: str) -> set[str]:
    return {item.code for item in get_taxonomy(subject, topic)}


def misconception_description(
    subject: str, topic: str, code: str
) -> str:
    return next(
        (item.description for item in get_taxonomy(subject, topic) if item.code == code),
        "",
    )


def is_follow_up_code(code: str) -> bool:
    return code in FOLLOW_UP_CODES


def all_misconception_codes() -> set[str]:
    return {
        item.code
        for taxonomy in SUBJECT_TAXONOMY.values()
        for item in taxonomy
    } | {FOLLOW_UP_CODE, "CORRECT"}
