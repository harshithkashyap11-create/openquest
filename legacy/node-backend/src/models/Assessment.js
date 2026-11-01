const mongoose = require('mongoose');

const assessmentSchema = new mongoose.Schema(
  {
    title: {
      type: String,
      required: [true, 'Assessment title is required'],
      trim: true,
    },
    description: {
      type: String,
      default: '',
    },
    topic: {
      type: String,
      default: 'Fractions',
    },
    grade: {
      type: Number,
      default: 5,
    },
    questions: [
      {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Question',
      },
    ],
    status: {
      type: String,
      enum: ['draft', 'active', 'archived'],
      default: 'active',
    },
  },
  { timestamps: true }
);

module.exports = mongoose.model('Assessment', assessmentSchema);
