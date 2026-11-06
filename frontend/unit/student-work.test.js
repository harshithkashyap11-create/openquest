import test from 'node:test';
import assert from 'node:assert/strict';
import { buildStudentWork } from '../src/services/studentWork.js';

test('shows unsubmitted quizzes and available studio work, without completed or locked work', () => {
  const work = buildStudentWork({ quizzes: [{ id: 'q1', title: 'Quiz', submitted: false }, { id: 'q2', submitted: true }], activities: [{ id: 'a1', title: 'Activity', attempts: [], max_attempts: 2 }, { id: 'a2', attempts: [{}], max_attempts: 1 }, { id: 'a3', locked: 'Wait', attempts: [], max_attempts: 1 }], lessons: [] });
  assert.deepEqual(work.map(x => [x.title, x.href]), [['Quiz', '/student/quizzes/q1'], ['Activity', '/student/studio']]);
});

test('includes assigned accessible lessons without claiming their practice is complete', () => {
  const work = buildStudentWork({ quizzes: [], activities: [], lessons: [{ id: 'l1', content: { title: 'Read me' } }] });
  assert.deepEqual(work.map(x => [x.title, x.href, x.kind]), [['Read me', '/student/inclusive', 'lesson']]);
});
