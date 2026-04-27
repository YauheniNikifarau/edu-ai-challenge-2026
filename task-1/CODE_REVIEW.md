# Code Review — Leaderboard (task-1)

**Reviewer:** Frontend Tech Lead  
**Date:** 2026-04-27  
**Scope:** `task-1/leaderboard/src` — JS/JSX logic, data integrity, accessibility, architecture

---

## Summary

The codebase is well-structured, follows the spec closely, and is readable. State is managed cleanly in `App.jsx`, the `useLeaderboard` hook is a sensible abstraction, and the component tree is appropriately decomposed. The filtering pipeline is mostly correct. That said, there are several issues ranging from a clear visual bug to logic inefficiencies and accessibility gaps that should be addressed before shipping.

---

## 🔴 High — Bugs / Functional Issues

### 1. `PodiumSlot.jsx` — Position 3 uses silver colors instead of bronze

**File:** [`src/components/Podium/PodiumSlot.jsx:22-24`](leaderboard/src/components/Podium/PodiumSlot.jsx)

```js
// Current (wrong)
3: {
  ringColor: 'var(--color-ring-bronze)',
  badgeColor: 'var(--color-rank-badge-3)',
  blockColor: 'var(--color-podium-silver)',       // ← bug: should be bronze
  numeralColor: 'var(--color-podium-silver-text)', // ← bug: should be bronze
  blockHeight: 60,
},
```

`ringColor` and `badgeColor` correctly reference bronze tokens, but the podium block itself renders silver. This is a copy-paste error — position 3 should use `--color-podium-bronze` and `--color-podium-bronze-text`.

**Fix:**
```js
3: {
  ringColor: 'var(--color-ring-bronze)',
  badgeColor: 'var(--color-rank-badge-3)',
  blockColor: 'var(--color-podium-bronze)',
  numeralColor: 'var(--color-podium-bronze-text)',
  blockHeight: 60,
},
```

---

### 2. `EmployeeCard.jsx` — Space key not handled on interactive card

**File:** [`src/components/LeaderboardList/EmployeeCard.jsx:74`](leaderboard/src/components/LeaderboardList/EmployeeCard.jsx)

```js
onKeyDown={(e) => e.key === 'Enter' && onToggle(employee.id)}
```

The card has `role="button"` and `tabIndex={0}`, which means both Enter **and** Space must trigger activation per WAI-ARIA spec. Space is currently a no-op.

**Fix:**
```js
onKeyDown={(e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    onToggle(employee.id);
  }
}}
```

---

### 3. `Dropdown.jsx` — Custom listbox missing keyboard navigation

**File:** [`src/components/Filters/Dropdown.jsx`](leaderboard/src/components/Filters/Dropdown.jsx)

The component uses `role="listbox"` and `role="option"`, which carry WAI-ARIA keyboard expectations: `Escape` to close, `ArrowDown`/`ArrowUp` to navigate options, `Enter`/`Space` to select. None of these are implemented. Only outside-click dismissal exists. This renders the filter unusable for keyboard-only users.

---

## 🟡 Medium — Logic and Design Issues

### 4. `useLeaderboard.js` — Three separate filter passes to count categories

**File:** [`src/hooks/useLeaderboard.js:10-18`](leaderboard/src/hooks/useLeaderboard.js)

```js
const publicSpeakingCount = filteredActivities.filter(
  (a) => a.category === 'Public Speaking'
).length;
const educationCount = filteredActivities.filter(
  (a) => a.category === 'Education'
).length;
const universityPartnersCount = filteredActivities.filter(
  (a) => a.category === 'University Partners'
).length;
```

This iterates `filteredActivities` three times. For an employee with 136 activities, that's 408 iterations. When a category filter is active, two of the three counts will always be 0 — wasted work. A single `reduce` handles this in one pass:

```js
const counts = filteredActivities.reduce(
  (acc, a) => {
    if (a.category === 'Public Speaking') acc.publicSpeakingCount++;
    else if (a.category === 'Education') acc.educationCount++;
    else if (a.category === 'University Partners') acc.universityPartnersCount++;
    return acc;
  },
  { publicSpeakingCount: 0, educationCount: 0, universityPartnersCount: 0 }
);
```

