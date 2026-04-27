# Architecture — Leaderboard React Application

## 1. Project Structure

```
leaderboard/
├── public/
│   └── favicon.ico
├── src/
│   ├── data/
│   │   └── employees.json          # All fake employee + activity data
│   ├── components/
│   │   ├── Header/
│   │   │   ├── Header.jsx
│   │   │   └── Header.module.css
│   │   ├── Filters/
│   │   │   ├── Filters.jsx         # Container for all 4 filter controls
│   │   │   ├── Filters.module.css
│   │   │   ├── Dropdown.jsx        # Reusable custom dropdown
│   │   │   ├── Dropdown.module.css
│   │   │   ├── SearchInput.jsx     # Search with × clear button
│   │   │   └── SearchInput.module.css
│   │   ├── Podium/
│   │   │   ├── Podium.jsx          # Three-column podium layout
│   │   │   ├── Podium.module.css
│   │   │   ├── PodiumSlot.jsx      # Single position (avatar + name + block)
│   │   │   └── PodiumSlot.module.css
│   │   ├── LeaderboardList/
│   │   │   ├── LeaderboardList.jsx # Renders all employee cards
│   │   │   ├── LeaderboardList.module.css
│   │   │   ├── EmployeeCard.jsx    # Single card (collapsed + expanded)
│   │   │   ├── EmployeeCard.module.css
│   │   │   ├── ActivityTable.jsx   # Recent Activity table inside expanded card
│   │   │   └── ActivityTable.module.css
│   │   ├── CategoryBadge/
│   │   │   ├── CategoryBadge.jsx   # Gray pill badge
│   │   │   └── CategoryBadge.module.css
│   │   └── EmptyState/
│   │       ├── EmptyState.jsx
│   │       └── EmptyState.module.css
│   ├── hooks/
│   │   └── useLeaderboard.js       # Core filtering + ranking logic
│   ├── utils/
│   │   └── filters.js              # Pure filter helper functions
│   ├── App.jsx
│   ├── App.module.css
│   └── index.css                   # Global reset + CSS variables
├── index.html
├── vite.config.js
├── package.json
└── report.md
```

---

## 2. Component Tree

```
App
├── Header
└── main.container
    ├── Filters
    │   ├── Dropdown (year)
    │   ├── Dropdown (quarter)
    │   ├── Dropdown (category)
    │   └── SearchInput
    ├── Podium                        ← hidden when 0 results
    │   ├── PodiumSlot (position=2)   ← hidden when < 2 results
    │   ├── PodiumSlot (position=1)
    │   └── PodiumSlot (position=3)   ← hidden when < 3 results
    ├── LeaderboardList               ← hidden when 0 results
    │   └── EmployeeCard[]
    │       └── (when expanded) ActivityTable
    │           └── CategoryBadge[]
    └── EmptyState                    ← shown only when 0 results
```

---

## 3. State Architecture

All state lives in `App.jsx` and is passed down via props. No global state manager (Redux, Zustand) needed for this scope.

### 3.1 State Variables (`App.jsx`)

```javascript
const [selectedYear, setSelectedYear]         = useState('all');   // 'all' | '2025' | '2024'
const [selectedQuarter, setSelectedQuarter]   = useState('all');   // 'all' | '1' | '2' | '3' | '4'
const [selectedCategory, setSelectedCategory] = useState('all');   // 'all' | 'Education' | ...
const [searchQuery, setSearchQuery]           = useState('');       // free text
const [expandedEmployeeId, setExpandedEmployeeId] = useState(null); // string | null
```

### 3.2 Data Flow

```
employees.json
      │
      ▼
useLeaderboard(employees, { selectedYear, selectedQuarter, selectedCategory, searchQuery })
      │
      ▼ returns: { rankedEmployees, topThree }
      │
      ├──► Podium receives topThree[0..2]
      └──► LeaderboardList receives rankedEmployees
```

---

## 4. `useLeaderboard` Hook

**File:** `src/hooks/useLeaderboard.js`

### Signature

```javascript
function useLeaderboard(employees, filters) {
  // filters: { year, quarter, category, search }
  // returns: { rankedEmployees, topThree }
}
```

### Logic (step by step)

```
1. For each employee:
   a. Filter employee.activities by year (if not 'all')
   b. Filter remaining by quarter (if not 'all')
   c. Filter remaining by category (if not 'all')
   d. Sum points of filtered activities → employee.filteredTotal
   e. Count activities per category → publicSpeakingCount, educationCount

2. Filter employees array by searchQuery (case-insensitive name match)

3. Remove employees with filteredTotal === 0 (no qualifying activities)

4. Sort by filteredTotal descending

5. Assign rank (1-based index after sort)

6. Return:
   - rankedEmployees: full sorted list with rank + filtered data
   - topThree: first 3 items from rankedEmployees
```

### Return Object Shape

