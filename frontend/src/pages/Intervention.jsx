import { useCallback, useState } from 'react';
import { Check, CircleAlert, UsersRound } from 'lucide-react';
import { Link, useLocation, useParams } from 'react-router-dom';
import MetricCard from '../components/MetricCard';
import Drawer from '../components/ui/Drawer';
import Tabs from '../components/ui/Tabs';
import Button from '../components/ui/Button';
import PageHeader from '../components/PageHeader';
import {
  EmptyState,
  ErrorState,
  LoadingState,
  RefreshNotice,
} from '../components/PageStates';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import { getErrorMessage } from '../services/api';
import {
  generateGroups,
  generateIntervention,
  getClassAssignments,
  getGroups,
  reviewGroup,
} from '../services/classpulseApi';
import { StudentActivity, StudentActivityList } from './StudentActivity';

function loadTeacherInterventions(classId) {
  return Promise.all([getGroups(classId), getClassAssignments(classId)]).then(
    ([groups, assignments]) => ({ groups, assignments }),
  );
}

export default function Intervention() {
  const { session } = useDemoSession();
  const { assignmentId } = useParams();
  if (session.role === 'student' && assignmentId) {
    return (
      <StudentActivity
        key={`${session.studentId}:${assignmentId}`}
        assignmentId={assignmentId}
        studentId={session.studentId}
      />
    );
  }
  if (session.role === 'student')
    return <StudentActivityList studentId={session.studentId} />;
  return (
    <TeacherInterventions key={session.classId} classId={session.classId} />
  );
}

