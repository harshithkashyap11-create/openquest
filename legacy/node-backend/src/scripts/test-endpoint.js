require('dotenv').config();
const mongoose = require('mongoose');
const Student = require('../models/Student');
const Assessment = require('../models/Assessment');
const Question = require('../models/Question');
const Attempt = require('../models/Attempt');
const app = require('../app');
const http = require('http');

async function runTest() {
  console.log('=== DAY 1 ENDPOINT TEST: POST /api/v1/assessments/submit ===');
  const mongoUri = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/classpulse';
  await mongoose.connect(mongoUri);

  // Find seeded records
  const student = await Student.findOne();
  const assessment = await Assessment.findOne();
  const question = await Question.findOne({ text: 'What is 1/3 + 1/4?' });

  if (!student || !assessment || !question) {
    console.error('Missing seed data! Please run "npm run seed" first.');
    process.exit(1);
  }

  // Start temporary test server
  const server = http.createServer(app);
  await new Promise((resolve) => server.listen(5001, resolve));
  console.log('Test HTTP server listening on port 5001\n');

  try {
    // TEST 1: Incorrect Answer triggering "ADD_NUM_AND_DENOM" misconception
    console.log('[TEST 1] Submitting Misconception Answer (Option A: 2/7 for 1/3 + 1/4)...');
    const res1 = await fetch('http://localhost:5001/api/v1/assessments/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        studentId: student._id.toString(),
        assessmentId: assessment._id.toString(),
        questionId: question._id.toString(),
        selectedOption: 'A',
        responseLatencyMs: 3400,
      }),
    });

    const data1 = await res1.json();
    console.log('HTTP Status:', res1.status);
    console.log('Response Body:', JSON.stringify(data1, null, 2));

    if (!data1.success || data1.data.isCorrect !== false) {
      throw new Error('Test 1 failed: Expected isCorrect to be false.');
    }
    if (data1.data.detectedMisconception?.code !== 'ADD_NUM_AND_DENOM') {
      throw new Error(`Test 1 failed: Expected misconception ADD_NUM_AND_DENOM, got ${data1.data.detectedMisconception?.code}`);
    }
    if (data1.data.nextAction !== 'TRIGGER_TARGETED_INTERVENTION') {
      throw new Error(`Test 1 failed: Expected nextAction TRIGGER_TARGETED_INTERVENTION, got ${data1.data.nextAction}`);
    }
    console.log('✅ TEST 1 PASSED: Misconception identified and targeted intervention triggered!\n');

    // TEST 2: Correct Answer (Option B: 7/12)
    console.log('[TEST 2] Submitting Correct Answer (Option B: 7/12)...');
    const res2 = await fetch('http://localhost:5001/api/v1/assessments/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        studentId: student._id.toString(),
        assessmentId: assessment._id.toString(),
        questionId: question._id.toString(),
        selectedOption: 'B',
        responseLatencyMs: 2100,
      }),
    });

    const data2 = await res2.json();
    console.log('HTTP Status:', res2.status);
    console.log('Response Body:', JSON.stringify(data2, null, 2));

    if (!data2.success || data2.data.isCorrect !== true) {
      throw new Error('Test 2 failed: Expected isCorrect to be true.');
    }
    if (data2.data.detectedMisconception !== null) {
      throw new Error('Test 2 failed: Expected detectedMisconception to be null for correct answer.');
    }
    if (data2.data.nextAction !== 'PROCEED_TO_NEXT_QUESTION') {
      throw new Error(`Test 2 failed: Expected nextAction PROCEED_TO_NEXT_QUESTION, got ${data2.data.nextAction}`);
    }
    console.log('✅ TEST 2 PASSED: Correct answer validated, nextAction PROCEED_TO_NEXT_QUESTION!\n');

    // TEST 3: Verify Attempt saved in MongoDB
    console.log('[TEST 3] Verifying Attempts saved in MongoDB...');
    const attempts = await Attempt.find({ student: student._id }).sort({ createdAt: -1 });
    console.log(`Found ${attempts.length} attempts in database for student ${student.name}.`);
    if (attempts.length < 2) {
      throw new Error('Test 3 failed: Attempts were not saved properly in MongoDB.');
    }
    console.log('✅ TEST 3 PASSED: Attempts verified in MongoDB!\n');

    // TEST 4: Input Validation Check (missing fields)
    console.log('[TEST 4] Testing Input Validation with missing assessmentId...');
    const res4 = await fetch('http://localhost:5001/api/v1/assessments/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        studentId: student._id.toString(),
        questionId: question._id.toString(),
        selectedOption: 'A',
      }),
    });
    const data4 = await res4.json();
    if (res4.status !== 400 || data4.success !== false) {
      throw new Error('Test 4 failed: Expected 400 validation error for missing field.');
    }
    console.log('✅ TEST 4 PASSED: Validation handles missing fields correctly!\n');

    console.log('🎉 ALL DAY 1 ENDPOINT TESTS PASSED SUCCESSFULLY! 🎉');
  } finally {
    server.close();
    await mongoose.disconnect();
  }
}

runTest().catch((err) => {
  console.error('Test execution failed:', err);
  process.exit(1);
});
