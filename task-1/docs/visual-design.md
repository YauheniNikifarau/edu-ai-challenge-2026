# Visual Design Specification — Leaderboard

## 1. Color Palette

### 1.1 Base Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `--color-bg-page` | `#f0f2f5` | Page background |
| `--color-bg-card` | `#ffffff` | Cards, panels, filter bar |
| `--color-bg-empty` | `#f5f5f5` | Empty state background |
| `--color-border` | `#e5e7eb` | Card borders, table dividers |

### 1.2 Text Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `--color-text-primary` | `#111827` | Employee names, headings, body |
| `--color-text-secondary` | `#6b7280` | Job titles, dept. codes, table headers |
| `--color-text-subtitle` | `#4b92c8` | Page subtitle under "Leaderboard" |
| `--color-text-muted` | `#9ca3af` | TOTAL label, minor labels |

### 1.3 Accent Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `--color-accent-blue` | `#2e86de` | Star icons, total score, points `+N`, icon counts |
| `--color-accent-blue-dark` | `#1a6bb5` | Hover state on blue elements |

### 1.4 Podium Colors

| Token | Hex | Position | Usage |
|-------|-----|----------|-------|
| `--color-podium-gold` | `#f5e07a` | 1st | Podium block fill |
| `--color-podium-gold-text` | `#c9a200` | 1st | Numeral "1" inside block |
| `--color-podium-silver` | `#d4d4d4` | 2nd | Podium block fill |
| `--color-podium-silver-text` | `#a0a0a0` | 2nd | Numeral "2" inside block |
| `--color-podium-bronze` | `#d4d4d4` | 3rd | Podium block fill (same as silver) |
| `--color-podium-bronze-text` | `#a0a0a0` | 3rd | Numeral "3" inside block |

### 1.5 Avatar Ring Colors

| Token | Hex | Position |
|-------|-----|----------|
| `--color-ring-gold` | `#f0a500` | 1st place |
| `--color-ring-silver` | `#9e9e9e` | 2nd place |
| `--color-ring-bronze` | `#8b6914` | 3rd place |

### 1.6 Badge / Pill Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `--color-badge-bg` | `#e8e8e8` | Category badge background |
| `--color-badge-text` | `#374151` | Category badge text |
| `--color-rank-badge-1` | `#f0a500` | Rank badge for 1st |
| `--color-rank-badge-2` | `#6b7280` | Rank badge for 2nd |
| `--color-rank-badge-3` | `#8b6914` | Rank badge for 3rd |

---

## 2. Typography

### 2.1 Font

- **Font family:** System UI stack — `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- No custom font download required.

### 2.2 Type Scale

| Role | Size | Weight | Color |
|------|------|--------|-------|
| Page title ("Leaderboard") | `28–32px` | `700` | `--color-text-primary` |
| Page subtitle | `14px` | `400` | `--color-text-subtitle` |
| Filter label (in dropdown trigger) | `14px` | `400` | `--color-text-primary` |
| Employee name (list) | `15px` | `600` | `--color-text-primary` |
| Job title (list) | `13px` | `400` | `--color-text-secondary` |
| Employee name (podium) | `15px` | `700` | `--color-text-primary` |
| Job title (podium) | `12px` | `400` | `--color-text-secondary` |
| Total score number | `18–20px` | `700` | `--color-accent-blue` |
| TOTAL label | `10px` | `500` | `--color-text-muted` (uppercase) |
| Icon count (🖥 N) | `14px` | `400` | `--color-text-secondary` |
| Table header (ACTIVITY etc.) | `11px` | `600` | `--color-text-secondary` (uppercase) |
| Activity title (table row) | `14px` | `400` | `--color-text-primary` |
| Date (table row) | `13px` | `400` | `--color-text-secondary` |
| Points (table row) | `14px` | `700` | `--color-accent-blue` |
| Category badge text | `12px` | `400` | `--color-badge-text` |

---

## 3. Spacing & Sizing

### 3.1 Layout

| Element | Value |
|---------|-------|
| Page max-width | `1200px` (centered) |
| Page horizontal padding | `24px` desktop / `16px` mobile |
| Page vertical padding (top/bottom) | `32px` desktop / `16px` mobile |
| Main card border-radius | `12px` |
| Main card padding | `32px` desktop / `16px` mobile |

### 3.2 Filters Bar

| Element | Value |
|---------|-------|
| Filters panel padding | `16px 20px` |
| Filters panel border-radius | `8px` |
| Gap between filter controls (desktop) | `8px` |
| Dropdown min-width | `140px` |
| Dropdown height | `36px` |
| Dropdown border-radius | `6px` |
| Dropdown border | `1px solid #d1d5db` |
| Search input height | `36px` |
| Search input border-radius | `6px` |

