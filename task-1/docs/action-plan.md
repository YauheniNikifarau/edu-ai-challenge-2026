# Action Plan — Leaderboard Implementation

## Overview

| Phase | Description | Est. Effort |
|-------|-------------|-------------|
| Phase 1 | Project setup & scaffolding | ~1h |
| Phase 2 | Data generation | ~1h |
| Phase 3 | Core components | ~3h |
| Phase 4 | Filters & logic | ~2h |
| Phase 5 | Responsive + polish | ~1h |
| Phase 6 | Deployment + report | ~1h |
| **Total** | | **~9h** |

---

## Phase 1 — Project Setup

### Step 1.1 — Initialize Vite + React project

```bash
npm create vite@latest leaderboard -- --template react
cd leaderboard
npm install
```

### Step 1.2 — Install gh-pages

```bash
npm install --save-dev gh-pages
```

### Step 1.3 — Configure `vite.config.js` for GitHub Pages

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/leaderboard/',
  plugins: [react()],
})
```

### Step 1.4 — Configure `package.json`

Add `homepage` and deploy script:

```json
{
  "homepage": "https://<username>.github.io/leaderboard",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "predeploy": "npm run build",
    "deploy": "gh-pages -d dist"
  }
}
```

### Step 1.5 — Clean up Vite boilerplate

- Remove `src/assets/react.svg`, `public/vite.svg`
- Clear `App.jsx` and `App.css`
- Set up `index.css` with CSS variables (see [visual-design.md](./visual-design.md))

### Step 1.6 — Create folder structure

```bash
mkdir -p src/{data,components/{Header,Filters,Podium,LeaderboardList,CategoryBadge,EmptyState},hooks,utils}
```

### Deliverable
Working `npm run dev` with blank page, no errors.

---

## Phase 2 — Data Generation

### Step 2.1 — Generate `employees.json`

Create 20 fake employees following rules in [data-model.md](./data-model.md):

- 20 unique employees
- Mix of genders (10–12 male, 8–10 female)
- Range of job titles (see data model)
- 3–4 different department code prefixes
- Each employee: 5–15 activities across 2024–2025, all 4 quarters, 2–3 categories

**Point total distribution target:**
- Ranks 1–3: 400–600 pts
- Ranks 4–8: 250–399 pts
- Ranks 9–14: 100–249 pts
- Ranks 15–20: 30–99 pts

### Step 2.2 — Assign avatar URLs

Use `https://randomuser.me/api/portraits/[men|women]/N.jpg` (N = 1–70).
Match portrait gender to the employee name.

### Step 2.3 — Validate JSON

Check against schema in [data-model.md](./data-model.md):
- No duplicate `id` values
- `year` and `quarter` match `date` string
- All `category` values are exact enum strings
- All `date` strings match `DD-Mon-YYYY` format

### Deliverable
`src/data/employees.json` with 20 employees, readable and passing manual validation.

---

## Phase 3 — Core Components

Build components bottom-up (smallest/most reusable first).

### Step 3.1 — `CategoryBadge`

**File:** `src/components/CategoryBadge/CategoryBadge.jsx`

Renders a gray pill with category text.

```jsx
export function CategoryBadge({ category }) {
  return <span className={styles.badge}>{category}</span>
}
```

Test: renders correctly for each of the 3 categories.

---

### Step 3.2 — `EmptyState`

**File:** `src/components/EmptyState/EmptyState.jsx`

Simple info message with icon.

```jsx
export function EmptyState() {
  return (
    <div className={styles.container}>
      <span className={styles.icon}>ℹ</span>
      <span>No activities found matching the current filters.</span>
    </div>
  )
}
```

---

### Step 3.3 — `Header`

**File:** `src/components/Header/Header.jsx`

Static component — title and subtitle.

```jsx
export function Header() {
  return (
    <header className={styles.header}>
      <h1>Leaderboard</h1>
      <p>Top performers based on contributions and activity</p>
    </header>
  )
}
```

---

### Step 3.4 — `ActivityTable`

**File:** `src/components/LeaderboardList/ActivityTable.jsx`

