# Frontend Project Structure

## Overview

The frontend is a **React + TypeScript** single-page application built with **Vite**, using **Material UI (MUI)** for components and a **dark theme** (subject to change). It communicates with the FastAPI backend via a typed API layer with **Zod** schema validation on all responses.

## Directory Structure

```
frontend/src/
├── main.tsx                              # Entry point — renders <App />
├── components/
│   ├── App/
│   │   └── App.tsx                       # Root component: ThemeProvider, CssBaseline, BrowserRouter, route definitions
│   ├── Login/
│   │   ├── Login.tsx                     # Login form with MUI Card, TextField, Alert
│   │   └── Login.scss                    # Login page layout (centering)
│   ├── DayCard/
│   │   ├── DayCard.tsx                   # Clickable card for a single day — shows date + room chips
│   │   └── DayCard.scss                  # Hover animation
│   ├── DayDetail/
│   │   ├── DayDetail.tsx                 # Day detail view — room statuses + SHAP feature bars
│   │   └── DayDetail.scss               # Feature row layout
│   ├── AnomaliesView/
│   │   └── AnomaliesView.tsx             # Anomaly stats cards + list of anomalous DayCards
│   ├── AllDaysView/
│   │   └── AllDaysView.tsx               # List of all DayCards
│   ├── SimulateView/
│   │   ├── SimulateView.tsx              # File upload (drag-and-drop) + live prediction results
│   │   └── SimulateView.scss             # Feature row layout
│   ├── EvaluationView/
│   │   └── EvaluationView.tsx            # Model performance metrics table
│   └── AuditView/
│       └── AuditView.tsx                 # Audit log table (admin only)
├── layouts/
│   └── DashboardLayout.tsx               # MUI AppBar + Tabs navigation + <Outlet />
├── routes/
│   └── ProtectedRoute.tsx                # Auth guard — redirects to /login if no token
├── api/
│   ├── client.ts                         # Generic fetch wrapper, token/role management (localStorage)
│   └── requests.ts                       # Typed API functions: login, getDays, getAnomalies, etc.
├── model/
│   ├── auth.ts                           # Zod schema + type for login response
│   ├── day.ts                            # Zod schemas + types for day summaries, room info, features
│   ├── evaluation.ts                     # Zod schema + type for evaluation metrics
│   ├── audit.ts                          # Zod schema + type for audit log entries
│   └── predict.ts                        # Zod schemas + types for predict request/response
└── utils/
    └── csv.ts                            # CSV parser with validation for sensor event files
```

## Design Philosophy

### 1. Component-per-folder

Each component lives in its own folder (`ComponentName/ComponentName.tsx`). If custom styling is needed beyond MUI's `sx` prop, a co-located `.scss` file is added. Components that are fully styled via MUI have no SCSS file — we only create SCSS when there's real styling to write.

### 2. Logic in TSX, styling in SCSS (when needed)

Component `.tsx` files contain all logic and MUI component composition, with no inline CSS. Styling is handled through:
- **MUI's `sx` prop** — for theme-aware styles (colors, spacing, responsive values)
- **SCSS files** — for structural layout that doesn't need theme tokens (flex rows, animations, widths)

### 3. No hardcoded colors

All colors come from the MUI theme. The app uses `createTheme({ palette: { mode: "dark" } })` and references tokens like `"error.main"`, `"success.main"`, `"background.default"`, `"divider"`, etc. This means switching themes (or adding light mode) requires zero component changes.

### 4. Typed API layer with Zod validation

Every API response is validated at runtime using Zod schemas defined in `model/`. The `requests.ts` functions call `Schema.parse(response)` which:
- Throws immediately if the backend returns unexpected data
- Provides inferred TypeScript types (via `z.infer<typeof Schema>`) so components get full type safety without manually maintained interfaces

### 5. Route-based navigation

The app uses `react-router-dom` with nested routes:
- `/login` — public, renders Login
- `/` — protected (requires token), wraps in DashboardLayout
  - `/anomalies`, `/anomalies/:date` — anomaly list and detail
  - `/days`, `/days/:date` — all days list and detail
  - `/simulate`, `/evaluation`, `/audit` — other views

The DashboardLayout provides the AppBar, tab navigation, and `<Outlet />` for child routes. The ProtectedRoute checks for a token and redirects to `/login` if absent.

### 6. Auth via localStorage

The token and role are stored in `localStorage` by the API client during login. The role determines which tabs are shown (admin gets the Audit Log tab). On logout or 401 response, both are cleared and the user is redirected to `/login`.

### 7. File upload with validation

The SimulateView uses `mui-file-upload`'s `FileDropzone` for drag-and-drop CSV uploads. The `utils/csv.ts` parser validates:
- File is not empty
- Lines match expected format (`date,time,sensor,state` or `time,sensor,state`)
- Time fields match `HH:MM` pattern
- Sensor and state fields are non-empty

Validation errors are shown as MUI `Alert` components. If no valid events are found, the API call is skipped entirely.

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `react` + `react-dom` | UI framework |
| `react-router-dom` | Client-side routing |
| `@mui/material` + `@emotion/react` + `@emotion/styled` | Component library + styling engine |
| `@mui/icons-material` | Material icons |
| `mui-file-upload` | Drag-and-drop file upload component |
| `zod` | Runtime schema validation + TypeScript type inference |
| `sass` | SCSS compilation |
| `typescript` | Type checking |
| `vite` | Build tool + dev server |