### 3.3 Podium

| Element | Value |
|---------|-------|
| Podium section vertical padding | `40px 0 0 0` |
| Avatar diameter (1st) | `90px` desktop / `70px` mobile |
| Avatar diameter (2nd, 3rd) | `72px` desktop / `56px` mobile |
| Avatar ring width | `3px` |
| Rank badge diameter | `24px` |
| Rank badge font size | `13px` |
| Gap between name and score | `8px` |
| Podium block height (1st) | `120px` |
| Podium block height (2nd) | `72px` |
| Podium block height (3rd) | `60px` |
| Podium block min-width | `160px` desktop / `100px` mobile |
| Numeral font size inside block | `48px` |

### 3.4 List Cards

| Element | Value |
|---------|-------|
| Card padding | `16px 20px` |
| Card border-radius | `8px` |
| Card border | `1px solid #e5e7eb` |
| Gap between cards | `4px` |
| Avatar diameter | `44px` |
| Avatar border-radius | `50%` |
| Rank number width | `32px` |
| Gap: avatar → text | `12px` |
| Icon size (🖥, 🎓) | `16px` |
| Gap between icon groups | `16px` |
| Divider between icons and TOTAL | `1px solid #e5e7eb` vertical |
| Chevron size | `20px` |

### 3.5 Activity Table (Expanded)

| Element | Value |
|---------|-------|
| Table top margin | `16px` |
| Section label "RECENT ACTIVITY" font-size | `11px` uppercase, letter-spacing |
| Table header row padding | `8px 0` |
| Table row padding | `14px 0` |
| Table row bottom border | `1px solid #f3f4f6` |
| Badge padding | `3px 10px` |

---

## 4. Shadows & Borders

| Element | Value |
|---------|-------|
| Main white card shadow | `0 1px 4px rgba(0, 0, 0, 0.08)` |
| Filter bar shadow | `0 1px 3px rgba(0, 0, 0, 0.06)` |
| Dropdown menu shadow | `0 4px 12px rgba(0, 0, 0, 0.12)` |
| Expanded card outline | `2px solid #2e86de` (highlight border) |

---

## 5. Responsive Breakpoints

| Breakpoint | Width | Changes |
|------------|-------|---------|
| Desktop | `≥ 768px` | Filters in one row; list cards full layout |
| Mobile | `< 768px` | Filters stacked vertically (each on own row); compact card layout |

### Mobile-specific changes

- Filters: each `<Dropdown>` and `<SearchInput>` takes full width, stacked.
- Podium avatars: smaller (see Podium sizing above).
- List cards: activity icon counts may move below name line.
- Expanded card table: columns may truncate or stack differently.
- No tooltips (hover state not applicable on touch).

---

## 6. Icon Specifications

| Icon | Purpose | Suggested Source |
|------|---------|-----------------|
| Monitor / screen | Public Speaking count | SVG inline or Heroicons `computer-desktop` |
| Graduation cap | Education count | SVG inline or Heroicons `academic-cap` |
| Star (★) | Total points | SVG inline (filled star) or `★` character |
| Chevron down/up | Expand/collapse | SVG inline or `▾`/`▴` characters |
| Magnifying glass | Search | SVG inline |
| × (cross) | Clear search | `×` character or SVG |
| Info circle (ℹ) | Empty state | SVG inline or `ℹ` character |

All icons should be the **same blue** as the accent color (`#2e86de`) when used with scores/counts, or **gray** (`#9ca3af`) when used as UI controls (chevron, search icon).

---

## 7. Animation / Transition

| Element | Transition |
|---------|-----------|
| Card expand/collapse | `max-height` transition or `height` animation, `200ms ease` |
| Chevron rotation | `transform: rotate(180deg)`, `200ms ease` |
| Dropdown open/close | Fade-in `opacity 150ms ease` |
| Filter dropdown items on hover | Background color `100ms ease` |
