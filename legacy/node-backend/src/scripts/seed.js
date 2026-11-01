require('dotenv').config();
const mongoose = require('mongoose');
const Student = require('../models/Student');
const Question = require('../models/Question');
const Assessment = require('../models/Assessment');
const Attempt = require('../models/Attempt');

const seedData = async () => {
  try {
    const mongoUri = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/classpulse';
    console.log(`Connecting to MongoDB at ${mongoUri}...`);
    await mongoose.connect(mongoUri);
    console.log('MongoDB connected successfully for seeding.');

    // Clear previous seed data
    await Promise.all([
      Student.deleteMany({}),
      Question.deleteMany({}),
      Assessment.deleteMany({}),
      Attempt.deleteMany({}),
    ]);
    console.log('Existing collections cleared.');

    // 1. Seed Student
    const student = await Student.create({
      name: 'Alex Rivera',
      email: 'alex.rivera@example.com',
      grade: 5,
      identifiedMisconceptions: [],
    });
    console.log(`Created Student: ${student.name} (ID: ${student._id})`);

    // 2. Seed Questions with Misconception Maps
    const q1 = await Question.create({
      text: 'What is 1/3 + 1/4?',
      topic: 'Fractions',
      subtopic: 'Addition with unlike denominators',
      difficulty: 'medium',
      options: [
        {
          id: 'A',
          text: '2/7',
          isCorrect: false,
          misconceptionCode: 'ADD_NUM_AND_DENOM',
          misconceptionDescription:
            'Added numerators (1+1=2) and denominators (3+4=7) straight across, treating them as independent integers.',
        },
        {
          id: 'B',
          text: '7/12',
          isCorrect: true,
          misconceptionCode: null,
          misconceptionDescription: null,
        },
        {
          id: 'C',
          text: '2/12',
          isCorrect: false,
          misconceptionCode: 'IGNORE_COMMON_DENOMINATOR',
          misconceptionDescription:
            'Found common denominator 12 by multiplying, but added numerators directly without converting unit fractions.',
        },
        {
          id: 'D',
          text: '1/7',
          isCorrect: false,
          misconceptionCode: 'UNMAPPED_INCORRECT',
          misconceptionDescription: 'Kept numerator 1 and added denominators 3 + 4 = 7.',
        },
      ],
      correctOptionId: 'B',
      explanation:
        'To add fractions with unlike denominators, find the lowest common denominator (12). 1/3 = 4/12 and 1/4 = 3/12. 4/12 + 3/12 = 7/12.',
    });

    const q2 = await Question.create({
      text: 'Which fraction is greater: 1/8 or 1/4?',
      topic: 'Fractions',
      subtopic: 'Unit fraction comparison',
      difficulty: 'easy',
      options: [
        {
          id: 'A',
          text: '1/8, because 8 is greater than 4',
          isCorrect: false,
          misconceptionCode: 'LARGER_DENOMINATOR_LARGER_VALUE',
          misconceptionDescription:
            'Assumes a larger denominator implies a larger fraction value (whole number magnitude bias).',
        },
        {
          id: 'B',
          text: '1/4, because the whole is divided into fewer, larger pieces',
          isCorrect: true,
          misconceptionCode: null,
          misconceptionDescription: null,
        },
        {
          id: 'C',
          text: 'They are equal in size',
          isCorrect: false,
          misconceptionCode: 'UNMAPPED_INCORRECT',
          misconceptionDescription: 'Believes all unit fractions have equivalent value.',
        },
      ],
      correctOptionId: 'B',
      explanation:
        '1/4 is greater than 1/8. As the denominator grows larger, each individual partition of the unit whole becomes smaller.',
    });

    const q3 = await Question.create({
      text: 'What is 2/5 + 1/5?',
      topic: 'Fractions',
      subtopic: 'Addition with like denominators',
      difficulty: 'easy',
      options: [
        {
          id: 'A',
          text: '3/10',
          isCorrect: false,
          misconceptionCode: 'ADD_NUM_AND_DENOM',
          misconceptionDescription:
            'Added denominators even though common denominator was already present (5+5=10).',
        },
        {
          id: 'B',
          text: '3/5',
          isCorrect: true,
          misconceptionCode: null,
          misconceptionDescription: null,
        },
        {
          id: 'C',
          text: '2/10',
          isCorrect: false,
          misconceptionCode: 'UNMAPPED_INCORRECT',
          misconceptionDescription: 'Calculation error.',
        },
      ],
      correctOptionId: 'B',
      explanation:
        'When fractions have the same denominator, keep the denominator and add the numerators: (2 + 1) / 5 = 3/5.',
    });

    console.log(`Created 3 diagnostic questions: [${q1._id}, ${q2._id}, ${q3._id}]`);

    // 3. Seed Assessment
    const assessment = await Assessment.create({
      title: 'Grade 5 Diagnostic: Fraction Foundations',
      description: 'Introductory diagnostic assessment evaluating student mental models in fraction arithmetic and comparisons.',
      topic: 'Fractions',
      grade: 5,
      questions: [q1._id, q2._id, q3._id],
      status: 'active',
    });
    console.log(`Created Assessment: "${assessment.title}" (ID: ${assessment._id})`);

    console.log('\n--- SEED COMPLETE ---');
    console.log('Test IDs for POST /api/v1/assessments/submit:');
    console.log(`studentId:    "${student._id}"`);
    console.log(`assessmentId: "${assessment._id}"`);
    console.log(`questionId:   "${q1._id}" (Question: 1/3 + 1/4)`);
    console.log('Option A ("2/7") triggers ADD_NUM_AND_DENOM misconception -> nextAction: TRIGGER_TARGETED_INTERVENTION');
    console.log('Option B ("7/12") is CORRECT -> nextAction: PROCEED_TO_NEXT_QUESTION');
    console.log('---------------------\n');

    await mongoose.disconnect();
    console.log('Database disconnected.');
    process.exit(0);
  } catch (err) {
    console.error('Error during seeding:', err);
    process.exit(1);
  }
};

seedData();
