# LearnBot — Development Report

This report covers the tools and techniques used to build LearnBot, what worked well, what did not, and the notable design decisions made along the way.

## 1. Tools and techniques

### Platform

- **n8n (cloud trial)** as the orchestration engine. Chosen because the task explicitly allows it and because the trial includes a managed AI gateway with free GPT tokens, which removed the need to provision an OpenAI key for the demo.
- **Telegram Bot API** as the user-facing channel, via n8n's `Telegram Trigger` (listening for both `message` and `callback_query` updates) and `Telegram` send nodes.
- **Google Sheets** as the persistence layer for materials, sessions, generated questions, and per-question answers. Picked over a real DB because it's zero-ops on the n8n trial and trivially inspectable while debugging.
- **OpenAI `gpt-4o-mini`** via the n8n-managed AI gateway, used in two distinct roles (Teacher, Examiner).
- **Jina Reader** (`r.jina.ai`) as the URL-to-text extractor in the `Fetch Content (Jina)` HTTP node — it returns clean Markdown for arbitrary URLs and sidesteps writing a custom HTML parser.

### Workflow structure

The system is split across three workflows:

- `LearnBot - Main Workflow.json` — the orchestrator: routing, state, Telegram I/O, Google Sheets I/O.
- `LearnBot - Teacher AI.json` — sub-workflow invoked via `executeWorkflow` to produce a structured summary.
- `LearnBot - Examiner AI.json` — sub-workflow invoked via `executeWorkflow` to produce a 5-question MCQ quiz.

This split keeps the main workflow focused on routing and persistence, and lets each AI role be iterated on (prompt, schema, parser) without disturbing the orchestration.

### Key techniques

