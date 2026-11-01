const express = require('express');
const router = express.Router();
const {
  submitAssessmentAnswer,
  getAssessments,
  getAssessmentById,
} = require('../controllers/assessmentController');

router.route('/')
  .get(getAssessments);

router.route('/submit')
  .post(submitAssessmentAnswer);

router.route('/:id')
  .get(getAssessmentById);

module.exports = router;
