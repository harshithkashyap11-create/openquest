from typing import Any
import json
import re

from app.schemas.copilot import (
    ChatMessage,
    ClassContextSummary,
    CopilotChatRequest,
    CopilotChatResponse,
    DraftActivity,
    DraftContentItem,
    DraftEducationalContent,
    DraftLessonPlan,
    LessonPhase,
)
from app.services.diagnosis_provider import (
    ProviderConfigurationError,
    ProviderError,
    ProviderRateLimited,
)
from app.services.openrouter_client import OpenRouterChatClient
from app.subject_taxonomy import SUBJECT_TAXONOMY, get_taxonomy


def normalize_subject_topic(
    subject: str | None, topic: str | None
) -> tuple[str, str]:
    """Normalize subject and topic aliases to match official SUBJECT_TAXONOMY keys."""
    sub_raw = (subject or "").strip().casefold()
    top_raw = (topic or "").strip().casefold()
    display_topic = (topic or "").strip()

    def has_any(*terms: str) -> bool:
        return any(term in top_raw for term in terms)

    if sub_raw:
        if "math" in sub_raw:
            if not top_raw or has_any("fraction", "numerator", "denominator"):
                return ("Mathematics", "Fractions")
            if has_any("algebra", "equation", "variable"):
                return ("Mathematics", "Basic algebra")
        elif "science" in sub_raw:
            if not top_raw or has_any("force", "motion", "inertia", "speed", "newton"):
                return ("Science", "Force and motion")
            if has_any("electric", "circuit", "voltage", "current"):
                return ("Science", "Basic electricity")
        elif "english" in sub_raw:
            if not top_raw or has_any("grammar", "tense", "punctuation", "pronoun"):
                return ("English", "Grammar")
            if has_any("subject-verb", "agreement", "singular", "plural"):
                return ("English", "Subject-verb agreement")
        return ("Unsupported", display_topic or (subject or "Unsupported").strip())

    # With no subject, infer it only from a recognized topic alias.
    if has_any("fraction", "numerator", "denominator"):
        return ("Mathematics", "Fractions")
    if has_any("algebra", "equation", "variable"):
        return ("Mathematics", "Basic algebra")
    if has_any("force", "motion", "inertia", "speed", "newton"):
        return ("Science", "Force and motion")
    if has_any("electric", "circuit", "voltage", "current"):
        return ("Science", "Basic electricity")
    if has_any("subject-verb", "agreement", "singular", "plural"):
        return ("English", "Subject-verb agreement")
    if has_any("grammar", "tense", "punctuation", "pronoun"):
        return ("English", "Grammar")

    return ("Unsupported", display_topic or "Unsupported")


def detect_intent(message: str, action: str | None) -> str:
    if action:
        act = action.lower()
        if any(k in act for k in ["summarize", "performance", "struggling", "misconception", "compare"]):
            return "classroom_intelligence"
        if any(k in act for k in ["strategy", "activity", "lesson_plan", "explain"]):
            return "teaching_assistance"
        if any(k in act for k in ["worksheet", "question", "quiz", "remedial", "exercise"]):
            return "content_generation"

    msg = message.lower()
    if any(k in msg for k in ["analyze my class", "quiz results", "quiz report", "quiz performance"]):
        return "classroom_intelligence"
    if any(k in msg for k in ["worksheet", "quiz", "practice question", "questions", "remedial", "exercise", "test"]):
        return "content_generation"
    if any(k in msg for k in ["how is the class", "summary", "summarize", "struggling", "misconception", "performance", "accuracy", "progress", "attention", "reassessment", "compare"]):
        return "classroom_intelligence"
    if any(k in msg for k in ["lesson plan", "plan a lesson", "strategy", "teach", "activity", "explain", "beginner", "intermediate", "advanced", "differentiate"]):
        return "teaching_assistance"
    return "conversational"


