# Data Model — Leaderboard

All data is stored in a single static JSON file: `src/data/employees.json`.
No backend, no API calls — the app reads this file at build time.

---

## 1. Top-Level Structure

```json
{
  "employees": [ ...Employee[] ]
}
```

---

## 2. Employee Object

```typescript
interface Employee {
  id: string;           // Unique identifier, e.g. "emp_001"
  name: string;         // Full name, e.g. "Alex Johnson"
  avatar: string;       // Full URL to portrait image
  jobTitle: string;     // e.g. "Senior Software Engineer"
  department: string;   // Encoded department code, e.g. "US.U1.D1.G1"
  activities: Activity[];
}
```

### Field Rules

| Field | Format         | Example | Notes                                    |
|-------|----------------|---------|------------------------------------------|
| `id` | `"emp_NNN"`    | `"emp_001"` | Zero-padded, sequential                  |
| `name` | `"First Last"` | `"Alex Johnson"` | Fake names — no real persons             |
| `avatar` | Full URL       | `"https://randomuser.me/api/portraits/men/1.jpg"` | randomuser.me, gender-coded path         |
| `jobTitle` | String         | `"Lead QA Engineer"` | Fake titles, must be plausible           |
| `department` | String         | `"QA.AS.MANUAL.T1"` | Some Random Department Code |
| `activities` | Array          | `[...]` | May be empty array `[]`                  |

---

## 3. Activity Object

```typescript
interface Activity {
  id: string;            // Unique identifier, e.g. "act_001"
  title: string;         // Activity title with prefix, e.g. "[EDU] React Patterns"
  category: Category;    // One of three category values
  date: string;          // Display date, format "DD-Mon-YYYY"
  year: number;          // Numeric year for filtering, e.g. 2025
  quarter: number;       // 1 | 2 | 3 | 4 — derived from date month
  points: number;        // Positive integer, typical values: 8, 16, 32, 64
}

type Category = "Education" | "Public Speaking" | "University Partners";
```

### Field Rules

| Field | Format | Example | Notes |
|-------|--------|---------|-------|
| `id` | `"act_NNN"` | `"act_042"` | Globally unique across all employees |
| `title` | `"[PREFIX] Description"` | `"[EDU] GraphQL Workshop"` | See Title Prefixes |
| `category` | Enum string | `"Public Speaking"` | Exactly one of three values |
| `date` | `"DD-Mon-YYYY"` | `"16-Dec-2025"` | Month is 3-letter English abbreviation |
| `year` | Integer | `2025` | Must match year in `date` field |
| `quarter` | `1\|2\|3\|4` | `4` | Must match month in `date` field |
| `points` | Integer | `32` | See Points Scale |

### Title Prefixes by Category

| Category | Prefix | Example Title |
|----------|--------|---------------|
| `Public Speaking` | `[EDU]` | `[EDU] TypeScript Deep Dive` |
| `Education` | `[LAB]` | `[LAB] Mentoring of John Smith` |
| `University Partners` | `[UNI]` | `[UNI] Guest Lecture at Tech University` |

### Quarter ↔ Month Mapping

| Quarter | Months |
|---------|--------|
| `1` | January, February, March |
| `2` | April, May, June |
| `3` | July, August, September |
| `4` | October, November, December |

### Month Abbreviations for `date` Field

`Jan`, `Feb`, `Mar`, `Apr`, `May`, `Jun`, `Jul`, `Aug`, `Sep`, `Oct`, `Nov`, `Dec`

### Points Scale

| Points | Typical Activity Type |
|--------|----------------------|
| `8` | Short talk, quiz review |
| `16` | Standard presentation or quiz |
| `32` | Full technical session, digest |
| `64` | Mentoring engagement, long workshop |

---

## 4. Computed / Derived Fields (not stored in JSON)

These values are **calculated at runtime** by the app from the raw data:

| Derived Value | Formula |
|--------------|---------|
| `totalPoints` | `sum(employee.activities.map(a => a.points))` — filtered by active filters |
| `rank` | Position in array sorted by `totalPoints` descending — recalculated after filtering |
| `publicSpeakingCount` | `activities.filter(a => a.category === "Public Speaking").length` |
| `educationCount` | `activities.filter(a => a.category === "Education").length` |

---