Receives filtered activities array. Renders table with 4 columns.

- Sort activities by date descending before render.
- Use `<CategoryBadge>` in the CATEGORY column.
- Points column: blue bold text with `+` prefix.

---

### Step 3.5 — `EmployeeCard`

**File:** `src/components/LeaderboardList/EmployeeCard.jsx`

Props: `{ employee, isExpanded, onToggle }`

Structure:
```
div.card (onClick → onToggle)
  div.cardHeader
    span.rank
    img.avatar
    div.info
      span.name
      span.jobTitle + span.dept
    div.icons
      div.iconGroup (with tooltip)
        MonitorIcon
        span.count
      div.iconGroup (with tooltip)
        GradCapIcon
        span.count
    div.divider
    div.total
      span.totalLabel
      StarIcon + span.totalScore
    ChevronIcon (rotated when expanded)
  (isExpanded &&) ActivityTable
```

**Tooltip:** On desktop, hovering the icon group shows the category name using a CSS `::after` pseudo-element or a small absolute-positioned div.

---

### Step 3.6 — `LeaderboardList`

**File:** `src/components/LeaderboardList/LeaderboardList.jsx`

Props: `{ employees, expandedId, onToggle }`

Renders `<EmployeeCard>` for each employee in `employees` array.

```jsx
export function LeaderboardList({ employees, expandedId, onToggle }) {
  return (
    <div className={styles.list}>
      {employees.map(emp => (
        <EmployeeCard
          key={emp.id}
          employee={emp}
          isExpanded={expandedId === emp.id}
          onToggle={onToggle}
        />
      ))}
    </div>
  )
}
```

---

### Step 3.7 — `PodiumSlot`

**File:** `src/components/Podium/PodiumSlot.jsx`

Props: `{ employee, position }` where position is `1 | 2 | 3`.

Structure:
```
div.slot.slot--position-{1|2|3}
  div.avatarWrapper
    img.avatar
    span.ringBorder  (colored ring via CSS)
    span.rankBadge   {position}
  span.name
  span.jobTitle
  span.deptCode
  div.score
    StarIcon + span.points
  div.podiumBlock    {position}
```

---

### Step 3.8 — `Podium`

**File:** `src/components/Podium/Podium.jsx`

Props: `{ topThree }` — array of 0–3 employees.

Renders nothing if `topThree.length === 0`.

Order: slot for position 2 (left), slot for position 1 (center), slot for position 3 (right).

```jsx
export function Podium({ topThree }) {
  if (topThree.length === 0) return null;
  const first  = topThree[0];
  const second = topThree[1] ?? null;
  const third  = topThree[2] ?? null;

  return (
    <div className={styles.podium}>
      {second && <PodiumSlot employee={second} position={2} />}
      <PodiumSlot employee={first} position={1} />
      {third && <PodiumSlot employee={third} position={3} />}
    </div>
  )
}
```

---

### Step 3.9 — `Filters`

**File:** `src/components/Filters/Filters.jsx`

Props: `{ year, quarter, category, search, onChange }`

Renders 3 `<Dropdown>` + 1 `<SearchInput>` in a white panel.

#### `Dropdown` Component

- Custom implementation (not native `<select>`) for matching visual style.
- Options list appears as an absolute-positioned panel below the trigger.
- `useEffect` to close on outside click:

```javascript
useEffect(() => {
  const handleClick = (e) => {
    if (!ref.current.contains(e.target)) setOpen(false);
  };
  document.addEventListener('mousedown', handleClick);
  return () => document.removeEventListener('mousedown', handleClick);
}, []);
```

#### `SearchInput` Component

- Controlled input.
- Shows `×` button when value is not empty.
- Calls `onClear` (which sets value to `""`) on `×` click.

---

## Phase 4 — Logic & State

### Step 4.1 — `useLeaderboard` Hook

**File:** `src/hooks/useLeaderboard.js`

Implement full filtering + ranking logic (see [architecture.md](./architecture.md) section 4).

