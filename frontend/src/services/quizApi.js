import api, { getStudentConfig } from './api';

const teacherConfig = (classId) => ({
  headers: { 'X-Demo-Role': 'teacher', 'X-Class-ID': classId },
});
export const listQuizzes = async (classId) =>
  (await api.get(`/classes/${classId}/quizzes`, teacherConfig(classId))).data;
export const saveQuiz = async (classId, quizId, payload) =>
  (
    await (quizId
      ? api.patch(`/quizzes/${quizId}`, payload, teacherConfig(classId))
      : api.post(
          `/classes/${classId}/quizzes`,
          payload,
          teacherConfig(classId),
        ))
  ).data;
export const publishQuiz = async (classId, quizId) =>
  (await api.post(`/quizzes/${quizId}/publish`, {}, teacherConfig(classId)))
    .data;
export const importQuiz = async (classId, content) =>
  (await api.post('/quizzes/import', { content }, teacherConfig(classId))).data;
export const quizInsights = async (classId, quizId, signal) =>
  (
    await api.get(`/quizzes/${quizId}/insights`, {
      ...teacherConfig(classId),
      signal,
    })
  ).data;
export const reviewReflection = async (
  classId,
  quizId,
  reflectionId,
  flagged,
) =>
  (
    await api.patch(
      `/quizzes/${quizId}/reflections/${reflectionId}/review`,
      { flagged },
      teacherConfig(classId),
    )
  ).data;
export const suggestLesson = async (classId, quizId) =>
  (
    await api.post(
      `/quizzes/${quizId}/lesson`,
      {},
      { ...teacherConfig(classId), timeout: 60000 },
    )
  ).data;
export const reviewLesson = async (classId, quizId, payload) =>
  (
    await api.patch(
      `/quizzes/${quizId}/lesson`,
      payload,
      teacherConfig(classId),
    )
  ).data;
export const studentQuizzes = async (studentId) =>
  (await api.get(`/students/${studentId}/quizzes`, getStudentConfig(studentId)))
    .data;
export const studentQuiz = async (studentId, quizId) =>
  (
    await api.get(
      `/students/${studentId}/quizzes/${quizId}`,
      getStudentConfig(studentId),
    )
  ).data;
export const submitQuiz = async (studentId, quizId, answers) =>
  (
    await api.post(
      `/students/${studentId}/quizzes/${quizId}/submit`,
      { answers },
      getStudentConfig(studentId),
    )
  ).data;
export const reflectOnQuestion = async (
  studentId,
  quizId,
  questionId,
  message,
  language,
) =>
  (
    await api.post(
      `/students/${studentId}/quizzes/${quizId}/questions/${questionId}/reflect`,
      { message, language },
      { ...getStudentConfig(studentId), timeout: 60000 },
    )
  ).data;
export const answerRepair = async (
  studentId,
  quizId,
  questionId,
  selectedOption,
) =>
  (
    await api.post(
      `/students/${studentId}/quizzes/${quizId}/questions/${questionId}/repair`,
      { selected_option: selectedOption },
      getStudentConfig(studentId),
    )
  ).data;
