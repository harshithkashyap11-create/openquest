import api, { getStudentConfig } from './api';

export async function listDemoClasses() {
  return (await api.get('/demo/classes')).data;
}

export async function listDemoStudents(classId) {
  return (await api.get(`/demo/classes/${classId}/students`)).data;
}

export async function resolveStudent(classId, studentCode) {
  return (
    await api.post('/demo/students/resolve', {
      class_id: classId,
      student_code: studentCode,
    })
  ).data;
}

export async function getClassAssessment(classId, studentId) {
  return (
    await api.get(`/classes/${classId}/assessment`, getStudentConfig(studentId))
  ).data;
}

export async function submitAssessment(studentId, answers) {
  return (
    await api.post(
      `/students/${studentId}/assessment-submissions`,
      { answers },
      getStudentConfig(studentId),
    )
  ).data;
}

export async function getAssessmentSummary(classId) {
  return (await api.get(`/classes/${classId}/assessment-summary`)).data;
}

export async function getDiagnosisSummary(classId) {
  return (await api.get(`/classes/${classId}/diagnoses/summary`)).data;
}

export async function getClassDiagnoses(classId) {
  const pageSize = 100;
  const collected = [];
  let offset = 0;
  while (true) {
    const page = (
      await api.get(`/classes/${classId}/diagnoses`, {
        params: { limit: pageSize, offset },
      })
    ).data;
    collected.push(...page);
    if (page.length < pageSize) return collected;
    offset += pageSize;
  }
}

export async function runDiagnosis(classId) {
  return (await api.post(`/classes/${classId}/diagnose`)).data;
}

export async function getGroups(classId) {
  return (await api.get(`/classes/${classId}/groups`)).data;
}

export async function generateGroups(classId) {
  return (await api.post(`/classes/${classId}/groups/generate`)).data;
}

export async function reviewGroup(groupId, status) {
  return (await api.patch(`/groups/${groupId}/review`, { status })).data;
}

export async function generateIntervention(groupId) {
  return (
    await api.post(`/groups/${groupId}/interventions/generate`, null, {
      timeout: 60000,
    })
  ).data;
}

export async function getClassProgress(classId) {
  return (await api.get(`/classes/${classId}/progress`)).data;
}

export async function getClassAssignments(classId) {
  return (await api.get(`/classes/${classId}/intervention-assignments`)).data;
}

export async function getStudentInterventions(studentId) {
  return (
    await api.get(
      `/students/${studentId}/interventions`,
      getStudentConfig(studentId),
    )
  ).data;
}

export async function getStudentAssignment(assignmentId, studentId) {
  return (
    await api.get(
      `/intervention-assignments/${assignmentId}`,
      getStudentConfig(studentId),
    )
  ).data;
}

export async function submitPractice(assignmentId, studentId, answers) {
  return (
    await api.post(
      `/intervention-assignments/${assignmentId}/submit`,
      { answers },
      getStudentConfig(studentId),
    )
  ).data;
}

export async function completeIntervention(assignmentId, studentId) {
  return (
    await api.post(
      `/intervention-assignments/${assignmentId}/complete`,
      {},
      getStudentConfig(studentId),
    )
  ).data;
}

export async function getStudentReassessment(assignmentId, studentId) {
  return (
    await api.post(
      `/intervention-assignments/${assignmentId}/reassessment`,
      {},
      getStudentConfig(studentId),
    )
  ).data;
}

export async function getReassessment(reassessmentId, studentId) {
  return (
    await api.get(
      `/reassessments/${reassessmentId}`,
      getStudentConfig(studentId),
    )
  ).data;
}

export async function submitReassessment(reassessmentId, studentId, answers) {
  return (
    await api.post(
      `/reassessments/${reassessmentId}/submit`,
      { answers },
      getStudentConfig(studentId),
    )
  ).data;
}

export async function getStudentProgress(studentId) {
  return (
    await api.get(
      `/students/${studentId}/progress`,
      getStudentConfig(studentId),
    )
  ).data;
}

export async function chatWithCopilot({
  message,
  classId = null,
  subject = null,
  topic = null,
  history = [],
  action = null,
}) {
  return (
    await api.post('/copilot/chat', {
      message,
      class_id: classId,
      subject,
      topic,
      history,
      action,
    }, { timeout: 60000 })
  ).data;
}

export async function getCopilotClassContext(classId) {
  return (await api.get(`/copilot/classes/${classId}/context`)).data;
}

export async function getCopilotTaxonomy() {
  return (await api.get('/copilot/taxonomy')).data;
}