This also makes adding a fourth category a one-line change rather than a copy-paste block.

---

### 5. `Podium.jsx` — Re-runs `matchesSearch` that the hook already computed

**File:** [`src/components/Podium/Podium.jsx:16-28`](leaderboard/src/components/Podium/Podium.jsx)

```js
<PodiumSlot
  employee={second}
  position={2}
  hidden={!matchesSearch(second, search)}
/>
```

`matchesSearch` is being called in a presentational component, duplicating logic that `useLeaderboard` already executes. This creates a coupling between the view layer and the utility module and makes it non-obvious that podium visibility is a derived concern.

The `search` prop currently flows all the way from `App` → `Podium` → `matchesSearch`. A cleaner approach: compute a `visibleInPodium` boolean per employee inside `useLeaderboard` and pass it as a field on each `topThree` entry, keeping the component dumb.

---

### 6. `filters.js` — `sortByPoints` has no tie-breaking

**File:** [`src/utils/filters.js:30-32`](leaderboard/src/utils/filters.js)

```js
export function sortByPoints(employees) {
  return [...employees].sort((a, b) => b.filteredTotal - a.filteredTotal);
}
```

When two employees have equal `filteredTotal`, their relative order is non-deterministic — it depends on their order in the source JSON and JavaScript engine sort stability. This means ranks can silently shift across re-renders or filter changes. A secondary sort key (e.g., `id`) makes the ranking stable:

```js
export function sortByPoints(employees) {
  return [...employees].sort(
    (a, b) => b.filteredTotal - a.filteredTotal || a.id.localeCompare(b.id)
  );
}
```

---

### 7. `ActivityTable.jsx` — Shows all activities despite "Recent Activity" label

**File:** [`src/components/LeaderboardList/ActivityTable.jsx:6`](leaderboard/src/components/LeaderboardList/ActivityTable.jsx)

```js
const sorted = sortActivitiesByDateDesc(activities);
```

The section is labeled **"Recent Activity"** but renders the entire `filteredActivities` array — up to 136 rows for one employee. There is no cap, pagination, or "show more" control. For usability and render performance, a reasonable default limit (e.g., 10 most recent) with an optional expand should be applied:

```js
const sorted = sortActivitiesByDateDesc(activities).slice(0, 10);
```

---

### 8. `Filters.jsx` — Year options are hardcoded

**File:** [`src/components/Filters/Filters.jsx:5-9`](leaderboard/src/components/Filters/Filters.jsx)

```js
const YEAR_OPTIONS = [
  { value: 'all', label: 'All Years' },
  { value: '2025', label: '2025' },
  { value: '2024', label: '2024' },
];
```

If the data is extended to include 2026 activities, the year filter silently stops working — 2026 records exist but are unreachable through the UI. Year options should be derived from the dataset at startup:

```js
// In App.jsx or a dedicated util
const yearOptions = [
  { value: 'all', label: 'All Years' },
  ...Array.from(
    new Set(employees.flatMap((e) => e.activities.map((a) => a.year)))
  )
    .sort((a, b) => b - a)
    .map((y) => ({ value: String(y), label: String(y) })),
];
```

---

## 🔵 Low — Code Quality and Maintainability

### 9. `filters.js` — `getYearFromDate` and `getMonthFromDate` are dead code in the filtering path

**File:** [`src/utils/filters.js:6-18`](leaderboard/src/utils/filters.js)

```js
export function getYearFromDate(dateStr) { ... }
export function getMonthFromDate(dateStr) { ... }
export function getQuarterFromMonth(month) { ... }
```

These are exported and appear designed to derive `year`/`quarter` from the `date` string. However, `filterActivities` reads `activity.year` and `activity.quarter` directly from the pre-computed JSON fields — the parse functions are never called. This is misleading: a reader would expect the filtering to use the date string, or expect these functions to validate the pre-computed fields. Either remove them or use them to cross-validate the JSON at dev time.