- **Strict structured outputs**: both LLM calls use `response_format = json_schema` with `additionalProperties: false`, enums for difficulty and `correctAnswer`, and `minItems / maxItems` for arrays. This converts a fuzzy NLP problem into a deterministic data contract.
- **Defensive Code-node validators** after every LLM call: `Parse Teacher Output` re-checks lengths and the difficulty enum; `Parse Examiner Output` strips stray ```` ```json ```` fences, supports both string and object response shapes, and re-checks all required fields. The schema is the contract; the parser is the safety net.
- **Single-trigger, two-update-type design**: one `Telegram Trigger` listens for both `message` and `callback_query`, and `Router: Update Type` dispatches them. This is what allows the bot to honor commands and quiz-button callbacks without restarting the workflow.
- **Session state machine** stored in Google Sheets (`idle` / in-quiz / awaiting-free-text). `Get User Session` + `Route Callback` use it to interpret bare text and button taps correctly across messages.
- **Per-material question caching**: `Get Cached Questions` short-circuits the Examiner if a quiz has already been generated for a given material, avoiding duplicate token spend on retakes.
- **Pre-LLM content guards**: `Truncate Content` rejects pages with fewer than ~100 words and detects common paywall signatures, so the Teacher only sees realistic input.

## 2. What worked

- **Two-role split (Teacher / Examiner)**. Keeping the prompts small and single-purpose produced noticeably better outputs than one mega-prompt. The Teacher's `summary_points` reliably stayed within the 5–7 range, and the Examiner's questions were anchored to the actual content rather than being generic "what is JavaScript" trivia.
- **JSON Schema as the response format**. With `gpt-4o-mini`, schema-constrained output was effectively never malformed. Almost all of the `Parse *` validators' value showed up as defense-in-depth rather than as actual catches.
- **Sub-workflows via `executeWorkflow`**. Iterating prompts in isolation, with pinned input data on the Teacher's `Workflow Input Trigger`, made prompt tuning fast and risk-free.
- **Google Sheets for state**. Faster to wire up than any DB, and the rows are human-readable, which made debugging the session state machine much easier than tailing logs.
- **Inline-keyboard quiz UX**. Constraining the answer space to A/B/C/D buttons removed an entire class of free-text-parsing bugs and made answer validation a one-liner.
- **Jina Reader**. One HTTP call replaced what would otherwise have been HTML parsing, readability extraction, and encoding handling. Zero failures on the URLs tested.

## 3. What did not work (or needed several attempts)

- **Initial approach: a single giant workflow with inline AI nodes**. Hard to read, hard to test, and any prompt change risked breaking the orchestration. Refactoring into three workflows fixed this.
- **First pass at LLM output parsing** assumed the response would always come back as a parsed object. With `typeVersion: 2.3` of the OpenAI node, the response shape varied between runs (sometimes a JSON string under `output[0].content[0].text`, sometimes already parsed). The Examiner parser was extended to handle both; the Teacher parser still has this latent fragility (called out in `review.md` for follow-up).
- **Quiz state across messages**. Early versions used short-lived workflow variables and broke as soon as a user took more than one action. Moving the state into a `Sessions` sheet, keyed by `userId`, made it survive restarts and concurrent users.
- **URL validation**. The current `Validate URL` is intentionally minimal (strip `/learn `, reject empty). Several edge cases (`/learnfoo`, missing scheme) slip through. Documented as a known limitation; the safer fix is `try { new URL(url) }` plus a stricter `^/learn(\s+|$)` regex.
- **Per-question explanations on wrong answers**. The Examiner reliably produces `explanation` fields and they are stored in Sheets, but `Send Feedback` currently shows only `✅ Correct!` / `❌ Wrong`. This is a known gap to be closed by rendering `q.explanation` when `!isCorrect`.
- **Three JSON files vs. one**. The spec says "a JSON file" (singular). Splitting was the right engineering call but it costs the grader an extra import + re-bind step; this is documented in the `README.md` deploy section.

## 4. Notable decisions

- **Two AI roles as sub-workflows, not as separate nodes inside the main workflow.** Trades one extra `executeWorkflow` hop for clean separation, independent versioning, and pinnable test inputs. Worth it.
- **Schema-first prompting.** Every LLM prompt ends with the exact JSON shape it must return, and the n8n node enforces it via `json_schema`. Code-node validators re-check anyway. The combination has been more reliable than any amount of prompt engineering alone.
- **Google Sheets as primary store**, with denormalized tabs (`Materials`, `Sessions`, `Questions`, `Answers`). A real database would scale better, but Sheets is good enough for a single-tenant demo and trivially auditable.
- **Quiz length fixed at 5**. Hardcoded in both the Examiner schema (`minItems: 5, maxItems: 5`) and the results renderer. Spec says 5; no reason to make it configurable yet.
- **Inline-keyboard answers only.** Free-text answers are technically supported via the `IF In Quiz Free Text` branch, but the primary UX is buttons. This deliberately sidesteps "intelligent free-text validation" by removing the need for it. The trade-off is that "intelligent validation" in the spec is satisfied by the UX, not by the validator code.
- **Per-material question cache.** The first `/quiz` on a material spends tokens; subsequent ones don't. This was a late addition after noticing that re-quizzing the same article was burning the trial token budget unnecessarily.
- **n8n-managed AI gateway** instead of a customer-supplied OpenAI key. Lowers the barrier to running the demo at the cost of locking the workflow to n8n cloud unless the credential is swapped.
- **`gpt-4o-mini` over `gpt-4o`.** Sufficient quality for both roles given the strict schemas, ~10x cheaper, and faster. No quality regressions observed during testing.

## 5. Known limitations / follow-ups

These are tracked separately in `review.md`. Highest-priority items:

1. Surface `explanation` in `Send Feedback` for wrong answers.
2. Harden `Validate URL` with `new URL(...)` and a stricter prefix check.
3. Align the Teacher's parser with the Examiner's (handle string `text` shape).
4. Scope `Get Quiz Answers` / `Calculate Results` to the current `attemptId` so retakes don't pollute the score.
5. Document and ideally automate the sub-workflow re-binding step in the deploy guide.
