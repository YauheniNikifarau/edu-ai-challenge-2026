# Report — AI Challenge 2.0 (Task 2: Event Hosting Platform)

## Overview
For this task, I built a lightweight event hosting and attendance platform from scratch using **Lovable** as the primary development environment. The application supports the full event lifecycle: **Publish → RSVP → Ticket → Check-in**, including waitlist management, role-based permissions, gallery moderation, and post-event feedback.

Unlike Task 1 (which was a UI replica), Task 2 required building a real, full-stack application with authentication, persistent state, and multiple user roles. To handle this complexity, I adopted a more rigorous, specification-driven workflow based on the **BMAD-Method**.

## Tools Used
- **Lovable** — primary build & deploy environment (frontend + Supabase backend)
- **BMAD-Method** — structured AI-agent framework for analysis, planning and implementation
- **Claude (Sonnet / Opus)** — reasoning model used inside the BMAD agents
- **Abacus AI ChatLLM** — secondary assistant for cross-checking specs and prompt refinement
- **Supabase** — auth, database, storage (managed through Lovable)
- **GitHub** — version control, repository hosting (`task-2` folder)
- **Browser DevTools** — manual QA, network inspection, responsive checks

## Approach

### BMAD-Method as the Backbone
Instead of jumping straight into prompting, I ran the task through the **BMAD-Method** pipeline, which simulates a small product team via specialized AI agents:

- **Analyst agent** — parsed the raw task description, extracted functional and non-functional requirements, and identified ambiguities (e.g. waitlist promotion semantics, role inheritance, "Ended" state behavior).
- **Product Manager agent** — produced a structured PRD covering user roles, core flows, edge cases, and acceptance criteria.
- **Architect agent** — defined the data model (Hosts, Events, RSVPs, Tickets, Waitlist, Gallery, Reports, Roles), permission matrix, and page/route map.
- **Scrum Master agent** — sliced the PRD into a sequence of **11 implementation stories**, each scoped to be executable as a single Lovable prompt without context overflow.

This produced a detailed, versioned specification *before* a single line of code was written — which turned out to be the single most important quality lever in the whole project.

## What Worked
- **Spec-first workflow.** Producing a full PRD + architecture before prompting eliminated almost all "AI drift" — the model rarely invented features or skipped requirements.
- **Role-based AI agents (BMAD).** Forcing different "personas" to challenge each other surfaced edge cases (e.g. waitlist promotion when capacity is *increased*, not just on cancellation) that I would have missed solo.
