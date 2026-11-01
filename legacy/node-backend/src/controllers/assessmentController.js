const mongoose = require('mongoose');
const Student = require('../models/Student');
const Assessment = require('../models/Assessment');
const Question = require('../models/Question');
const Attempt = require('../models/Attempt');
const { diagnoseAnswer } = require('../services/misconceptionService');

/**
 * POST /api/v1/assessments/submit
 * Submits a question attempt within an assessment.
 *
 * Steps:
 * 1. Validate the student and assessment.
 * 2. Fetch the question from MongoDB.
 * 3. Check the submitted answer.
 * 4. Identify a possible misconception using the question mapping.
 * 5. Save the attempt.
 * 6. Return the next action.
 */
exports.submitAssessmentAnswer = async (req, res) => {
  try {
    const { studentId, assessmentId, questionId, selectedOption, responseLatencyMs } = req.body;

    // 1. Validate input payload
    if (!studentId || !assessmentId || !questionId || selectedOption === undefined) {
      return res.status(400).json({
        success: false,
        error: 'Validation failed: studentId, assessmentId, questionId, and selectedOption are required.',
      });
    }

    if (!mongoose.Types.ObjectId.isValid(studentId) ||
        !mongoose.Types.ObjectId.isValid(assessmentId) ||
        !mongoose.Types.ObjectId.isValid(questionId)) {
      return res.status(400).json({
        success: false,
        error: 'Invalid ObjectId format provided for studentId, assessmentId, or questionId.',
      });
    }

    // 1b. Validate Student and Assessment existence
    const [student, assessment] = await Promise.all([
      Student.findById(studentId),
      Assessment.findById(assessmentId),
    ]);

    if (!student) {
      return res.status(404).json({
        success: false,
        error: `Student not found with ID: ${studentId}`,
      });
    }

    if (!assessment) {
      return res.status(404).json({
        success: false,
        error: `Assessment not found with ID: ${assessmentId}`,
      });
    }

    // 2. Fetch the question from MongoDB
    const question = await Question.findById(questionId);
    if (!question) {
      return res.status(404).json({
        success: false,
        error: `Question not found with ID: ${questionId}`,
      });
    }

    // 3 & 4. Check submitted answer and identify possible misconception using question mapping
    const diagnostic = diagnoseAnswer(question, selectedOption);

    // 5. Save the attempt
    const attempt = await Attempt.create({
      student: student._id,
      assessment: assessment._id,
      question: question._id,
      selectedOption: String(selectedOption).toUpperCase(),
      isCorrect: diagnostic.isCorrect,
      detectedMisconception: diagnostic.detectedMisconception,
      nextAction: diagnostic.nextAction,
      responseLatencyMs: responseLatencyMs || 0,
    });

    // Update student's identified misconceptions if found
    if (diagnostic.detectedMisconception?.code && diagnostic.detectedMisconception.code !== 'UNMAPPED_INCORRECT') {
      const existingGapIndex = student.identifiedMisconceptions.findIndex(
        (m) => m.misconceptionCode === diagnostic.detectedMisconception.code
      );

      if (existingGapIndex > -1) {
        student.identifiedMisconceptions[existingGapIndex].frequency += 1;
        student.identifiedMisconceptions[existingGapIndex].detectedAt = new Date();
      } else {
        student.identifiedMisconceptions.push({
          misconceptionCode: diagnostic.detectedMisconception.code,
          label: diagnostic.detectedMisconception.label,
          detectedAt: new Date(),
          frequency: 1,
        });
      }
      await student.save();
    }

    // 6. Return response with attempt, diagnosis, and next action
    return res.status(200).json({
      success: true,
      data: {
        attemptId: attempt._id,
        isCorrect: diagnostic.isCorrect,
        correctOptionId: diagnostic.isCorrect ? undefined : question.correctOptionId,
        explanation: question.explanation,
        detectedMisconception: diagnostic.detectedMisconception,
        nextAction: diagnostic.nextAction,
        feedback: diagnostic.feedback,
        submittedAt: attempt.createdAt,
      },
    });
  } catch (error) {
    console.error('Error in submitAssessmentAnswer:', error);
    return res.status(500).json({
      success: false,
      error: 'Internal server error while processing assessment submission.',
      details: error.message,
    });
  }
};

/**
 * GET /api/v1/assessments
 * List available assessments
 */
exports.getAssessments = async (req, res) => {
  try {
    const assessments = await Assessment.find({ status: 'active' }).populate('questions');
    res.status(200).json({ success: true, count: assessments.length, data: assessments });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};

/**
 * GET /api/v1/assessments/:id
 * Get single assessment with questions
 */
exports.getAssessmentById = async (req, res) => {
  try {
    const assessment = await Assessment.findById(req.params.id).populate('questions');
    if (!assessment) {
      return res.status(404).json({ success: false, error: 'Assessment not found' });
    }
    res.status(200).json({ success: true, data: assessment });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};
