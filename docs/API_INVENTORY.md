# Source-derived API inventory

Credential mode applies a global session/CSRF/role/class dependency.
Local demo mode is explicitly self-asserted. This inventory describes definitions;
runtime evidence is in FINAL_IMPLEMENTATION_REPORT.md.

| Method | Path | Request / response schema | Access |
|---|---|---|---|
| GET | `/api/auth/config` | JSON | public |
| POST | `/api/auth/demo-login` | DemoLoginInput, HTTPValidationError | public (demo login only in demo mode) |
| POST | `/api/auth/login` | LoginInput, HTTPValidationError | public |
| POST | `/api/auth/logout` | JSON | own student/class teacher |
| GET | `/api/auth/me` | JSON | own student/class teacher |
| GET | `/api/classes/{class_id}/assessment` | ClassAssessmentResponse, HTTPValidationError | own student/class teacher |
| GET | `/api/classes/{class_id}/assessment-summary` | AssessmentSummaryResponse, HTTPValidationError | authorized teacher/class |
| POST | `/api/classes/{class_id}/diagnose` | DiagnosisBatchResponse, HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/diagnoses` | DiagnosisItem, HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/diagnoses/summary` | DiagnosisSummary, HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/groups` | LearningGroupResponse, HTTPValidationError | authorized teacher/class |
| POST | `/api/classes/{class_id}/groups/generate` | GroupGenerationResponse, HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/intervention-assignments` | TeacherAssignmentReport, HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/learning-states` | HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/lessons` | HTTPValidationError | authorized teacher/class |
| POST | `/api/classes/{class_id}/lessons/generate` | GenerateLesson, HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/misconception-map` | MapSummary, HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/misconception-map/evidence` | EvidencePage, HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/progress` | ClassProgressResponse, HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/quizzes` | HTTPValidationError | authorized teacher/class |
| POST | `/api/classes/{class_id}/quizzes` | QuizInput, HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/studio/activities` | HTTPValidationError | authorized teacher/class |
| POST | `/api/classes/{class_id}/studio/activities` | ActivityInput, HTTPValidationError | authorized teacher/class |
| PATCH | `/api/classes/{class_id}/studio/activities/{activity_id}` | ActivityInput, HTTPValidationError | authorized teacher/class |
| POST | `/api/classes/{class_id}/studio/activities/{activity_id}/publish` | HTTPValidationError | authorized teacher/class |
| POST | `/api/classes/{class_id}/studio/generate` | GenerateInput, HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/studio/grades.csv` | HTTPValidationError | authorized teacher/class |
| POST | `/api/classes/{class_id}/studio/import-pdf` | PDFInput, HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/studio/integrations` | HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/studio/library` | HTTPValidationError | authorized teacher/class |
| POST | `/api/classes/{class_id}/studio/library` | StudioQuestion, HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/studio/qr-sessions` | HTTPValidationError | authorized teacher/class |
| POST | `/api/classes/{class_id}/studio/qr-sessions` | QRInput, HTTPValidationError | authorized teacher/class |
| POST | `/api/classes/{class_id}/studio/qr-sessions/{qr_id}/close` | HTTPValidationError | authorized teacher/class |
| POST | `/api/classes/{class_id}/studio/qr-sessions/{qr_id}/responses` | QRResponseInput, HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/studio/report` | HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/studio/roster` | HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/studio/sets` | HTTPValidationError | authorized teacher/class |
| POST | `/api/classes/{class_id}/studio/sets` | SetInput, HTTPValidationError | authorized teacher/class |
| GET | `/api/classes/{class_id}/studio/work/{work_id}/export.pdf` | HTTPValidationError | authorized teacher/class |
| PATCH | `/api/classes/{class_id}/studio/work/{work_id}/grade` | GradeInput, HTTPValidationError | authorized teacher/class |
| POST | `/api/classes/{class_id}/studio/work/{work_id}/passback` | HTTPValidationError | authorized teacher/class |
| POST | `/api/copilot/chat` | CopilotChatRequest, CopilotChatResponse, HTTPValidationError | authorized teacher/class |
| GET | `/api/copilot/classes/{class_id}/context` | ClassContextSummary, HTTPValidationError | authorized teacher/class |
| GET | `/api/copilot/taxonomy` | JSON | authorized teacher/class |
| GET | `/api/demo/classes` | DemoClassResponse | own student/class teacher |
| GET | `/api/demo/classes/{class_id}/students` | DemoStudentResponse, HTTPValidationError | authorized teacher/class |
| POST | `/api/demo/students/resolve` | DemoStudentResolutionRequest, DemoStudentResolutionResponse, HTTPValidationError | authorized teacher/class |
| GET | `/api/diagnoses/{diagnosis_id}/corrections` | HTTPValidationError | authorized teacher/class |
| POST | `/api/diagnoses/{diagnosis_id}/corrections` | CorrectionInput, HTTPValidationError | authorized teacher/class |
| POST | `/api/groups/{group_id}/interventions/generate` | InterventionGenerationResponse, HTTPValidationError | authorized teacher/class |
| PATCH | `/api/groups/{group_id}/review` | GroupReviewRequest, LearningGroupResponse, HTTPValidationError | authorized teacher/class |
| GET | `/api/intervention-assignments/{assignment_id}` | InterventionAssignmentResponse, HTTPValidationError | own student/class teacher |
| POST | `/api/intervention-assignments/{assignment_id}/complete` | InterventionCompletionResponse, HTTPValidationError | own student/class teacher |
| POST | `/api/intervention-assignments/{assignment_id}/reassessment` | ReassessmentResponse, HTTPValidationError | own student/class teacher |
| POST | `/api/intervention-assignments/{assignment_id}/submit` | PracticeSubmissionRequest, PracticeSubmissionResponse, HTTPValidationError | own student/class teacher |
| POST | `/api/intervention-assignments/{assignment_id}/sync-practice` | OfflinePractice, HTTPValidationError | own student/class teacher |
| GET | `/api/intervention-assignments/{assignment_id}/tutor` | HTTPValidationError | own student/class teacher |
| POST | `/api/intervention-assignments/{assignment_id}/tutor/hints` | HintRequest, HTTPValidationError | own student/class teacher |
| GET | `/api/lessons/{lesson_id}` | HTTPValidationError | own student/class teacher |
| PATCH | `/api/lessons/{lesson_id}` | EditLesson, HTTPValidationError | authorized teacher/class |
| POST | `/api/lessons/{lesson_id}/assign` | AssignLesson, HTTPValidationError | authorized teacher/class |
| POST | `/api/lessons/{lesson_id}/review` | ReviewLesson, HTTPValidationError | authorized teacher/class |
| POST | `/api/quizzes/import` | ImportInput, HTTPValidationError | authorized teacher/class |
| GET | `/api/quizzes/{quiz_id}` | HTTPValidationError | authorized teacher/class |
| PATCH | `/api/quizzes/{quiz_id}` | QuizInput, HTTPValidationError | authorized teacher/class |
| GET | `/api/quizzes/{quiz_id}/insights` | HTTPValidationError | authorized teacher/class |
| PATCH | `/api/quizzes/{quiz_id}/lesson` | LessonReviewInput, HTTPValidationError | authorized teacher/class |
| POST | `/api/quizzes/{quiz_id}/lesson` | HTTPValidationError | authorized teacher/class |
| POST | `/api/quizzes/{quiz_id}/publish` | HTTPValidationError | authorized teacher/class |
| PATCH | `/api/quizzes/{quiz_id}/reflections/{reflection_id}/review` | ReviewInput, HTTPValidationError | authorized teacher/class |
| GET | `/api/reassessments/{reassessment_id}` | ReassessmentSubmissionResponse, HTTPValidationError | own student/class teacher |
| POST | `/api/reassessments/{reassessment_id}/submit` | ReassessmentSubmissionRequest, ReassessmentSubmissionResponse, HTTPValidationError | own student/class teacher |
| POST | `/api/students/{student_id}/assessment-submissions` | AssessmentSubmissionRequest, AssessmentSubmissionResponse, HTTPValidationError | own student/class teacher |
| GET | `/api/students/{student_id}/interventions` | InterventionAssignmentResponse, HTTPValidationError | own student/class teacher |
| GET | `/api/students/{student_id}/journey` | JourneyPage, HTTPValidationError | own student/class teacher |
| GET | `/api/students/{student_id}/learning-state` | HTTPValidationError | own student/class teacher |
| GET | `/api/students/{student_id}/lessons` | HTTPValidationError | own student/class teacher |
| GET | `/api/students/{student_id}/progress` | StudentProgressResponse, HTTPValidationError | own student/class teacher |
| GET | `/api/students/{student_id}/quizzes` | HTTPValidationError | own student/class teacher |
| GET | `/api/students/{student_id}/quizzes/{quiz_id}` | HTTPValidationError | own student/class teacher |
| POST | `/api/students/{student_id}/quizzes/{quiz_id}/questions/{question_id}/reflect` | ReflectionInput, HTTPValidationError | own student/class teacher |
| POST | `/api/students/{student_id}/quizzes/{quiz_id}/questions/{question_id}/repair` | RepairAnswerInput, HTTPValidationError | own student/class teacher |
| POST | `/api/students/{student_id}/quizzes/{quiz_id}/submit` | SubmitQuizInput, HTTPValidationError | own student/class teacher |
| GET | `/api/students/{student_id}/studio/activities` | HTTPValidationError | own student/class teacher |
| GET | `/api/students/{student_id}/studio/activities/{activity_id}` | HTTPValidationError | own student/class teacher |
| POST | `/api/students/{student_id}/studio/activities/{activity_id}/submit` | WorkInput, HTTPValidationError | own student/class teacher |
| GET | `/api/students/{student_id}/studio/sets` | HTTPValidationError | own student/class teacher |
| GET | `/api/students/{student_id}/studio/work/{work_id}/export.pdf` | HTTPValidationError | own student/class teacher |
| POST | `/api/students/{student_id}/studio/work/{work_id}/feedback` | FeedbackInput, HTTPValidationError | own student/class teacher |
| GET | `/api/system-status` | JSON | own student/class teacher |
| POST | `/api/v1/copilot/chat` | CopilotChatRequest, CopilotChatResponse, HTTPValidationError | authorized teacher/class |
| GET | `/api/v1/copilot/classes/{class_id}/context` | ClassContextSummary, HTTPValidationError | authorized teacher/class |
| GET | `/api/v1/copilot/taxonomy` | JSON | authorized teacher/class |
| GET | `/health` | JSON | public |
| GET | `/health/ai` | JSON | public |
| GET | `/health/ready` | JSON | public |
