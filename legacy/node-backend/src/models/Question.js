const mongoose = require('mongoose');

const optionSchema = new mongoose.Schema({
  id: {
    type: String, // 'A', 'B', 'C', 'D'
    required: true,
  },
  text: {
    type: String,
    required: true,
  },
  isCorrect: {
    type: Boolean,
    default: false,
  },
  misconceptionCode: {
    type: String, // e.g., 'ADD_NUM_AND_DENOM'
    default: null,
  },
  misconceptionDescription: {
    type: String,
    default: null,
  },
});

const questionSchema = new mongoose.Schema(
  {
    text: {
      type: String,
      required: [true, 'Question text is required'],
    },
    topic: {
      type: String,
      default: 'Fractions',
    },
    subtopic: {
      type: String,
      default: 'Fraction Addition & Comparison',
    },
    difficulty: {
      type: String,
      enum: ['easy', 'medium', 'hard'],
      default: 'medium',
    },
    options: [optionSchema],
    correctOptionId: {
      type: String,
      required: true,
    },
    explanation: {
      type: String,
    },
  },
  { timestamps: true }
);

module.exports = mongoose.model('Question', questionSchema);
