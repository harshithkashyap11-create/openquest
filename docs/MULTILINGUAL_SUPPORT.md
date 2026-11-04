# English, Hindi and Telugu

Existing UI resources remain in `frontend/src/i18n/{en,hi,te}.json`. New learning,
review, authentication and offline controls use the same translation mechanism.
Language switching changes interface labels without replacing the current learner
or classroom. The key-set checker now exits with failure on mismatches.

Lesson Studio requests independently generated drafts in en/hi/te. Mathematics
must use readable plain-text fractions (for example 1/2), operators and units;
unsupported LaTeX markup is rejected because this renderer is plain text. English
grammar examples stay in English when the surrounding explanation is regional.
Worked examples, correction of the mistaken rule, practice and exit ticket are
separate structured fields. A teacher must attest to linguistic and answer-key
review before approval; publication is separate.

Live native Gemini M01 drafts were generated and inspected in all three languages.
The initial prompts produced generic introductory fraction content, so target
misconception definitions and a required correction field were added. Revised
samples target common-denominator addition and preserve readable fraction notation.
See `upgrade-evidence/agentic/live-lessons.json` for the synthetic samples. This is
not an independent linguistic evaluation or proof across every topic.

Template mode supports English for the existing misconception catalog and authored
M01 content in Hindi/Telugu. New guided hint ladders support English throughout and
M01 in Hindi/Telugu. Other regional template requests return an explicit unsupported
response. Opt-in live tutoring can request all three languages; a two-level Telugu
M01 synthetic smoke check returned validated response-aware hints. Saved published lessons retain their own language regardless of UI locale.
Downloaded content keeps that language offline.

Translation variants tied to a canonical source revision, automated terminology
checks beyond markup, independent language adjudication, voice input and spoken
playback are not implemented. Independently generated language drafts must not be
represented as synchronized reviewed translations of one canonical source.
