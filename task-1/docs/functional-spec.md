# Functional Specification — Leaderboard

## 1. Page Layout

The page has a light gray background (`#f0f2f5`) and a single main container (white card with rounded corners and subtle shadow) that holds all content.

### 1.1 Layout Sections (top to bottom)

```
┌─────────────────────────────────────────────────────┐
│  HEADER                                             │
│  Title + subtitle                                   │
├─────────────────────────────────────────────────────┤
│  FILTERS BAR                                        │
│  [Year ▾] [Quarter ▾] [Category ▾] [🔍 Search...]  │
├─────────────────────────────────────────────────────┤
│  PODIUM                                             │
│       [2]         [1]         [3]                   │
│    Name/score  Name/score  Name/score               │
│      ▓▓▓▓       ████        ░░░░                    │
├─────────────────────────────────────────────────────┤
│  RANKED LIST                                        │
│  1  [avatar]  Name / Title         🖥 N  🎓 N  ★ N  │
│  2  [avatar]  Name / Title         🖥 N  🎓 N  ★ N  │
│  ...                                                │
└─────────────────────────────────────────────────────┘
```

---

## 2. Header

| Property | Value |
|----------|-------|
| Title text | `Leaderboard` |
| Title style | Bold, ~28–32px, black |
| Subtitle text | `Top performers based on contributions and activity` |
| Subtitle style | Regular, ~14px, muted blue/teal (`#5b8fa8` or similar) |

---

## 3. Filters Bar

All four controls are inside a white rounded panel with shadow, sitting between the header and podium.

### 3.1 Year Dropdown

| Property | Value |
|----------|-------|
| Default label | `All Years` |
| Options | `All Years`, `2025`, `2024` |
| Behavior | Selecting a year filters all employee activity data to that year only. Rankings and counts recalculate. |

### 3.2 Quarter Dropdown

| Property | Value |
|----------|-------|
| Default label | `All Quarters` |
| Options | `All Quarters`, `Q1`, `Q2`, `Q3`, `Q4` |
| Behavior | Filters activities by calendar quarter. Quarter boundaries: Q1 = Jan–Mar, Q2 = Apr–Jun, Q3 = Jul–Sep, Q4 = Oct–Dec. |
| Dependency | Quarter filter is independent of Year filter — both apply simultaneously (AND logic). |

### 3.3 Category Dropdown

| Property | Value |
|----------|-------|
| Default label | `All Categories` |
| Options | `All Categories`, `Education`, `Public Speaking`, `University Partners` |
| Behavior | Filters activities by category. Only activities of the selected category count toward the total score. |

### 3.4 Search Input

| Property | Value |
|----------|-------|
| Placeholder | `Search employee...` |
| Left icon | Magnifying glass (🔍) |
| Right button | `×` clear button — visible only when input has text |
| Behavior | Case-insensitive substring match on employee full name. Filters the list and podium in real time on each keystroke. |
| Clear action | Clicking `×` resets search to empty, restoring full list. |

### 3.5 Filter Combination Rules