```javascript
export function useLeaderboard(employees, { year, quarter, category, search }) {
  return useMemo(() => {
    // 1. Filter activities per employee
    // 2. Filter employees by search
    // 3. Remove employees with 0 filtered total
    // 4. Sort by total descending
    // 5. Assign rank
    // 6. Return { rankedEmployees, topThree }
  }, [employees, year, quarter, category, search]);
}
```

Use `useMemo` to avoid recalculating on every render.

### Step 4.2 — Wire up `App.jsx`

```jsx
import employees from './data/employees.json'

export default function App() {
  const [year, setYear] = useState('all');
  const [quarter, setQuarter] = useState('all');
  const [category, setCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [expandedId, setExpandedId] = useState(null);

  const { rankedEmployees, topThree } = useLeaderboard(
    employees.employees,
    { year, quarter, category, search }
  );

  const handleToggle = (id) => {
    setExpandedId(prev => prev === id ? null : id);
  };

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <Header />
        <Filters year={year} quarter={quarter} category={category} search={search}
          onChange={{ setYear, setQuarter, setCategory, setSearch }} />
        {rankedEmployees.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <Podium topThree={topThree} />
            <LeaderboardList
              employees={rankedEmployees}
              expandedId={expandedId}
              onToggle={handleToggle}
            />
          </>
        )}
      </div>
    </div>
  );
}
```

### Step 4.3 — Manual testing of all filter combinations

| Test Case | Expected |
|-----------|----------|
| All defaults | All 20 employees shown, sorted by total |
| Year = 2025 | Only 2025 activities count; totals change; ranks may change |
| Quarter = Q1 | Only Q1 activities; some employees may drop to 0 and disappear |
| Category = Education | Only Education activities; icon counts update |
| Search = partial name | Only matching employees shown; podium updates |
| Search = nonsense | 0 results → EmptyState shown |
| Year + Quarter combined | AND logic — both filters apply |
| All 4 filters active | Narrowest result set |

---

## Phase 5 — Responsive & Polish

### Step 5.1 — Mobile layout (< 768px)

In `Filters.module.css`:
```css
@media (max-width: 767px) {
  .filtersRow {
    flex-direction: column;
  }
  .filtersRow > * {
    width: 100%;
  }
}
```

In `EmployeeCard.module.css` — adjust padding, font sizes for mobile.

In `Podium.module.css` — reduce avatar and block sizes for mobile.

### Step 5.2 — Edge case polish

- Rank badge overlaps avatar correctly (absolute positioning).
- Long employee names don't break layout (text-overflow: ellipsis or wrapping).
- Long activity titles in the table wrap gracefully.
- Chevron rotates smoothly on expand/collapse.

### Step 5.3 — Cross-browser check

Test in Chrome and Safari (macOS). Fix any CSS differences.

---

## Phase 6 — Deployment & Report

### Step 6.1 — Create GitHub repository

```bash
git init
git add .
git commit -m "initial commit"
gh repo create leaderboard --public
git push -u origin main
```

### Step 6.2 — Deploy to GitHub Pages

```bash
npm run deploy
```

Verify: `https://<username>.github.io/leaderboard/` is accessible.

### Step 6.3 — Enable GitHub Pages in repo settings

Repository → Settings → Pages → Source: `gh-pages` branch, `/ (root)`.

### Step 6.4 — Write `report.md` (in project root)

Content to include:
1. Approach overview
2. Tools and technologies used
3. How fake data was generated and why
4. How UI was replicated (components, CSS approach)
5. Data replacement strategy (names, avatars, activity titles, dept codes)
6. Deployment process
7. Live link

---

## Definition of Done

- [ ] App loads on GitHub Pages URL without errors
- [ ] All 4 filters work and combine correctly
- [ ] Podium shows correct top-3 for any filter combination
- [ ] List shows correct ranked order for any filter combination
- [ ] Empty state shows when no results
- [ ] Cards expand/collapse correctly (one at a time)
- [ ] Activity table shows filtered activities, sorted by date desc
- [ ] Responsive layout works on mobile (< 768px)
- [ ] No real data from original screenshots in the app
- [ ] `report.md` present in repo root
- [ ] Source code in GitHub repository
- [ ] Working GitHub Pages link
