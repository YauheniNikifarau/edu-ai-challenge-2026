# LearnBot — Telegram Learning Assistant

An AI-powered personal learning assistant built on **n8n + Telegram + OpenAI + Google Sheets**. Send it a URL, get a structured summary, then take a 5-question multiple-choice quiz with per-question feedback.

## Bot link

- Telegram: `@<your_bot_username>` _(replace after deploy)_

## Commands

| Command | What it does |
|---|---|
| `/start` | Greets the user and explains how to use the bot. |
| `/learn <url>` | Fetches the page, extracts text, and returns a structured summary (title, difficulty, 5–7 key points, main concepts). The material is saved for later. |
| `/quiz` | Lets you pick one of your saved materials and runs a 5-question multiple-choice quiz with inline buttons. |

## Step-by-step usage

1. Open Telegram and start a chat with the bot.
2. Send `/start` — you should get a welcome message.
3. Send `/learn https://example.com/some-article`.
   - The bot fetches the page, runs the **Teacher AI**, and replies with the title, difficulty, key points, and main concepts.
   - The material is now persisted in your library.
4. Send `/quiz`.
   - If you have one saved material, the quiz starts immediately.
   - If you have several, the bot shows an inline-keyboard list of your topics — tap one to start.
5. Answer each question by tapping `A`, `B`, `C`, or `D`.
   - You get instant correct/incorrect feedback after each question.
6. After question 5, the bot sends a results summary with your score (e.g. `4/5 (80%)`) and per-question recap.
7. Send `/quiz` again to retake or add a new URL with `/learn`.

## How to deploy your own copy

### 1. Prerequisites

- An [n8n](https://n8n.io) instance (cloud trial is enough — it includes free GPT tokens via the built-in AI gateway).
- A Telegram bot token from [@BotFather](https://t.me/BotFather).
- A Google account with access to Google Sheets (for persistence).

### 2. Create the Google Sheet

Create a spreadsheet with the following tabs (column headers shown):

- **Materials**: `id`, `userId`, `url`, `title`, `content`, `summary`, `difficulty`, `mainConcepts`, `addedDate`
- **Sessions**: `userId`, `state`, `materialId`, `questionIndex`, `attemptId`, `updatedAt`
- **Questions**: `materialId`, `questionId`, `question`, `optionA`, `optionB`, `optionC`, `optionD`, `correctAnswer`, `explanation`
- **Answers**: `userId`, `materialId`, `attemptId`, `questionId`, `userAnswer`, `isCorrect`, `answeredAt`

### 3. Import the workflows

In n8n, import in this order (because the main workflow references the sub-workflows by ID):

1. `workflows/LearnBot - Teacher AI.json`
2. `workflows/LearnBot - Examiner AI.json`
3. `workflows/LearnBot - Main Workflow.json`

After importing the main workflow:

- Open the **Run Teacher AI** node and re-bind it to the imported `LearnBot - Teacher AI` workflow.
- Open the **Run Examiner AI** node and re-bind it to the imported `LearnBot - Examiner AI` workflow.

### 4. Configure credentials

- **Telegram Trigger** + every Telegram node: bind your Telegram Bot API credential.
- **Every Google Sheets node**: bind your Google Sheets OAuth2 credential and point it at the spreadsheet/tabs from step 2.
- **OpenAI nodes** in the Teacher and Examiner sub-workflows: use the n8n-managed AI gateway (default) or replace with your own OpenAI API key.

### 5. Activate

Activate all three workflows. The Telegram Trigger registers a webhook automatically. Send `/start` to your bot — you should get a reply.

## Architecture (one-liner)

`Telegram Trigger → Router (message vs callback) → /start | /learn | /quiz handlers → Teacher AI sub-workflow (summary) / Examiner AI sub-workflow (5 MCQs) → Google Sheets (materials, sessions, questions, answers) → Telegram replies with inline keyboards.`

See `report.md` for design decisions and lessons learned.

## Troubleshooting

- **Bot does not respond**: workflow is not active, or Telegram credential is wrong. Re-activate the main workflow and check the webhook in BotFather.
- **`Error: AI Failed`** after `/learn`: the page was empty/paywalled or the LLM returned malformed JSON. Try a different URL.
- **`/quiz` says "no materials"**: send `/learn <url>` first.
- **Sub-workflow not found**: re-bind the `Run Teacher AI` / `Run Examiner AI` nodes after import (see step 3).