class MockCopilotProvider:
    name = "mock"
    model_version = "mock-copilot-v1"

    def generate(
        self,
        request: CopilotChatRequest,
        context_summary: ClassContextSummary | None = None,
        grounding_text: str = "",
    ) -> CopilotChatResponse:
        subject, topic = self._resolve_subject_topic(request, context_summary)
        intent = detect_intent(request.message, request.action)

        if subject == "Unsupported":
            supported = ", ".join(
                f"{s}: {t}" for s, t in SUBJECT_TAXONOMY
            )
            return CopilotChatResponse(
                reply=(
                    f"I can’t generate subject-specific guidance for {topic!r} yet. "
                    f"Supported topics are {supported}."
                ),
                intent=intent,
                subject=subject,
                topic=topic,
                class_id=context_summary.class_id if context_summary else None,
                class_context_summary=context_summary,
                suggested_followups=["Choose one of the supported subjects and topics."],
                provider=self.name,
                model_version=self.model_version,
            )

        if intent == "classroom_intelligence":
            return self._handle_classroom_intelligence(request, context_summary, subject, topic)
        elif intent == "teaching_assistance":
            return self._handle_teaching_assistance(request, context_summary, subject, topic)
        elif intent == "content_generation":
            return self._handle_content_generation(request, context_summary, subject, topic)
        else:
            return self._handle_conversational(request, context_summary, subject, topic)

    def _resolve_subject_topic(
        self, request: CopilotChatRequest, context_summary: ClassContextSummary | None
    ) -> tuple[str, str]:
        # Check explicit request override first
        if request.subject or request.topic:
            return normalize_subject_topic(request.subject, request.topic)
        # Check class context
        if context_summary is not None:
            return normalize_subject_topic(context_summary.subject, context_summary.topic)
        # Default
        return ("Mathematics", "Fractions")

    def _handle_classroom_intelligence(
        self,
        request: CopilotChatRequest,
        summary: ClassContextSummary | None,
        subject: str,
        topic: str,
    ) -> CopilotChatResponse:
        if summary is None:
            reply = (
                f"You have not selected a specific classroom yet. To view performance analytics, "
                f"misconception clusters, and student progress, please select a class from your dashboard, "
                f"or ask me general pedagogical and curriculum questions about {subject}: {topic}."
            )
            return CopilotChatResponse(
                reply=reply,
                intent="classroom_intelligence",
                subject=subject,
                topic=topic,
                class_id=None,
                suggested_followups=[
                    f"Create a 45-minute lesson plan for {topic}",
                    f"Generate a diagnostic worksheet for {topic}",
                    f"How do I explain {topic} to beginners?",
                ],
                provider=self.name,
                model_version=self.model_version,
            )

        # Build grounded summary using actual database records
        lines = [
            f"### Classroom Intelligence Summary for **{summary.class_name}** ({subject}: {topic})",
            "",
            f"- **Enrolled Students:** {summary.total_students}",
            f"- **Submissions:** {summary.submitted_students} of {summary.total_students} students have submitted assessments ({summary.diagnosed_answers} diagnosed, {summary.pending_diagnoses} pending).",
        ]

        if summary.baseline_accuracy is not None:
            lines.append(
                f"- **Initial Baseline Accuracy:** {summary.baseline_accuracy:.1f}% across {summary.baseline_sample_size} recorded responses."
            )
        else:
            lines.append("- **Initial Baseline Accuracy:** Pending initial assessment submissions.")

        if summary.reassessment_accuracy is not None:
            delta_note = f" (net shift of {'+' if summary.accuracy_delta >= 0 else ''}{summary.accuracy_delta:.1f} percentage points)" if summary.accuracy_delta is not None else ""
            lines.append(
                f"- **Post-Intervention Reassessment Accuracy:** {summary.reassessment_accuracy:.1f}% across {summary.reassessment_sample_size} completed reassessments{delta_note}."
            )
        else:
            lines.append("- **Reassessment Outcomes:** No students have completed reassessments yet.")

        if summary.top_misconceptions:
            lines.append("\n#### Top Observed Misconceptions:")
            for m in summary.top_misconceptions:
                ev_str = f" *Example student quote:* \"{m.sample_evidence[0]}\"" if m.sample_evidence else ""
                lines.append(
                    f"- **{m.code} — {m.category}:** Affecting **{m.student_count}** student(s) (`{', '.join(m.affected_students)}`).\n"
                    f"  {m.description}{ev_str}"
                )
        else:
            lines.append("\n#### Misconceptions: No diagnosed misconceptions recorded.")

        if summary.students_needing_attention:
            lines.append(
                f"\n#### Students Requiring Attention:\n"
                f"The following student(s) need immediate intervention or follow-up diagnostics: "
                f"`{', '.join(summary.students_needing_attention)}`."
            )

        lines.append(
            f"\n#### Interventions & Groups:\n"
            f"- **{summary.groups_count}** learning group(s) proposed ({summary.approved_groups_count} approved).\n"
            f"- **{summary.assigned_interventions_count}** student intervention assignment(s) created."
        )

        if summary.quiz_reports:
            lines.append("\n#### Published quiz checkpoints (separate from baseline assessments):")
            for quiz in summary.quiz_reports:
                lines.append(f"- **{quiz.title}:** {quiz.submitted_students} submitted students.")
                for question in quiz.questions:
                    lines.append(f"  - Question {question.ordinal}: {question.wrong_answers} missed answers; "
                                 f"{question.reflected_students} shared reasoning, {question.uncertain_students} uncertain. "
                                 f"Tentative error themes: {', '.join(str(t['error_type']) + ': ' + str(t['students']) for t in question.themes) or 'none yet'}.")

        if summary.studio_report.get('saved_attempts'):
            studio = summary.studio_report
            lines.append(f"\n#### Classroom Studio: {studio['submitted_students']} students, {studio['saved_attempts']} saved attempts")
            for row in studio['standards']:
                lines.append(f"- {row['standard']}: {row['earned']}/{row['possible']} observed points; {row['pending']} pending reviews.")
            lines.append('Review the original work before deciding on support. These scores do not establish mastery.')
        reply = "\n".join(lines)
        return CopilotChatResponse(
            reply=reply,
            intent="classroom_intelligence",
            subject=subject,
            topic=topic,
            class_id=summary.class_id,
            class_context_summary=summary,
            suggested_followups=[
                f"Generate targeted remedial exercises for {summary.top_misconceptions[0].code}" if summary.top_misconceptions else f"Generate practice questions for {topic}",
                f"Recommend teaching strategies for {topic}",
                f"Create a differentiated lesson plan for {summary.class_name}",
            ],
            provider=self.name,
            model_version=self.model_version,
        )

    def _handle_teaching_assistance(
        self,
        request: CopilotChatRequest,
        summary: ClassContextSummary | None,
        subject: str,
        topic: str,
    ) -> CopilotChatResponse:
        is_lesson_plan = "lesson plan" in request.message.lower() or (request.action and "lesson_plan" in request.action)
        is_levels = any(k in request.message.lower() for k in ["beginner", "intermediate", "advanced", "level", "explain concept"])

        if is_lesson_plan:
            plan = self._build_mock_lesson_plan(subject, topic)
            reply = (
                f"### Differentiated Lesson Plan: {plan.title}\n\n"
                f"**Subject:** {subject} | **Topic:** {topic} | **Target Duration:** {plan.duration_minutes} minutes\n\n"
                f"#### Learning Objectives:\n" + "\n".join(f"- {obj}" for obj in plan.objectives) + "\n\n"
                f"#### Materials Needed:\n" + "\n".join(f"- {mat}" for mat in plan.materials_needed) + "\n\n"
                f"#### Lesson Phases:\n" + "\n".join(
                    f"1. **{phase.phase_name} ({phase.duration_minutes} min):**\n"
                    f"   - *Teacher:* {phase.teacher_action}\n"
                    f"   - *Students:* {phase.student_action}"
                    for phase in plan.phases
                ) + "\n\n"
                f"#### Differentiated Instruction:\n"
                f"- **Beginner:** {plan.differentiation.get('beginner', '')}\n"
                f"- **Intermediate:** {plan.differentiation.get('intermediate', '')}\n"
                f"- **Advanced:** {plan.differentiation.get('advanced', '')}\n\n"
                f"#### Formative Assessment Check:\n{plan.assessment_check}"
            )
            draft = DraftEducationalContent(
                content_type="lesson_plan",
                title=plan.title,
                target_audience="differentiated",
                lesson_plan=plan,
                is_draft=True,
            )
        elif is_levels:
            reply = self._build_levels_explanation(subject, topic)
            draft = None
        else:
            activity = self._build_mock_activity(subject, topic)
            reply = (
                f"### Recommended Teaching Strategy & Activity: {activity.activity_name}\n\n"
                f"**Subject:** {subject} | **Topic:** {topic}\n\n"
                f"#### Targeted Strategy:\n"
                f"Use active inquiry and visual/concrete anchors to help students confront and resolve intuitive misconceptions.\n\n"
                f"#### Classroom Activity Details:\n"
                f"- **Grouping:** {activity.group_size}\n"
                f"- **Materials:** {', '.join(activity.materials_needed)}\n"
                f"- **Instructions:** {activity.instructions}\n"
                f"- **Expected Takeaway:** {activity.expected_takeaway}"
            )
            draft = DraftEducationalContent(
                content_type="classroom_activity",
                title=activity.activity_name,
                target_audience="all",
                activity=activity,
                is_draft=True,
            )

        return CopilotChatResponse(
            reply=reply,
            intent="teaching_assistance",
            subject=subject,
            topic=topic,
            class_id=summary.class_id if summary else None,
            class_context_summary=summary,
            draft_content=draft,
            suggested_followups=[
                f"Generate a worksheet aligned with this {topic} activity",
                f"Explain {topic} at beginner, intermediate, and advanced levels",
                f"How should I address struggling students in this topic?",
            ],
            provider=self.name,
            model_version=self.model_version,
        )

    def _handle_content_generation(
        self,
        request: CopilotChatRequest,
        summary: ClassContextSummary | None,
        subject: str,
        topic: str,
    ) -> CopilotChatResponse:
        content_type = "worksheet"
        msg = request.message.lower()
        if "quiz" in msg:
            content_type = "quiz"
        elif "remedial" in msg:
            content_type = "remedial_exercise"
        elif "practice" in msg:
            content_type = "practice_questions"

        target_code = None
        # Check if a specific misconception code was mentioned
        match = re.search(r"\b(M0[1-6]|ALG0[1-3]|FM0[1-3]|EL0[1-3]|GR0[1-3]|SV0[1-3])\b", request.message, re.IGNORECASE)
        if match:
            target_code = match.group(1).upper()
        elif summary and summary.top_misconceptions:
            target_code = summary.top_misconceptions[0].code

        items = self._build_mock_content_items(subject, topic, target_code)
        title = f"Targeted {topic} {content_type.replace('_', ' ').title()}"
        if target_code:
            title += f" (Focus: {target_code})"

        reply_lines = [
            f"### {title} [Draft]",
            f"**Subject:** {subject} | **Topic:** {topic}" + (f" | **Focus Misconception:** `{target_code}`" if target_code else ""),
            "",
            "Here is the generated educational draft content. You can review, approve, or export this material for your students:",
            "",
        ]

        for i, item in enumerate(items, 1):
            reply_lines.append(f"**Question {i}:** {item.question}")
            if item.options:
                for opt in item.options:
                    reply_lines.append(f"  - {opt}")
            reply_lines.append(f"  *Answer:* `{item.correct_answer}`")
            reply_lines.append(f"  *Explanation:* {item.explanation}")
            if item.hints:
                reply_lines.append(f"  *Hint:* {item.hints[0]}")
            reply_lines.append("")

        draft = DraftEducationalContent(
            content_type=content_type,
            title=title,
            target_audience="classroom",
            misconception_code=target_code,
            items=items,
            is_draft=True,
        )

        return CopilotChatResponse(
            reply="\n".join(reply_lines),
            intent="content_generation",
            subject=subject,
            topic=topic,
            class_id=summary.class_id if summary else None,
            class_context_summary=summary,
            draft_content=draft,
            suggested_followups=[
                f"Generate a follow-up quiz for these questions",
                f"How can I differentiate these questions for beginners?",
                f"Create a 45-minute lesson plan for {topic}",
            ],
            provider=self.name,
            model_version=self.model_version,
        )

    def _handle_conversational(
        self,
        request: CopilotChatRequest,
        summary: ClassContextSummary | None,
        subject: str,
        topic: str,
    ) -> CopilotChatResponse:
        reply = (
            f"I am your AI Teacher Copilot for **{subject}: {topic}**. "
            f"I can help you review your classroom's diagnostic progress, unpack misconceptions with evidence, "
            f"differentiate your instruction across beginner to advanced levels, or generate customized worksheets, "
            f"lesson plans, and remedial exercises. What would you like to explore?"
        )
        return CopilotChatResponse(
            reply=reply,
            intent="conversational",
            subject=subject,
            topic=topic,
            class_id=summary.class_id if summary else None,
            class_context_summary=summary,
            suggested_followups=[
                f"Summarize my class's performance in {topic}" if summary else f"How do I explain {topic} to beginners?",
                f"Generate a targeted worksheet for {topic}",
                f"Plan a 45-minute lesson for {topic}",
            ],
            provider=self.name,
            model_version=self.model_version,
        )

    def _build_levels_explanation(self, subject: str, topic: str) -> str:
        if topic == "Fractions":
            return (
                "### Concept Explanation: Fractions across Three Pedagogical Levels\n\n"
                "#### 1. Beginner Level (Concrete & Visual)\n"
                "- **Concept:** A fraction represents equal slices of one whole.\n"
                "- **Analogy:** Imagine a rectangular chocolate bar divided into 4 equal blocks. If you eat 1 block, you have eaten 1 out of 4, written as 1/4.\n"
                "- **Key Rule:** The bottom number (denominator) tells you how many equal parts make the whole; the top number (numerator) counts how many parts you have.\n\n"
                "#### 2. Intermediate Level (Formal Rules & Equivalence)\n"
                "- **Concept:** Fractions represent rational numbers on a continuous number line.\n"
                "- **Procedure:** To add or compare fractions with different denominators, you must rename them using common equal-sized parts (common denominators).\n"
                "- **Common Pitfall:** Never add denominators (e.g., 1/2 + 1/3 is NOT 2/5; it is 3/6 + 2/6 = 5/6).\n\n"
                "#### 3. Advanced Level (Conceptual Synthesis & Proportions)\n"
                "- **Concept:** Fractions as division operators, multiplicative inverses, and scale factors.\n"
                "- **Insight:** Dividing by a fraction a/b is equivalent to multiplying by its reciprocal b/a because you are finding how many groups of size a/b fit into the dividend."
            )
        elif topic == "Basic algebra":
            return (
                "### Concept Explanation: Basic Algebra across Three Pedagogical Levels\n\n"
                "#### 1. Beginner Level (Intuitive & Balance)\n"
                "- **Concept:** The equals sign '=' is a balanced scale.\n"
                "- **Analogy:** If you have a mystery box and 3 apples balancing 7 apples on the other side, removing 3 apples from both sides reveals what is inside the mystery box.\n\n"
                "#### 2. Intermediate Level (Inverse Operations)\n"
                "- **Concept:** Isolating variables using inverse arithmetic operations.\n"
                "- **Procedure:** Whatever operation is performed on one side of the equation must be applied to the other side to maintain equality (e.g., in 2x + 4 = 12, subtract 4 from both sides, then divide by 2).\n\n"
                "#### 3. Advanced Level (Structure & Generalization)\n"
                "- **Concept:** Variables as dynamic parameters representing continuous functions and algebraic identities."
            )
        elif topic == "Force and motion":
            return (
                "### Concept Explanation: Force & Motion across Three Pedagogical Levels\n\n"
                "#### 1. Beginner Level (Sensory & Everyday Observation)\n"
                "- **Concept:** Forces are pushes and pulls that change how objects move.\n"
                "- **Key Anchor:** When a rolling ball stops on the carpet, it isn't 'running out of motion'—friction is pulling against it.\n\n"
                "#### 2. Intermediate Level (Newton's Laws & Inertia)\n"
                "- **Concept:** Newton's First Law (Inertia). An object maintains constant velocity unless acted upon by a net external force.\n"
                "- **Key Formula:** Net Force = mass × acceleration (F = ma).\n\n"
                "#### 3. Advanced Level (Vector Dynamics & Equilibrium)\n"
                "- **Concept:** Net force as the vector sum of all collinear and perpendicular forces."
            )
        elif topic == "Basic electricity":
            return (
                "### Concept Explanation: Basic Electricity across Three Pedagogical Levels\n\n"
                "#### 1. Beginner Level (Continuous Loops)\n"
                "- **Concept:** Electricity needs an unbroken closed path to flow, like a continuous circular race track.\n\n"
                "#### 2. Intermediate Level (Current, Voltage & Resistance)\n"
                "- **Concept:** Current is the rate of charge flow; voltage is the electrical potential driving the flow; resistance opposes it (Ohm's Law: V = IR).\n\n"
                "#### 3. Advanced Level (Conservation of Energy & Charge)\n"
                "- **Concept:** Kirchhoff's laws: Charge does not get used up in a circuit loop; energy is transformed into light, heat, or mechanical work."
            )
        elif topic == "Subject-verb agreement":
            return (
                "### Concept Explanation: Subject-Verb Agreement across Three Pedagogical Levels\n\n"
                "#### 1. Beginner Level (Singular vs Plural)\n"
                "- **Concept:** A singular subject takes a singular verb (The dog barks); a plural subject takes a plural verb (The dogs bark).\n\n"
                "#### 2. Intermediate Level (Intervening Prepositional Phrases)\n"
                "- **Concept:** Ignore prepositional phrases that sit between the subject and the verb (e.g., 'The box of chocolates IS heavy', not 'are heavy').\n\n"
                "#### 3. Advanced Level (Compound & Indefinite Pronoun Agreement)\n"
                "- **Concept:** Collective nouns, indefinite pronouns ('each', 'everyone' take singular verbs), and compound subjects joined by 'neither/nor'."
            )
        else: # Grammar
            return (
                "### Concept Explanation: Grammar & Tenses across Three Pedagogical Levels\n\n"
                "#### 1. Beginner Level:\nUnderstanding past, present, and future time words.\n\n"
                "#### 2. Intermediate Level:\nConsistent verb aspect (simple, continuous, perfect) across clauses.\n\n"
                "#### 3. Advanced Level:\nSubjunctive moods, conditional clauses, and stylistic voice."
            )

    def _build_mock_lesson_plan(self, subject: str, topic: str) -> DraftLessonPlan:
        return DraftLessonPlan(
            title=f"45-Minute Concept Mastery: {topic}",
            subject=subject,
            topic=topic,
            duration_minutes=45,
            objectives=[
                f"Identify and resolve core misconceptions in {topic}",
                f"Apply verified step-by-step reasoning to solve standard problems",
                f"Articulate mathematical/scientific reasoning verbally and in writing",
            ],
            materials_needed=[
                "Mini whiteboards and markers",
                "Printed diagnostic anchor chart",
                "Formative exit ticket cards",
            ],
            phases=[
                LessonPhase(
                    phase_name="Engagement & Misconception Hook",
                    duration_minutes=10,
                    teacher_action=f"Present a common non-example or classic student misconception in {topic} on the board.",
                    student_action="Identify why the example reasoning is flawed and propose a correction.",
                ),
                LessonPhase(
                    phase_name="Explicit Guided Modeling",
                    duration_minutes=15,
                    teacher_action="Demonstrate the correct target procedure with think-aloud modeling and visual anchors.",
                    student_action="Follow along with whiteboard practice, annotating key reasoning steps.",
                ),
                LessonPhase(
                    phase_name="Differentiated Partner Practice",
                    duration_minutes=15,
                    teacher_action="Circulate and provide targeted scaffolded prompts to struggling student clusters.",
                    student_action="Collaborate in pairs on tiered task cards with peer explanation checks.",
                ),
                LessonPhase(
                    phase_name="Synthesis & Exit Ticket Check",
                    duration_minutes=5,
                    teacher_action="Collect and review individual 2-minute exit tickets for next-day grouping.",
                    student_action="Independently solve one diagnostic problem and write one sentence explaining the reasoning.",
                ),
            ],
            differentiation={
                "beginner": "Provide concrete manipulatives, sentence starters, and pre-partitioned visual frames.",
                "intermediate": "Pair with peer discussion prompts and structured verification checklists.",
                "advanced": "Challenge with inverse problems, non-routine cases, and evaluating peer sample responses.",
            },
            assessment_check=f"Students complete a 2-question exit ticket requiring both final answer and written justification.",
        )

    def _build_mock_activity(self, subject: str, topic: str) -> DraftActivity:
        return DraftActivity(
            activity_name=f"Hands-On Reasoning Workshop: {topic}",
            instructions=(
                f"1. Divide class into small teams of 3-4.\n"
                f"2. Distribute three problem cards containing one correct solution and two classic misconception answers.\n"
                f"3. Have teams act as 'math detectives' to diagnose which response has the error, explain the flaw, and prove the correct solution.\n"
                f"4. Teams present their diagnostic defense in a 60-second classroom share."
            ),
            group_size="Small groups of 3-4",
            materials_needed=["Problem Detective Cards", "Chart paper or mini whiteboards", "Colored markers"],
            expected_takeaway=f"Students articulate the underlying rules of {topic} and recognize common trap reasoning patterns.",
        )

    def _build_mock_content_items(
        self, subject: str, topic: str, target_code: str | None
    ) -> list[DraftContentItem]:
        if topic == "Fractions":
            return [
                DraftContentItem(
                    question="Calculate 1/3 + 1/6. Simplify your answer if possible.",
                    options=["2/9", "3/6", "1/2", "2/6"],
                    correct_answer="1/2",
                    explanation="Rename 1/3 to 2/6 using common denominator 6. Then 2/6 + 1/6 = 3/6 = 1/2. Adding numerators and denominators (1+1)/(3+6) = 2/9 is an additive error (M01).",
                    hints=["Find a common denominator so the parts are the same size before adding."],
                    difficulty="intermediate",
                    targeted_misconception="M01",
                ),
                DraftContentItem(
                    question="Which fraction is larger: 1/4 or 1/8? Explain why.",
                    options=["1/4", "1/8", "They are equal"],
                    correct_answer="1/4",
                    explanation="When the numerator is 1, dividing a whole into 4 equal pieces produces larger pieces than dividing into 8 equal pieces. Believing 1/8 is larger because 8 > 4 is whole-number bias (M02).",
                    hints=["Think about sharing a pizza among 4 friends versus 8 friends."],
                    difficulty="beginner",
                    targeted_misconception="M02",
                ),
                DraftContentItem(
                    question="Write 2/5 with denominator 15.",
                    options=None,
                    correct_answer="6/15",
                    explanation="Multiply numerator and denominator by 3: (2 * 3) / (5 * 3) = 6/15.",
                    hints=["What number must you multiply 5 by to get 15?"],
                    difficulty="intermediate",
                    targeted_misconception="M04",
                ),
            ]
        elif topic == "Basic algebra":
            return [
                DraftContentItem(
                    question="Solve for x: x + 7 = 15.",
                    options=["x = 8", "x = 22", "x = 105", "x = 2"],
                    correct_answer="x = 8",
                    explanation="Subtract 7 from both sides: x = 15 - 7 = 8. Adding 7 to 15 (giving 22) is an inverse-operation error (ALG01).",
                    hints=["What operation undoes addition?"],
                    difficulty="beginner",
                    targeted_misconception="ALG01",
                ),
                DraftContentItem(
                    question="Expand the expression: 3(x + 4).",
                    options=["3x + 4", "3x + 12", "x + 12", "7x"],
                    correct_answer="3x + 12",
                    explanation="Multiply each term inside the parentheses by 3: 3 * x + 3 * 4 = 3x + 12. Forgetting to multiply 4 gives 3x + 4 (ALG02).",
                    hints=["Make sure the factor outside multiplies EVERY term inside."],
                    difficulty="intermediate",
                    targeted_misconception="ALG02",
                ),
                DraftContentItem(
                    question="Solve for y: 4y = 28.",
                    options=["y = 7", "y = 24", "y = 32", "y = 112"],
                    correct_answer="y = 7",
                    explanation="Divide both sides by 4: y = 28 / 4 = 7. Subtracting 4 from 28 is an operation error (ALG03).",
                    hints=["4y means 4 multiplied by y. How do you undo multiplication?"],
                    difficulty="intermediate",
                    targeted_misconception="ALG03",
                ),
            ]
        elif topic == "Force and motion":
            return [
                DraftContentItem(
                    question="A hockey puck slides across frictionless ice at 5 m/s after being hit. What forward force is required to keep it moving at 5 m/s?",
                    options=["5 N", "Zero forward force", "A force equal to its mass", "Continuous pushing force"],
                    correct_answer="Zero forward force",
                    explanation="By Newton's First Law (inertia), an object in motion stays in motion at constant velocity without needing a net force if friction is zero. Believing a continuing forward force is needed is misconception FM01.",
                    hints=["In the absence of friction, what causes an object to slow down?"],
                    difficulty="intermediate",
                    targeted_misconception="FM01",
                ),
                DraftContentItem(
                    question="A toy car travels 30 meters in 6 seconds. What is its average speed?",
                    options=["5 m/s", "180 m/s", "36 m/s", "24 m/s"],
                    correct_answer="5 m/s",
                    explanation="Average speed = total distance / elapsed time = 30 m / 6 s = 5 m/s. Multiplying 30 * 6 = 180 is speed formula confusion (FM02).",
                    hints=["Speed equals distance divided by time."],
                    difficulty="beginner",
                    targeted_misconception="FM02",
                ),
            ]
        elif topic == "Basic electricity":
            return [
                DraftContentItem(
                    question="Why does a lightbulb fail to light if one connecting wire in a battery circuit is disconnected?",
                    options=["The circuit is open so charge cannot flow in a complete loop", "The battery ran out of voltage immediately", "The bulb burned out", "The current got stuck in the wire"],
                    correct_answer="The circuit is open so charge cannot flow in a complete loop",
                    explanation="Current requires a continuous conducting path from the battery back to the battery. An open circuit stops the flow of charge (EL01).",
                    hints=["Can water flow through a pipe if there is a gap?"],
                    difficulty="beginner",
                    targeted_misconception="EL01",
                ),
                DraftContentItem(
                    question="In a simple circuit with two identical bulbs connected in series, how does the electric current entering the first bulb compare to the current leaving the second bulb?",
                    options=["The current is the same at both points", "The current is higher at the first bulb because the bulbs use up current", "The current is zero at the second bulb", "The second bulb gets more current"],
                    correct_answer="The current is the same at both points",
                    explanation="In a series circuit, current is the rate of flow of charge and is identical at all points in the loop. Bulbs consume energy, not current (EL02).",
                    hints=["Charge is conserved and does not get 'eaten up' by components."],
                    difficulty="intermediate",
                    targeted_misconception="EL02",
                ),
            ]
        elif topic == "Subject-verb agreement":
            return [
                DraftContentItem(
                    question="Choose the correct verb: The bouquet of fresh flowers _____ lovely on the dining table.",
                    options=["smell", "smells", "smelling", "are smelling"],
                    correct_answer="smells",
                    explanation="The subject is the singular noun 'bouquet'. The prepositional phrase 'of fresh flowers' does not change the subject. A singular subject takes 'smells' (SV01).",
                    hints=["Cross out 'of fresh flowers' to find the real subject."],
                    difficulty="intermediate",
                    targeted_misconception="SV01",
                ),
                DraftContentItem(
                    question="Choose the correct verb: Neither the teacher nor the students _____ in the auditorium.",
                    options=["is", "are", "was", "be"],
                    correct_answer="are",
                    explanation="When subjects are joined by 'neither... nor', the verb agrees with the closer subject. Here 'students' is plural, so 'are' is correct (SV03).",
                    hints=["Look at the subject closest to the verb."],
                    difficulty="advanced",
                    targeted_misconception="SV03",
                ),
            ]
        else: # Grammar
            return [
                DraftContentItem(
                    question="Select the sentence with correct verb tense consistency:",
                    options=[
                        "Yesterday she went to the library and borrowed two books.",
                        "Yesterday she goes to the library and borrowed two books.",
                        "Tomorrow she went to the library.",
                        "She is going to the library yesterday.",
                    ],
                    correct_answer="Yesterday she went to the library and borrowed two books.",
                    explanation="'Yesterday' signals the past tense. Both verbs ('went' and 'borrowed') must remain in the simple past (GR01).",
                    hints=["Check that the tense matches the time word 'Yesterday'."],
                    difficulty="beginner",
                    targeted_misconception="GR01",
                ),
            ]


