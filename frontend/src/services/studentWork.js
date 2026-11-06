export function buildStudentWork({ quizzes, activities, lessons }) {
  return [
    ...quizzes.filter(quiz => !quiz.submitted).map(quiz => ({ id: quiz.id, title: quiz.title, kind: 'quiz', href: `/student/quizzes/${quiz.id}` })),
    ...activities.filter(activity => !activity.locked && activity.attempts.length < activity.max_attempts).map(activity => ({ id: activity.id, title: activity.title, kind: 'activity', href: '/student/studio' })),
    ...lessons.map(lesson => ({ id: lesson.id, title: lesson.content.title, kind: 'lesson', href: '/student/inclusive' })),
  ];
}