## 5. Fake Data Generation Rules

### 5.1 Employee Count

Generate **20 employees** total. This is enough to show meaningful rankings and demonstrate filtering.

### 5.2 Name Generation

- Use common Western and Eastern European names (mix of genders).
- No real person's name from the original screenshots.
- Format: `"FirstName LastName"` — no middle names.

### 5.3 Avatar URLs

Use `https://randomuser.me/api/portraits/` — free, no auth required:

```
Men:   https://randomuser.me/api/portraits/men/{N}.jpg    (N = 1–99)
Women: https://randomuser.me/api/portraits/women/{N}.jpg  (N = 1–99)
```

Match gender of avatar to the name. Each employee gets a unique N value.

### 5.4 Job Titles

Use a mix of realistic software company roles:

```
Software Engineer
Senior Software Engineer
Lead Software Engineer
QA Engineer
Lead QA Engineer
Group Manager
HR Manager
Product Manager
DevOps Engineer
Data Engineer
Business Analyst
UX Designer
```

### 5.6 Activity Distribution

Each employee should have **between 5 and 15 activities** distributed across:
- Both years: 2024 and 2025
- All 4 quarters (not every quarter for every employee — natural variation)
- At least 2 different categories per employee

Point totals should create a **realistic spread** for interesting rankings:
- Top 3 employees: 400–600 points
- Middle tier: 200–400 points
- Lower tier: 50–200 points

### 5.7 Activity Titles (Public Speaking — `[EDU]`)

Generate 10–15 unique talk/presentation titles, e.g.:

```
[EDU] TypeScript Advanced Patterns
[EDU] Docker Fundamentals Workshop
[EDU] GraphQL Best Practices
[EDU] Clean Code Principles
[EDU] Node.js Performance Tuning
[EDU] React State Management
[EDU] CI/CD Pipeline Design
[EDU] Tech Interview Preparation
[EDU] Python for Backend Developers
[EDU] Microservices Architecture
[EDU] JavaScript News Digest
[EDU] API Security Essentials
[EDU] Database Indexing Strategies
[EDU] Agile Ceremonies Deep Dive
[EDU] Vue.js Crash Course
```

### 5.8 Activity Titles (Education — `[LAB]`)

```
[LAB] Mentoring of [Fake Name]
[LAB] Onboarding of [Fake Name]
```

Use first-name-only fake names for the mentored person.

### 5.9 Activity Titles (University Partners — `[UNI]`)

```
[UNI] Guest Lecture at State Technical University
[UNI] Career Fair Presentation
[UNI] Internship Program Introduction
[UNI] Workshop for Final Year Students
[UNI] Open Day Presentation
```

---

## 6. Full JSON Schema (for validation)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["employees"],
  "properties": {
    "employees": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "name", "avatar", "jobTitle", "department", "activities"],
        "properties": {
          "id":         { "type": "string", "pattern": "^emp_\\d+$" },
          "name":       { "type": "string", "minLength": 3 },
          "avatar":     { "type": "string", "format": "uri" },
          "jobTitle":   { "type": "string", "minLength": 2 },
          "department": { "type": "string", "pattern": "^[A-Z]+\\." },
          "activities": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["id", "title", "category", "date", "year", "quarter", "points"],
              "properties": {
                "id":       { "type": "string", "pattern": "^act_\\d+$" },
                "title":    { "type": "string", "pattern": "^\\[(EDU|LAB|UNI)\\] " },
                "category": { "type": "string", "enum": ["Education", "Public Speaking", "University Partners"] },
                "date":     { "type": "string", "pattern": "^\\d{2}-[A-Z][a-z]{2}-\\d{4}$" },
                "year":     { "type": "integer", "minimum": 2020 },
                "quarter":  { "type": "integer", "enum": [1, 2, 3, 4] },
                "points":   { "type": "integer", "minimum": 1 }
              }
            }
          }
        }
      }
    }
  }
}
```

---

## 7. Available Filter Values (derived from JSON)

The app **dynamically reads** available filter options from the data:

| Filter | How Derived |
|--------|-------------|
| Year options | `[...new Set(allActivities.map(a => a.year))].sort().reverse()` |
| Quarter options | Static: always Q1, Q2, Q3, Q4 |
| Category options | Static: always Education, Public Speaking, University Partners |
