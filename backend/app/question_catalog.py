from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogQuestion:
    question_text: str
    correct_answer: str
    explanation_expected: str
    topic: str = "Fractions"
    accepted_answers: tuple[str, ...] = ()
    subject: str = "Mathematics"


# Operational question key, intentionally separate from offline ground-truth labels.
QUESTION_CATALOG: dict[str, CatalogQuestion] = {
    "Q01": CatalogQuestion(
        question_text="Calculate 1/2 + 1/3.",
        correct_answer="5/6",
        explanation_expected=(
            "Key concept: add unlike denominators by rewriting both fractions "
            "with a common denominator."
        ),
    ),
    "Q02": CatalogQuestion(
        question_text="Which is larger, 1/4 or 1/8?",
        correct_answer="1/4",
        explanation_expected=(
            "Key concept: unit fractions with larger denominators represent "
            "smaller equal-sized parts."
        ),
    ),
    "Q03": CatalogQuestion(
        question_text="Are 1/2 and 2/4 equivalent?",
        correct_answer="Yes",
        explanation_expected=(
            "Key concept: equivalent fractions name the same value; multiplying "
            "the numerator and denominator of 1/2 by 2 gives 2/4."
        ),
    ),
    "Q04": CatalogQuestion(
        question_text="Add 1/3 + 1/6.",
        correct_answer="1/2",
        explanation_expected=(
            "Key concept: rewrite 1/3 as 2/6, add to get 3/6, then simplify to 1/2."
        ),
    ),
    "Q05": CatalogQuestion(
        question_text="Compare 2/3 and 3/4.",
        correct_answer="3/4",
        explanation_expected=(
            "Key concept: compare equivalent fractions with denominator 12; "
            "2/3 is 8/12 and 3/4 is 9/12."
        ),
        accepted_answers=("3/4", "8/12 and 9/12"),
    ),
    "Q06": CatalogQuestion(
        "Solve 2x + 3 = 11.",
        "4",
        "Subtract 3 from both sides, then divide both sides by 2.",
        topic="Basic algebra",
    ),
    "Q07": CatalogQuestion(
        "Expand 3(x + 2).",
        "3x + 6",
        "Distribute 3 to both terms inside the parentheses.",
        topic="Basic algebra",
    ),
    "Q08": CatalogQuestion(
        "Solve x/4 = 3.",
        "12",
        "Multiply both sides by 4 to preserve equality.",
        topic="Basic algebra",
    ),
    "Q09": CatalogQuestion(
        "A bicycle travels 30 meters in 6 seconds. What is its average speed?",
        "5 m/s",
        "Average speed equals distance divided by elapsed time: 30 ÷ 6 = 5 m/s.",
        topic="Force and motion",
        subject="Science",
    ),
    "Q10": CatalogQuestion(
        "A puck moves on nearly frictionless ice. What happens after the push stops?",
        "It continues moving at constant velocity.",
        "With negligible friction and no net force, the puck continues at constant velocity.",
        topic="Force and motion",
        subject="Science",
    ),
    "Q11": CatalogQuestion(
        "A 2 kg cart has a net force of 8 N. What is its acceleration?",
        "4 m/s^2",
        "Newton's second law gives acceleration = net force ÷ mass = 8 ÷ 2 = 4 m/s^2.",
        topic="Force and motion",
        subject="Science",
    ),
    "Q12": CatalogQuestion(
        "What must a simple circuit have for its bulb to light: a closed loop or an open gap?",
        "A closed loop",
        "A complete conducting loop allows charge to flow through the bulb.",
        topic="Basic electricity",
        subject="Science",
    ),
    "Q13": CatalogQuestion(
        "Two bulbs are in one simple series circuit. What happens to the other bulb if one is removed?",
        "It goes out.",
        "Removing one series component opens the only current path, so both bulbs go out.",
        topic="Basic electricity",
        subject="Science",
    ),
    "Q14": CatalogQuestion(
        "In a simple series circuit, is current used up or the same through each component?",
        "The current is the same through each component.",
        "In a series circuit, the current is the same at every point in the loop.",
        topic="Basic electricity",
        subject="Science",
    ),
    "Q15": CatalogQuestion(
        "Choose the correct verb: Yesterday, Ravi (walk/walks) to school.",
        "walked",
        "Yesterday signals past time, so use the past-tense verb walked.",
        topic="Grammar",
        subject="English",
    ),
    "Q16": CatalogQuestion(
        "Choose the pronoun: Ana and Bo brought ___ books.",
        "their",
        "Their refers to the plural antecedent Ana and Bo.",
        topic="Grammar",
        subject="English",
    ),
    "Q17": CatalogQuestion(
        "Add capitalization and punctuation: we read poems and stories",
        "We read poems and stories.",
        "A complete sentence begins with a capital letter and ends with a period.",
        topic="Grammar",
        subject="English",
        accepted_answers=("We read poems and stories.",),
    ),
    "Q18": CatalogQuestion(
        "Choose the verb: The basket of apples (is/are) on the table.",
        "is",
        "Basket is the singular subject; the intervening plural noun apples does not change it.",
        topic="Subject-verb agreement",
        subject="English",
    ),
    "Q19": CatalogQuestion(
        "Choose the verb: Each of the players (has/have) a number.",
        "has",
        "Each is singular, so it takes the singular verb has.",
        topic="Subject-verb agreement",
        subject="English",
    ),
    "Q20": CatalogQuestion(
        "Choose the verb: Mina and her brother (study/studies) after school.",
        "study",
        "The compound subject Mina and her brother is plural, so use study.",
        topic="Subject-verb agreement",
        subject="English",
    ),
}
