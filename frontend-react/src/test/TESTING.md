# Testing Conventions

This document defines the testing standards for the `frontend-react` project.

---

## Test Infrastructure

### Files

| File | Purpose |
|------|---------|
| `src/test/test-utils.jsx` | All shared helpers, mocks, and providers |
| `src/test/setupTests.js` | Global setup: API mock wiring + afterEach cleanup |
| `vitest.config.js` | Vitest configuration |
| `playwright.config.js` | Playwright E2E configuration |

### Exported Helpers

| Helper | Purpose |
|--------|---------|
| `setupUser(capabilities, extras)` | Set auth store with capabilities |
| `clearUser()` | Clear auth store (auto-handled in global afterEach) |
| `renderWithProviders(ui, options)` | Render with Router + QueryClient + Toast |
| `createDeferred()` | Create a controllable promise for loading states |
| `mockApiEndpoints(endpointMap)` | Set up `getMock` with URL pattern matching |
| `paginated(results, options)` | Build DRF paginated response |
| `getMock / postMock / patchMock / deleteMock` | API method spies |

---

## Component Architecture Rules

### The Container + Pure Pattern

```
Page (Container)          ← reads stores, calls hooks, handles mutations
  └── SubComponent (Pure) ← receives ONLY props, no stores
       └── SubComponent   ← receives ONLY props, no stores
```

### Rules

1. **Only `*Page.jsx` components access stores** (`useAuthStore`, `useNotificationStore`)
2. **Only `*Page.jsx` components call `useQuery` / `useMutation`**
3. **Sub-components (`*Table`, `*Form`, `*Grid`, `*Tab`)** are pure:
   - They receive data via props
   - They emit events via callback props (`onSubmit`, `onChange`, `onDelete`)
   - They never import stores or API clients
4. **`usePermissions(me)` is called in the Page**, results passed down as props

### ❌ Bad — Store in sub-component

```jsx
// AdminCoursesTable.jsx — DON'T DO THIS
import { useAuthStore } from '../../stores/useAuthStore';

export function AdminCoursesTable({ rows }) {
  const me = useAuthStore((s) => s.user); // ❌ store access in view
  const canEdit = me?.capabilities?.includes('COURSE_EDIT');
  // ...
}
```

### ✅ Good — Props only in sub-component

```jsx
// AdminCoursesTable.jsx — DO THIS
export function AdminCoursesTable({ rows, canUpdate, canDelete, onStartEdit, onDelete }) {
  // ✅ pure component, all data from props
}
```

---

## Test Writing Rules

### 1. Auth Setup

Use `setupUser()` from test-utils. **Never** call `useAuthStore` directly in tests.

```jsx
// ✅ Good
import { setupUser, renderWithProviders } from '../../test/test-utils';

beforeEach(() => {
  setupUser(['COURSE_VIEW', 'COURSE_CREATE']);
});

// ❌ Bad
import { useAuthStore } from '../../stores/useAuthStore';

beforeEach(() => {
  useAuthStore.getState().setUser({ capabilities: ['COURSE_VIEW'] });
});
```

### 2. Query Selectors Priority

Follow the Testing Library query priority:

```
1. getByRole()        ← buttons, checkboxes, headings
2. getByLabelText()   ← form inputs
3. getByTestId()      ← structural elements (titles, sections, tables)
4. getByText()        ← dynamic data content only
```

**Key rule**: Never assert against static UI copy with `getByText`. Use `data-testid` for:
- Page titles
- Section headings
- Summary grids
- Error/loading states

```jsx
// ✅ Good — structural elements by testid
expect(screen.getByTestId('admin-courses-title')).toBeInTheDocument();

// ✅ Good — dynamic data by text
expect(screen.getByText('5A')).toBeInTheDocument();

// ✅ Good — interactive elements by role
await user.click(screen.getByRole('button', { name: 'Crear' }));

// ❌ Bad — static UI copy by text (breaks if wording changes)
expect(screen.getByText('Admin Escolar: Cursos')).toBeInTheDocument();
```

### 3. Async Data Loading

Always use `findByText` or `waitFor` for content that depends on API responses:

```jsx
// ✅ Good
await screen.findByText('5A');

// ✅ Good
await waitFor(() => {
  expect(screen.getByText('5A')).toBeInTheDocument();
});

// ❌ Bad — data not loaded yet
expect(screen.getByText('5A')).toBeInTheDocument();
```

### 4. Loading States with Deferred Promises

Use `createDeferred()` to test loading → loaded transitions:

```jsx
import { createDeferred, renderWithProviders, getMock } from '../../test/test-utils';

it('shows loading then data', async () => {
  const deferred = createDeferred();
  getMock.mockReturnValue(deferred.promise);

  renderWithProviders(<MyPage />);

  // Assert loading state
  expect(screen.getAllByRole('status').length).toBeGreaterThan(0);

  // Resolve and assert loaded state
  await act(async () => { deferred.resolve(myData); });
  await screen.findByText('Expected Content');
});
```

### 5. FormOverlay Interactions

When testing forms inside `FormOverlay`, use `fireEvent.change` instead of `userEvent.type`:

```jsx
// ✅ Good — avoids auto-focus conflicts
await screen.findByRole('dialog');
fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: '6B' } });

// ❌ Bad — can conflict with overlay auto-focus
await user.type(screen.getByLabelText('Nombre'), '6B');
```

### 6. Test File Structure

```jsx
import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { renderWithProviders, setupUser, getMock, paginated } from '../../test/test-utils';
import MyPage from './MyPage';

describe('MyPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setupUser(['REQUIRED_CAPABILITY']);
  });

  it('renders data after loading', async () => {
    getMock.mockResolvedValue(paginated([{ id: 1, nombre: 'Test' }]));
    renderWithProviders(<MyPage />);
    await screen.findByText('Test');
  });
});
```

---

## data-testid Conventions

Format: `{feature}-{element}`

| Element | Pattern | Example |
|---------|---------|---------|
| Page title | `{feature}-title` | `admin-courses-title` |
| Summary section | `{feature}-summary` | `admin-courses-summary` |
| Main table | `{feature}-table` | `admin-courses-table` |
| Create/edit form | `{feature}-form` | `admin-courses-form` |
| Loading state | `{feature}-loading` | `admin-courses-loading` |
| Error state | `{feature}-error` | `admin-courses-error` |
| Empty state | `{feature}-empty` | `admin-courses-empty` |

---

## E2E Tests (Playwright)

Located in `tests/e2e/`. Require the backend to be running.

### Running

```bash
# All browsers
npx playwright test

# Single browser
npx playwright test --project=chromium

# Specific spec
npx playwright test tests/e2e/login.spec.js
```

### Helpers

Use `tests/e2e/helpers/auth.js` for shared login logic:

```js
import { loginAs } from './helpers/auth.js';

test('admin can view courses', async ({ page }) => {
  await loginAs(page, 'admin');
  await page.goto('/admin/cursos');
  await expect(page.getByTestId('admin-courses-title')).toBeVisible();
});
```
