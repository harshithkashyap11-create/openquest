const mongoose = require('mongoose');

const attemptSchema = new mongoose.Schema(
  {
    student: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Student',
      required: true,
    },
    assessment: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Assessment',
      required: true,
    },
    question: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Question',
      required: true,
    },
    selectedOption: {
      type: String,
      required: true,
    },
    isCorrect: {
      type: Boolean,
      required: true,
    },
    detectedMisconception: {
      code: { type: String, default: null },
      label: { type: String, default: null },
      description: { type: String, default: null },
      remedyRecommendation: { type: String, default: null },
    },
    nextAction: {
      type: String,
      enum: [
        'PROCEED_TO_NEXT_QUESTION',
        'TRIGGER_TARGETED_INTERVENTION',
        'COMPLETE_ASSESSMENT',
        'SCHEDULE_DIAGNOSTIC_RETEST',
      ],
      default: 'PROCEED_TO_NEXT_QUESTION',
    },
    responseLatencyMs: {
      type: Number,
      default: 0,
    },
  },
  { timestamps: true }
);

module.exports = mongoose.model('Attempt', attemptSchema);