function TeacherInterventions({ classId }) {
  const { t } = useI18n();
  const location = useLocation();
  const loadTeacherData = useCallback(
    () => loadTeacherInterventions(classId),
    [classId],
  );
  const { data, loading, error, refreshing, reload } = useAsyncData(
    loadTeacherData,
    classId,
  );
  const [working, setWorking] = useState('');
  const [message, setMessage] = useState('');
  const [actionError, setActionError] = useState('');
  const [generatedIntervention, setGeneratedIntervention] = useState(null);
  const [groupFilter, setGroupFilter] = useState('all');
  const [selectedGroupId, setSelectedGroupId] = useState(null);
  const [confirmGroupId, setConfirmGroupId] = useState(null);
  const showingAssignments = location.hash === '#assignments';

  async function perform(id, action, callback) {
    setWorking(id);
    setMessage('');
    setActionError('');
    try {
      const result = await callback();
      if (action === 'generate') {
        setGeneratedIntervention(result.intervention);
        setMessage(
          t('interventionGenerated', { count: result.assignments_created }),
        );
      } else {
        if (action === 'groups') setGroupFilter('all');
        setMessage(
          action === 'groups' ? t('groupsGenerated') : t('groupReviewed'),
        );
      }
      await reload();
    } catch (requestError) {
      setActionError(getErrorMessage(requestError, t('saveFailed')));
    } finally {
      setWorking('');
    }
  }

  if (loading) return <LoadingState />;
  if (error && !data) return <ErrorState error={error} onRetry={reload} />;

  const filteredGroups = data.groups.filter(
    (group) => (groupFilter === 'all' || group.review_status === groupFilter) &&
      (!new URLSearchParams(location.search).get('code') || group.misconception_code === new URLSearchParams(location.search).get('code')),
  );
  const selectedGroup = data.groups.find(
    (group) => group.id === selectedGroupId,
  );
  const confirmGroup = data.groups.find((group) => group.id === confirmGroupId);
  const approvedGroups = data.groups.filter((group) => group.teacher_approved);
  const activeAssignments = data.assignments.filter(
    (item) => item.status !== 'completed',
  ).length;
  const completedAssignments = data.assignments.length - activeAssignments;

  return (
    <div className="page-content interventions-page" id={showingAssignments ? 'assignments' : 'groups'}>
      <RefreshNotice error={error} refreshing={refreshing} onRetry={reload} />
      <PageHeader
        eyebrow={t('interventions')}
        title={t(showingAssignments ? 'interventions' : 'interventionManagement')}
        description={t(showingAssignments ? 'assignmentWorkflow' : 'groupsAndReview')}
        actions={
          showingAssignments ? <Link className="button button-secondary" to="/teacher/interventions#groups">{t('reviewLearningGroups')}</Link> :
          <button
            className="button button-primary"
            disabled={Boolean(working)}
            onClick={() =>
              perform('groups', 'groups', () => generateGroups(classId))
            }
          >
            <UsersRound size={17} aria-hidden="true" />
            {working === 'groups' ? t('loadingShort') : t('generateGroups')}
          </button>
        }
      />
      {message && (
        <p className="status-message" role="status">
          {message}
        </p>
      )}
      {actionError && (
        <p className="form-error" role="alert">
          {actionError}
        </p>
      )}

      <section className="metric-grid metric-grid-three">
        <MetricCard
          label={t('learningGroups')}
          value={data.groups.length}
          icon={UsersRound}
        />
        <MetricCard label={t('activeAssignments')} value={activeAssignments} />
        <MetricCard
          label={t('completedInterventions')}
          value={completedAssignments}
        />
      </section>

      {!showingAssignments && <section className="panel">
        {location.search && <Link to="/teacher/interventions#groups">{t('allGroups')}</Link>}
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t('groupActions')}</p>
            <h2>{t('groupsTitle')}</h2>
          </div>
        </div>
        <Tabs
          label={t('learningGroups')}
          value={groupFilter}
          onChange={setGroupFilter}
          items={[
            { value: 'all', label: t('allGroups') },
            { value: 'proposed', label: t('pendingReview') },
            { value: 'approved', label: t('approved') },
            { value: 'rejected', label: t('rejected') },
          ]}
        >
          {filteredGroups.length ? (
            <div className="group-list">
              {filteredGroups.map((group) => (
                <article className="group-card" key={group.id}>
                  <div className="group-card-main">
                    <div className="group-heading">
                      <span className="code-pill">
                        {group.misconception_code}
                      </span>
                      <span
                        className={`status-pill status-${group.review_status}`}
                      >
                        {t(group.review_status)}
                      </span>
                    </div>
                    <h3>{group.name}</h3>
                    <p>
                      {group.members.length} {t('members').toLowerCase()} ·{' '}
                      {group.topic}
                    </p>
                    <button
                      type="button"
                      className="text-link evidence-button"
                      onClick={() => setSelectedGroupId(group.id)}
                    >
                      {t('viewMembers')}{' '}
                      <UsersRound size={15} aria-hidden="true" />
                    </button>
                  </div>
                  <div className="group-actions">
                    {group.review_status === 'proposed' ? (
                      <>
                        <button
                          className="button button-secondary"
                          disabled={Boolean(working)}
                          onClick={() =>
                            perform(group.id, 'review', () =>
                              reviewGroup(group.id, 'rejected', group.revision),
                            )
                          }
                        >
                          {t('reject')}
                        </button>
                        <button
                          className="button button-primary"
                          disabled={Boolean(working)}
                          onClick={() =>
                            perform(group.id, 'review', () =>
                              reviewGroup(group.id, 'approved', group.revision),
                            )
                          }
                        >
                          <Check size={16} aria-hidden="true" /> {t('approve')}
                        </button>
                      </>
                    ) : group.teacher_approved ? (
                      <button
                        className="button button-primary"
                        disabled={Boolean(working)}
                        onClick={() => setConfirmGroupId(group.id)}
                      >
                        {working === group.id
                          ? t('loadingShort')
                          : t('generateAndAssign')}
                      </button>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <>
            <EmptyState
              title={t(data.groups.length ? 'noFilterResults' : 'emptyGroups')}
            />
            <div className="empty-workflow-actions">
              {data.groups.length ? <button className="button button-secondary" onClick={() => setGroupFilter('all')}>{t('allGroups')}</button> : <Link className="button button-secondary" to="/teacher/overview">{t('reviewStudentAnswers')}</Link>}
            </div>
            </>
          )}
        </Tabs>
        {approvedGroups.some((group) => group.misconception_code === 'M06') && (
          <p className="notice-inline">
            <CircleAlert size={16} /> {t('m06Notice')}
          </p>
        )}
      </section>}

      {!showingAssignments && generatedIntervention && (
        <section className="panel generated-intervention" aria-live="polite">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{t('generatedIntervention')}</p>
              <h2>{generatedIntervention.title}</h2>
            </div>
            {generatedIntervention.provider && (
              <span className="observed-badge">
                {generatedIntervention.provider.toLowerCase() === 'template'
                  ? t('templateFallback')
                  : generatedIntervention.provider.toLowerCase() ===
                      'openrouter'
                    ? t('personalizedWithOpenRouter')
                    : generatedIntervention.provider.toLowerCase() === 'gemini'
                      ? t('generatedWithGemini')
                      : t('personalizedWithProvider', {
                          provider: generatedIntervention.provider,
                        })}
              </span>
            )}
          </div>
          <p className="notice-inline">{t('generatedReviewNotice')}</p>
          <Link className="button button-secondary" to="/teacher/interventions#assignments">{t('viewAssignments')}</Link>
          <p>
            <strong>{t('learningObjective')}:</strong>{' '}
            {generatedIntervention.learning_objective}
          </p>
          <p className="learning-explanation">
            {generatedIntervention.explanation}
          </p>
          {generatedIntervention.instructions && (
            <p>
              <strong>{t('activityInstructions')}:</strong>{' '}
              {generatedIntervention.instructions}
            </p>
          )}
          {generatedIntervention.guided_example && (
            <div className="example-box">
              <h3>{t('guidedExample')}</h3>
              <p>{generatedIntervention.guided_example.question}</p>
              <p>{generatedIntervention.guided_example.steps}</p>
              <p>{generatedIntervention.guided_example.answer}</p>
            </div>
          )}
          {generatedIntervention.practice_questions?.length > 0 && (
            <div className="generated-practice">
              <h3>{t('practice')}</h3>
              <ol>
                {generatedIntervention.practice_questions.map((question, index) => (
                  <li key={question.question_index ?? index}>{question.question}</li>
                ))}
              </ol>
            </div>
          )}
          {generatedIntervention.generation_note && (
            <p className="muted-note">
              {generatedIntervention.generation_note}
            </p>
          )}
          {generatedIntervention.expected_answers?.length > 0 && (
            <details className="result-details teacher-answer-key">
              <summary>{t('teacherAnswerKey')}</summary>
              <ol>
                {generatedIntervention.expected_answers.map((answer, index) => (
                  <li key={`${index}:${answer}`}>{answer}</li>
                ))}
              </ol>
            </details>
          )}
        </section>
      )}

      {showingAssignments && <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t('assignmentTracking')}</p>
            <h2>{t('assignedActivities')}</h2>
          </div>
        </div>
        {data.assignments.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('learner')}</th>
                  <th>{t('activity')}</th>
                  <th>{t('status')}</th>
                  <th>{t('reassessmentScore')}</th>
                  <th>{t('sampleSize')}</th>
                  <th>{t('reassessmentResults')}</th>
                </tr>
              </thead>
              <tbody>
                {data.assignments.map((item) => (
                  <tr key={item.assignment_id}>
                    <td data-label={t('learner')}>{item.student_code}</td>
                    <td data-label={t('activity')}>
                      <span className="code-pill">
                        {item.misconception_code}
                      </span>{' '}
                      {item.title}
                    </td>
                    <td data-label={t('status')}>
                      <span className={`status-pill status-${item.status}`}>
                        {t(item.status)}
                      </span>
                    </td>
                    <td data-label={t('reassessmentScore')}>
                      {item.reassessment_accuracy_percentage == null
                        ? t('noReassessment')
                        : `${item.reassessment_accuracy_percentage}%`}
                    </td>
                    <td data-label={t('sampleSize')}>
                      {item.reassessment_total_questions ?? '—'}
                    </td>
                    <td data-label={t('reassessmentResults')}>
                      {item.reassessment_results.length ? (
                        <details className="result-details">
                          <summary>{t('viewAnswers')}</summary>
                          <div>
                            {item.reassessment_results.map((result) => (
                              <p key={result.question_id}>
                                <strong>
                                  {result.is_correct
                                    ? t('correct')
                                    : t('incorrect')}
                                  :
                                </strong>{' '}
                                {result.question_text} —{' '}
                                {result.answer || t('noAnswer')}
                              </p>
                            ))}
                          </div>
                        </details>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <><EmptyState title={t('emptyAssignments')} /><p className="empty-workflow-help">{t('assignmentWorkflow')}</p></>
        )}
      </section>}
      <Drawer
        open={Boolean(selectedGroup)}
        onClose={() => setSelectedGroupId(null)}
        title={t('groupMembers')}
      >
        {selectedGroup && (
          <div className="evidence-content">
            <h3>{selectedGroup.name}</h3>
            <span
              className={`status-pill status-${selectedGroup.review_status}`}
            >
              {t(selectedGroup.review_status)}
            </span>
            <p>
              {selectedGroup.members.length} {t('members')} ·{' '}
              {selectedGroup.topic}
            </p>
            <div className="member-codes">
              {selectedGroup.members.map((member) => (
                <span key={member.student_id}>{member.student_code}</span>
              ))}
            </div>
          </div>
        )}
      </Drawer>
      <Drawer
        open={Boolean(confirmGroup)}
        onClose={() => setConfirmGroupId(null)}
        title={t('confirmIntervention')}
        variant="modal"
      >
        {confirmGroup && (
          <>
            <p className="body-copy">
              {t('confirmInterventionDescription', {
                count: confirmGroup.members.length,
              })}
            </p>
            <div className="group-heading">
              <span className="code-pill">
                {confirmGroup.misconception_code}
              </span>
              <strong>{confirmGroup.name}</strong>
            </div>
            <div className="dialog-actions">
              <Button
                variant="secondary"
                onClick={() => setConfirmGroupId(null)}
              >
                {t('cancel')}
              </Button>
              <Button
                onClick={() => {
                  const group = confirmGroup;
                  setConfirmGroupId(null);
                  void perform(group.id, 'generate', () =>
                    generateIntervention(group.id),
                  );
                }}
              >
                {t('generateAndAssign')}
              </Button>
            </div>
          </>
        )}
      </Drawer>
    </div>
  );
}
