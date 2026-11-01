/**
 * Misconception Diagnostic Service
 * Maps student responses to educational misconceptions in fraction learning.
 */

const MISCONCEPTION_CATALOG = {
  ADD_NUM_AND_DENOM: {
    label: 'Whole Number Addition Bias',
    description:
      'Student adds numerators and denominators straight across (e.g., a/b + c/d = (a+c)/(b+d)), treating the numerator and denominator as separate independent integers.',
    remedyRecommendation:
      'Targeted visual intervention: Use fraction bars or visual pizza models showing that denominators represent part sizes, which cannot simply be summed.',
    severity: 'high',
  },
  LARGER_DENOMINATOR_LARGER_VALUE: {
    label: 'Inverse Size Neglect',
    description:
      'Student assumes that because a denominator is a larger integer, the fraction represents a larger quantity (e.g., 1/8 > 1/4 because 8 > 4).',
    remedyRecommendation:
      'Number line comparison and sharing contexts: Explore how dividing an object into more pieces makes each piece smaller.',
    severity: 'medium',
  },
  IGNORE_COMMON_DENOMINATOR: {
    label: 'Direct Numerator Operation',
    description:
      'Student adds or subtracts numerators while ignoring the necessity of equal part sizes / finding a common denominator.',
    remedyRecommendation:
      'Equivalence modeling: Show common denominator as finding common unit slices before combining.',
    severity: 'high',
  },
  CROSS_MULTIPLICATION_CONFUSION: {
    label: 'Algorithm Misapplication',
    description:
      'Student misapplies cross-multiplication or butterfly method inappropriately to simple fraction operations.',
    remedyRecommendation:
      'Conceptual grounding: Focus on meaning of fraction operations before algebraic shortcuts.',
    severity: 'medium',
  },
};

/**
 * Diagnoses an answer submission against a question.
 *
 * @param {Object} question - The Question document
 * @param {string} selectedOption - Option ID selected (e.g., 'A', 'B', 'C', 'D')
 * @returns {Object} Diagnostic result containing isCorrect, detectedMisconception, nextAction
 */
function diagnoseAnswer(question, selectedOption) {
  const isCorrect = String(question.correctOptionId).trim().toUpperCase() === String(selectedOption).trim().toUpperCase();

  if (isCorrect) {
    return {
      isCorrect: true,
      detectedMisconception: null,
      nextAction: 'PROCEED_TO_NEXT_QUESTION',
      feedback: 'Correct! Great understanding of fraction concepts.',
    };
  }

  // Find option details
  const chosenOption = question.options?.find(
    (opt) => String(opt.id).toUpperCase() === String(selectedOption).toUpperCase()
  );

  let misconceptionCode = chosenOption?.misconceptionCode || null;
  let customDescription = chosenOption?.misconceptionDescription || null;

  let misconceptionData = null;

  if (misconceptionCode && MISCONCEPTION_CATALOG[misconceptionCode]) {
    const catalogEntry = MISCONCEPTION_CATALOG[misconceptionCode];
    misconceptionData = {
      code: misconceptionCode,
      label: catalogEntry.label,
      description: customDescription || catalogEntry.description,
      remedyRecommendation: catalogEntry.remedyRecommendation,
      severity: catalogEntry.severity,
    };
  } else if (misconceptionCode) {
    misconceptionData = {
      code: misconceptionCode,
      label: 'Specific Concept Gap',
      description: customDescription || 'System identified a consistent patterned conceptual error.',
      remedyRecommendation: 'Focused conceptual review on this question topic.',
      severity: 'medium',
    };
  } else {
    misconceptionData = {
      code: 'UNMAPPED_INCORRECT',
      label: 'General Calculation Error',
      description: 'The response was incorrect, but did not match a known standard fraction misconception pattern.',
      remedyRecommendation: 'Review step-by-step arithmetic working.',
      severity: 'low',
    };
  }

  // Next action logic:
  // If a high-severity misconception is detected, propose targeted intervention.
  const nextAction =
    misconceptionData.severity === 'high'
      ? 'TRIGGER_TARGETED_INTERVENTION'
      : 'PROCEED_TO_NEXT_QUESTION';

  return {
    isCorrect: false,
    detectedMisconception: misconceptionData,
    nextAction,
    feedback: misconceptionData.description,
  };
}

module.exports = {
  MISCONCEPTION_CATALOG,
  diagnoseAnswer,
};