class OpenRouterCopilotProvider:
    name = "openrouter"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: float = 25,
        client=None,
        fallback_provider: MockCopilotProvider | None = None,
        chat_client=None,
        provider_name: str = "openrouter",
    ) -> None:
        self.name = provider_name
        self.client = chat_client or OpenRouterChatClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            client=client,
        )
        self.model_version = model
        self.fallback = fallback_provider or MockCopilotProvider()

    def generate(
        self,
        request: CopilotChatRequest,
        context_summary: ClassContextSummary | None = None,
        grounding_text: str = "",
    ) -> CopilotChatResponse:
        subject, topic = self.fallback._resolve_subject_topic(request, context_summary)
        if subject == "Unsupported":
            return self.fallback.generate(request, context_summary, grounding_text)
        intent = detect_intent(request.message, request.action)

        prompt = self._build_prompt(request, context_summary, grounding_text, subject, topic, intent)

        try:
            content = self.client.complete_json(prompt=prompt, temperature=0.3)
            data = json.loads(content)

            # Extract fields with safe fallbacks
            reply_text = data.get("reply", "")
            if not reply_text:
                raise ValueError("Model response missing 'reply' field")

            resp_intent = data.get("intent", intent)
            followups = data.get("suggested_followups", [])

            draft_content = None
            if "draft_content" in data and isinstance(data["draft_content"], dict):
                try:
                    draft_content = DraftEducationalContent.model_validate(data["draft_content"])
                except Exception:
                    draft_content = None

            return CopilotChatResponse(
                reply=reply_text,
                intent=resp_intent,
                subject=subject,
                topic=topic,
                class_id=context_summary.class_id if context_summary else None,
                class_context_summary=context_summary,
                draft_content=draft_content,
                suggested_followups=followups,
                provider=self.name,
                model_version=self.model_version,
            )

        except (ProviderRateLimited, ProviderConfigurationError):
            # Propagate configuration errors and explicit rate limits
            raise
        except Exception:
            # Handle model timeouts, provider network hiccups, or malformed JSON via graceful fallback
            fallback_resp = self.fallback.generate(request, context_summary, grounding_text)
            note = f"\n\n*(Live {self.name} was unavailable; this is explicitly labeled template fallback feedback.)*"
            return fallback_resp.model_copy(
                update={
                    "reply": fallback_resp.reply + note,
                    "provider": f"{self.name}_fallback",
                    "model_version": None,
                }
            )

    def _build_prompt(
        self,
        request: CopilotChatRequest,
        context_summary: ClassContextSummary | None,
        grounding_text: str,
        subject: str,
        topic: str,
        intent: str,
    ) -> str:
        prompt_parts = [
            "You are the AI Teacher Copilot for ClassPulse AI, an intelligent, context-aware teaching assistant.",
            f"Subject: {subject}",
            f"Topic: {topic}",
            f"Detected Intent: {intent}",
            "",
            "CRITICAL ARCHITECTURAL CONSTRAINTS:",
            "1. GROUNDING: Cite only supplied classroom counts and baseline/reassessment evidence. Student identifiers are intentionally withheld; never invent or request them. Never invent counts, scores, diagnoses or causal learning claims.",
            "2. DRAFTS: Any generated educational material (worksheets, quizzes, lesson plans) MUST be marked as a draft and cannot autonomously modify student records or grades.",
            "3. PEDAGOGICAL TONE: Professional, encouraging, evidence-driven, and supportive for educators.",
            "",
        ]

        if grounding_text:
            prompt_parts.append(f"CLASSROOM CONTEXT:\n{grounding_text}\n")
        else:
            prompt_parts.append("CLASSROOM CONTEXT: No specific class selected. Provide general curriculum and pedagogical guidance for the specified subject and topic.\n")

        if request.history:
            prompt_parts.append("CONVERSATION HISTORY:")
            for msg in request.history[-6:]:
                prompt_parts.append(f"- {msg.role.upper()}: {msg.content}")
            prompt_parts.append("")

        prompt_parts.append(f"TEACHER CURRENT MESSAGE:\n{request.message}\n")

        prompt_parts.append(
            "Respond strictly in valid JSON adhering to this JSON schema:\n"
            "{\n"
            '  "reply": "Detailed markdown explanation or response for the teacher",\n'
            '  "intent": "classroom_intelligence" | "teaching_assistance" | "content_generation" | "conversational",\n'
            '  "suggested_followups": ["followup question 1", "followup question 2"],\n'
            '  "draft_content": null or {\n'
            '    "content_type": "worksheet" | "quiz" | "lesson_plan" | "practice_questions" | "remedial_exercise" | "classroom_activity",\n'
            '    "title": "Title",\n'
            '    "target_audience": "all",\n'
            '    "misconception_code": "M01" or null,\n'
            '    "items": [{"question": "...", "options": ["..."], "correct_answer": "...", "explanation": "...", "hints": ["..."], "difficulty": "intermediate"}],\n'
            '    "is_draft": true\n'
            "  }\n"
            "}"
        )

        return "\n".join(prompt_parts)


def create_copilot_provider(settings, client=None) -> MockCopilotProvider | OpenRouterCopilotProvider:
    if settings.ai_provider == "gemini":
        from app.services.gemini_client import GeminiChatClient
        return OpenRouterCopilotProvider(
            api_key="", model=settings.gemini_model,
            chat_client=GeminiChatClient.from_settings(settings, client=client),
            provider_name="gemini",
        )
    if settings.ai_provider == "openrouter":
        if not settings.openrouter_api_key:
            raise ProviderConfigurationError("OPENROUTER_API_KEY is required when AI_PROVIDER=openrouter")
        if not settings.openrouter_model:
            raise ProviderConfigurationError("OPENROUTER_MODEL is required when AI_PROVIDER=openrouter")
        return OpenRouterCopilotProvider(
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            base_url=settings.openrouter_base_url,
            timeout_seconds=settings.openrouter_timeout_seconds,
            client=client,
        )
    return MockCopilotProvider()