- All four filters apply simultaneously using **AND** logic.
- When a filter is set to its "All ..." default, it has no effect.
- The podium and ranked list both update when any filter changes.
- Rankings (position numbers) are recalculated from the filtered data set — not from original positions.
- If the filtered result is empty → show [Empty State](#8-empty-state).

---

## 4. Podium

Displays the top 3 employees from the **currently filtered** result set.

### 4.1 Visual Layout

```
Desktop:

         ┌──────────────┐
         │  [avatar]    │   ← 1st place (center, highest)
         │  ① badge     │
         │  Name        │
         │  Job title   │
         │  ★ score     │
         │              │
         │  ┌────────┐  │
    ┌──────────────────────┐
[avatar]  │  ████████  │  [avatar]
  ② badge │            │    ③ badge
  Name    │            │    Name
  Job     │     1      │    Job
  ★ score │            │    ★ score
          │            │
┌──────┐  │            │   ┌──────┐
│  2   │  └────────────┘   │  3   │
└──────┘                   └──────┘
```

- Position **1**: center column, podium block is **taller** than 2 and 3.
- Position **2**: left column.
- Position **3**: right column.

### 4.2 Avatar Styling per Position

| Position | Ring color | Badge background |
|----------|-----------|-----------------|
| 1 | Gold / orange (`#f0a500`) | Gold |
| 2 | Gray (`#9e9e9e`) | Dark gray / charcoal |
| 3 | Bronze/brown (`#8b6914`) | Bronze/brown |

- Avatar is a circle, ~80–90px diameter on desktop, ~70px on mobile.
- Badge (rank number) is a small filled circle overlaid at bottom-right of avatar.
- Avatar has a colored ring/border matching the badge color.

### 4.3 Podium Block Styling

| Position | Color |
|----------|-------|
| 1 | Warm yellow `#f5e07a` — gold |
| 2 | Light gray `#d4d4d4` — silver |
| 3 | Light gray `#d4d4d4` — silver (same as 2) |

- The "1" numeral is rendered in a slightly darker shade inside the gold block.
- Heights ratio approximately: 2 = 60%, 3 = 50%, 1 = 100% of max podium height.

### 4.4 Podium Edge Cases

| Scenario | Behavior |
|----------|----------|
| Filtered result has exactly 1 person | Only position 1 (center) is rendered |
| Filtered result has exactly 2 people | Positions 1 and 2 are rendered |
| Filtered result has 0 people | Podium is hidden entirely; Empty State shown |

---

## 5. Ranked List

Below the podium, all employees from the filtered result are shown as a scrollable list, sorted by **total points descending**.

### 5.1 Collapsed Card

```
┌──────────────────────────────────────────────────────────────────┐
│  [#]  [avatar]  Full Name                   🖥 N  🎓 N  │ TOTAL  │
│                 Job Title (DEPT.CODE)                   │ ★ NNN  ⌄│
└──────────────────────────────────────────────────────────────────┘
```

| Element | Description |
|---------|-------------|
| `#` | Rank number (1-based, recalculated from filter) |
| Avatar | Circle, ~48px, employee photo |
| Full Name | Bold, medium font |
| Job Title | Below name, smaller gray text |
| Department code | In parentheses after job title, e.g. `(BY.U1.D1.G2)` |
| 🖥 icon + count | Monitor icon + number of **Public Speaking** activities |
| 🎓 icon + count | Graduation cap icon + number of **Education** activities |
| `TOTAL` label | Small uppercase gray label above score |
| ★ score | Blue star icon + total points number |
| ⌄ chevron | Expand indicator (right side); rotates to ⌃ when expanded |

**Note:** The icon counts (🖥, 🎓) reflect only the **currently filtered** categories. When "Category = Education" is selected, only the 🎓 count is meaningful.

### 5.2 Expanded Card

Clicking a card (or the chevron) expands it to reveal the **Recent Activity** section below the header row.

```
┌──────────────────────────────────────────────────────────────────┐
│  [#]  [avatar]  Full Name                   🖥 N  🎓 N  │ TOTAL  │
│                 Job Title (DEPT.CODE)                   │ ★ NNN  ⌃│
├──────────────────────────────────────────────────────────────────┤
│  RECENT ACTIVITY                                                 │
│                                                                  │
│  ACTIVITY                    CATEGORY         DATE      POINTS  │
│  ─────────────────────────────────────────────────────────────  │
│  [EDU] Some title here       Public Speaking  16-Dec-25   +32   │
│  [LAB] Mentoring of Name     Education        17-Jun-25   +64   │
│  [UNI] University talk       University Part. 03-Mar-25   +16   │
└──────────────────────────────────────────────────────────────────┘
```

#### Activity Table Columns

| Column | Width | Content |
|--------|-------|---------|
| ACTIVITY | ~50% | Full activity title string |
| CATEGORY | ~20% | Category badge (pill) |
| DATE | ~18% | `DD-Mon-YYYY` format, e.g. `16-Dec-2025` |
| POINTS | ~12% | Blue bold text, e.g. `+32` |

#### Category Badge (Pill)

- Rounded pill shape
- Background: light gray `#e8e8e8`
- Text: dark gray, small font
- Examples: `Public Speaking`, `Education`, `University Partners`

#### Hover Behavior

When hovering over a category badge in the collapsed row icon area, a **tooltip** appears showing the category name (e.g., "Public Speaking").

### 5.3 Expand / Collapse Rules

- Only **one card** can be expanded at a time.
- Clicking an already-expanded card collapses it.
- Clicking a different card collapses the current and expands the new one.
- Filtering while a card is expanded: card remains expanded if the employee is still visible; collapses if the employee is filtered out.

### 5.4 Activity List in Expanded Card

- Activities shown are filtered by the **currently active** Year / Quarter / Category filters.
- Sorted by **date descending** (most recent first).
- No pagination — all matching activities are shown.

---

## 6. Responsive Behavior

### 6.1 Desktop (≥ 768px)

- Filters bar: all four controls on a **single row**.
- Podium: three columns side by side.
- List cards: full single-row layout.

### 6.2 Mobile (< 768px)

- Filters bar: each control on its **own row** (stacked vertically).
- Podium: same three-column layout but smaller avatars and text.
- List cards: condensed layout — icons and counts below the name, or compressed spacing.
- Expanded card activity table: columns may wrap or be abbreviated.

---

## 7. Tooltip

- Appears on hover over the icon area (🖥 / 🎓) in a list row.
- Shows the category name text, e.g. `Public Speaking`.
- Small floating label above the hovered element.
- No tooltip on mobile (hover not applicable).

---

## 8. Empty State

Shown when the combined filters produce **zero matching employees**.

```
┌──────────────────────────────────────────────────────────────────┐
│  ℹ  No activities found matching the current filters.            │
└──────────────────────────────────────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Icon | Info circle `ℹ` |
| Text | `No activities found matching the current filters.` |
| Background | Light gray, full width of list area |
| Podium | Hidden (not rendered) |

---

## 9. Interactions Summary

| User Action | Result |
|-------------|--------|
| Change Year filter | Recalculate totals, re-rank, update podium and list |
| Change Quarter filter | Same as year filter |
| Change Category filter | Same; also changes icon counts |
| Type in search | Live-filter employees by name match |
| Click `×` in search | Clear search text, restore full results |
| Click a filter dropdown | Show dropdown options list |
| Click outside dropdown | Close dropdown |
| Click list card | Expand / collapse card |
| Click chevron | Same as clicking card |
| Hover icon (desktop) | Show category tooltip |