---

### 10. `ActivityTable.jsx` — `sortActivitiesByDateDesc` runs on every render, no memoization

**File:** [`src/components/LeaderboardList/ActivityTable.jsx:6`](leaderboard/src/components/LeaderboardList/ActivityTable.jsx)

```js
const sorted = sortActivitiesByDateDesc(activities);
```

`sortActivitiesByDateDesc` creates a new sorted array on each render. Since `ActivityTable` is only visible when a card is expanded, and `activities` is stable (it's a slice of JSON), this is acceptable — but once a "show more" control is added or the list grows, a `useMemo` wrapper becomes important.

---

### 11. `EmployeeCard.jsx` — JS state for tooltips is fragile; CSS hover preferred

**File:** [`src/components/LeaderboardList/EmployeeCard.jsx:66-137`](leaderboard/src/components/LeaderboardList/EmployeeCard.jsx)

```js
const [hoveredIcon, setHoveredIcon] = useState(null);
```

A shared `hoveredIcon` state is used to control three separate tooltips. If the mouse moves quickly from one icon group to another, the `onMouseLeave` of the first group fires `setHoveredIcon(null)` which may race with the `onMouseEnter` of the second group. The tooltip flickers. CSS `:hover + .tooltip` (or `[data-tooltip]`) is immune to this and requires no component state.

---

### 12. `EmployeeCard.jsx` — Icon groups have no accessible label for screen readers

**File:** [`src/components/LeaderboardList/EmployeeCard.jsx:93-138`](leaderboard/src/components/LeaderboardList/EmployeeCard.jsx)

The icon groups (`MonitorIcon`, `GradCapIcon`, `UniversityIcon`) are `aria-hidden="true"`. Their adjacent count spans have no label. A screen reader announces only a number (e.g., `"3"`) with no context of what it counts. Each group should carry an `aria-label`:

```jsx
<div
  className={styles.iconGroup}
  aria-label={`Public Speaking: ${employee.publicSpeakingCount}`}
  ...
>
```

---

## Data Integrity Note

A spot check of `employees.json` shows that `year`, `quarter`, and `date` fields are consistent across all sampled entries (the pre-computed fields match the parsed date values). The `[EDU]`/`[LAB]`/`[UNI]` title prefixes map to `Public Speaking`/`Education`/`University Partners` categories respectively, which is counter-intuitive but matches the spec in `architecture.md`.

---

## Issue Summary

| # | Severity | File | Issue |
|---|----------|------|-------|
| 1 | 🔴 High | `PodiumSlot.jsx` | Position 3 renders silver podium block instead of bronze |
| 2 | 🔴 High | `EmployeeCard.jsx` | Space key missing on `role="button"` element |
| 3 | 🔴 High | `Dropdown.jsx` | `role="listbox"` has no keyboard navigation |
| 4 | 🟡 Medium | `useLeaderboard.js` | Three filter passes to count categories; use single reduce |
| 5 | 🟡 Medium | `Podium.jsx` | `matchesSearch` called in component, duplicating hook logic |
| 6 | 🟡 Medium | `filters.js` | `sortByPoints` has no tie-breaking — ranks are non-deterministic on equal scores |
| 7 | 🟡 Medium | `ActivityTable.jsx` | All activities rendered under "Recent Activity" label — needs a cap |
| 8 | 🟡 Medium | `Filters.jsx` | Year options hardcoded; breaks silently when new year data is added |
| 9 | 🔵 Low | `filters.js` | `getYearFromDate`, `getMonthFromDate`, `getQuarterFromMonth` are unused dead code |
| 10 | 🔵 Low | `ActivityTable.jsx` | `sortActivitiesByDateDesc` lacks `useMemo` |
| 11 | 🔵 Low | `EmployeeCard.jsx` | JS state for tooltips can flicker; CSS hover is more reliable |
| 12 | 🔵 Low | `EmployeeCard.jsx` | Icon groups missing `aria-label`, inaccessible to screen readers |
