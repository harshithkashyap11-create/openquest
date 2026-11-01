const mongoose = require('mongoose');

const studentSchema = new mongoose.Schema(
  {
    name: {
      type: String,
      required: [true, 'Student name is required'],
      trim: true,
    },
    email: {
      type: String,
      required: [true, 'Student email is required'],
      unique: true,
      lowercase: true,
      trim: true,
    },
    grade: {
      type: Number,
      default: 5,
    },
    identifiedMisconceptions: [
      {
        misconceptionCode: String,
        label: String,
        detectedAt: { type: Date, default: Date.now },
        frequency: { type: Number, default: 1 },
      },
    ],
  },
  { timestamps: true }
);

module.exports = mongoose.model('Student', studentSchema);
