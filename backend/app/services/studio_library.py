"""Small original starter bank. These are not competitor items or certified standards."""
from app.question_catalog import QUESTION_CATALOG

# Deliberate wrong choices are teaching prompts, not diagnoses of a learner.
DISTRACTORS = {
 'Q01': [('2/5', 'Adds both denominators'), ('2/6', 'Multiplies denominators without equivalent numerators'), ('1/6', 'Subtracts numerators')],
 'Q02': [('1/8', 'Treats larger denominators as larger fractions'), ('Equal', 'Ignores denominator size'), ('Cannot compare', 'Needs a representation of equal wholes')],
 'Q03': [('No', 'Treats different numerals as different values'), ('Only when added', 'Confuses equivalence with an operation'), ('Cannot tell', 'Needs an equal-parts representation')],
 'Q04': [('2/9', 'Adds denominators'), ('2/6', 'Does not rewrite equivalent numerators'), ('1/9', 'Multiplies denominators')],
 'Q05': [('2/3', 'Compares denominators alone'), ('Equal', 'Treats nearby fractions as equal'), ('Cannot compare', 'Needs a common representation')],
 'Q06': [('7', 'Subtracts without dividing'), ('5.5', 'Divides before isolating the variable'), ('16', 'Moves terms without preserving equality')],
 'Q07': [('3x + 2', 'Distributes to only one term'), ('x + 6', 'Distributes to the constant only'), ('5x', 'Combines unlike terms')],
 'Q08': [('0.75', 'Divides rather than multiplies'), ('7', 'Adds the divisor'), ('-12', 'Introduces an unnecessary negative sign')],
 'Q09': [('180 m/s', 'Multiplies distance and time'), ('0.2 m/s', 'Divides time by distance'), ('24 m/s', 'Subtracts time from distance')],
 'Q10': [('It stops immediately.', 'Assumes motion requires continuous applied force'), ('It accelerates forever.', 'Confuses inertia with acceleration'), ('It reverses direction.', 'Infers a force without evidence')],
 'Q11': [('16 m/s^2', 'Multiplies force by mass'), ('0.25 m/s^2', 'Reverses force and mass'), ('6 m/s^2', 'Subtracts mass from force')],
 'Q12': [('An open gap', 'Confuses open and closed paths'), ('Either', 'Ignores the conducting path'), ('No battery or source', 'Omits the energy source')],
 'Q13': [('It stays lit.', 'Assumes separate paths in a series circuit'), ('It becomes brighter.', 'Overlooks the broken path'), ('It flashes forever.', 'Infers an energy source after disconnection')],
 'Q14': [('Current is used up.', 'Confuses current with energy transfer'), ('Current increases after each bulb.', 'Assumes components create charge'), ('Current exists only at the battery.', 'Does not trace the complete loop')],
 'Q15': [('walk', 'Does not mark past tense'), ('walks', 'Uses present tense for past time'), ('walking', 'Uses an incomplete verb phrase')],
 'Q16': [('his', 'Uses a singular possessive for a plural antecedent'), ('there', 'Confuses a place word with possession'), ('they', 'Uses a subject pronoun for possession')],
 'Q17': [('we read poems and stories', 'Omits sentence capitalization and final punctuation'), ('We read poems and stories', 'Omits final punctuation'), ('we read poems and stories.', 'Omits initial capitalization')],
 'Q18': [('are', 'Matches the verb to the nearby noun apples'), ('were', 'Changes tense without context'), ('be', 'Uses an uninflected verb')],
 'Q19': [('have', 'Matches players rather than each'), ('are', 'Changes the required verb'), ('having', 'Uses an incomplete verb phrase')],
 'Q20': [('studies', 'Treats a compound subject as singular'), ('studying', 'Uses an incomplete verb phrase'), ('is study', 'Adds an incorrect auxiliary')],
}


def library(subject=None, topic=None, query=''):
    result = []
    for index, (key, q) in enumerate(QUESTION_CATALOG.items()):
        if subject and q.subject != subject or topic and q.topic != topic:
            continue
        wrong = DISTRACTORS[key]
        # Fix an ambiguous inherited grammar prompt rather than perpetuate it.
        text = 'Choose the verb: Yesterday, Ravi ___ to school.' if key == 'Q15' else q.question_text
        position = index % 4
        options = [item[0] for item in wrong]; options.insert(position, q.correct_answer)
        row = {'id': f'bank-{key}', 'kind': 'choice', 'text': text, 'options': options, 'answer': position,
               'explanation': q.explanation_expected, 'hint': 'Explain the first step before choosing an answer.',
               'concept': q.topic, 'standard': 'CP.' + q.topic.upper().replace(' ', '_').replace('-', '_'),
               'points': 1, 'subject': q.subject, 'topic': q.topic, 'provenance': 'ClassPulse original starter content; custom standard label',
               'distractors': {str(i): next(item[1] for item in wrong if item[0] == option) for i, option in enumerate(options) if i != position}}
        searchable = {k: v for k, v in row.items() if k not in {'provenance', 'id'}}
        if not query or query.casefold() in str(searchable).casefold():
            result.append(row)
    return result