```javascript
{
  rankedEmployees: [
    {
      ...employee,          // original fields
      rank: 1,
      filteredTotal: 536,
      filteredActivities: [...],   // only matching activities
      publicSpeakingCount: 7,
      educationCount: 2,
    },
    // ...
  ],
  topThree: [/* same shape, first 3 items */]
}
```

---

## 5. Component Specifications

### 5.1 `Dropdown`

**Props:**
```typescript
{
  label: string;          // e.g. "All Years"
  options: { value: string; label: string }[];
  value: string;          // currently selected value
  onChange: (value: string) => void;
}
```

**Behavior:**
- Custom-built dropdown (not `<select>`), to match the original visual style.
- Click to open/close options list.
- Click outside closes the dropdown (use `useEffect` + document click listener).
- Selected option shown in trigger button with `▾` chevron icon.

### 5.2 `SearchInput`

**Props:**
```typescript
{
  value: string;
  onChange: (value: string) => void;
  onClear: () => void;
}
```

**Behavior:**
- Left: search icon (SVG or unicode `🔍`).
- Input fills available width.
- Right: `×` button rendered only when `value.length > 0`.
- `onClear` sets value to `""`.

### 5.3 `Podium`

**Props:**
```typescript
{
  topThree: RankedEmployee[];  // 0, 1, 2, or 3 items
}
```

**Behavior:**
- Renders nothing if `topThree.length === 0`.
- Order in DOM: position 2 (left), position 1 (center), position 3 (right).
- `PodiumSlot` at position 1 receives `isFirst={true}` for taller podium and gold ring.

### 5.4 `EmployeeCard`

**Props:**
```typescript
{
  employee: RankedEmployee;
  isExpanded: boolean;
  onToggle: (id: string) => void;
}
```

**Behavior:**
- Clicking anywhere on the card calls `onToggle(employee.id)`.
- When `isExpanded=true`, renders `<ActivityTable>` below the header row.
- Chevron icon rotates 180° when expanded (CSS transform).

### 5.5 `ActivityTable`

**Props:**
```typescript
{
  activities: Activity[];  // already filtered
}
```

- Sorts activities by date descending before rendering.
- Renders table header: `ACTIVITY | CATEGORY | DATE | POINTS`.
- Each row has a `<CategoryBadge>` in the category column.

### 5.6 `CategoryBadge`

**Props:**
```typescript
{
  category: "Education" | "Public Speaking" | "University Partners";
}
```

- Pill shape, gray background, dark text.
- No color differentiation between categories (all same gray style).

### 5.7 `EmptyState`

**Props:** none (stateless)

- Renders: `ℹ No activities found matching the current filters.`

---

## 6. Utility Functions (`src/utils/filters.js`)

```javascript
// Get quarter number (1-4) from a date string "DD-Mon-YYYY"
export function getQuarterFromDate(dateStr) { ... }

// Parse year from date string
export function getYearFromDate(dateStr) { ... }

// Filter activities by year/quarter/category
export function filterActivities(activities, { year, quarter, category }) { ... }

// Sort employees by total points descending
export function sortByPoints(employees) { ... }

// Case-insensitive name search
export function matchesSearch(employee, query) { ... }
```

---

## 7. CSS Strategy

- **CSS Modules** for all components — zero class name collisions.
- **CSS Custom Properties** (variables) in `index.css` for colors and spacing.
- **No CSS framework** (no Tailwind, no Bootstrap) — pixel-perfect control.
- **Media queries** inside each component's CSS module at `768px` breakpoint.

### Global CSS Variables (`index.css`)

```css
:root {
  --color-bg-page:        #f0f2f5;
  --color-bg-card:        #ffffff;
  --color-text-primary:   #1a1a2e;
  --color-text-secondary: #6b7280;
  --color-text-subtitle:  #5b8fa8;
  --color-accent-blue:    #2e86de;
  --color-podium-gold:    #f5e07a;
  --color-podium-silver:  #d4d4d4;
  --color-ring-gold:      #f0a500;
  --color-ring-silver:    #9e9e9e;
  --color-ring-bronze:    #8b6914;
  --color-badge-gray:     #e8e8e8;
  --shadow-card:          0 1px 4px rgba(0, 0, 0, 0.1);
  --border-radius-card:   8px;
  --border-radius-pill:   999px;
}
```

---

## 8. GitHub Pages Deployment

### `vite.config.js`

```javascript
export default defineConfig({
  base: '/leaderboard/',   // must match GitHub repo name
  plugins: [react()],
})
```

### `package.json` scripts

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "deploy": "npm run build && gh-pages -d dist"
  },
  "devDependencies": {
    "gh-pages": "^6.x"
  }
}
```

### Deploy Steps

```bash
npm run build        # outputs to /dist
npm run deploy       # pushes /dist to gh-pages branch
```

GitHub Pages serves from the `gh-pages` branch automatically once configured in repo Settings → Pages.
