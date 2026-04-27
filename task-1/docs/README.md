# Leaderboard — Project Documentation

> Replica of the internal company Leaderboard application built with React + fake JSON data, deployed to GitHub Pages.

## Contents

| File | Description |
|------|-------------|
| [functional-spec.md](./functional-spec.md) | Full UI & functional specification — all screens, components, states, interactions |
| [data-model.md](./data-model.md) | JSON data model, schemas, field descriptions, fake data generation rules |
| [architecture.md](./architecture.md) | React project structure, component tree, hooks, state management |
| [visual-design.md](./visual-design.md) | Colors, typography, spacing, responsive breakpoints |
| [action-plan.md](./action-plan.md) | Step-by-step implementation plan with task breakdown |

## Quick Overview

The Leaderboard displays a ranked list of employees based on their activity contributions. Key features:

- **Podium** — top-3 employees visualized as a medal podium
- **Ranked list** — all employees sorted by total points, expandable cards with activity history
- **Filters** — Year, Quarter, Category (all combinable), affect both rankings and displayed data
- **Search** — real-time employee name search with clear button
- **Responsive** — separate layouts for desktop and mobile
- **Empty state** — shown when filters produce no results

## Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Framework | React 18 (Vite) | Fast setup, modern tooling |
| Styling | Plain CSS (CSS Modules) | No UI library dependency, pixel-perfect control |
| Data | Static JSON | No backend required, GitHub Pages compatible |
| Deployment | GitHub Pages via `gh-pages` | Free hosting, fits requirements |
| Avatars | randomuser.me API URLs | Free, realistic photos, no download needed |
