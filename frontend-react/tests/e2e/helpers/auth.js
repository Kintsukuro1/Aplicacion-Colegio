import { expect } from '@playwright/test';

/**
 * Credentials for each role. These must match seed data in the Django backend.
 * Adjust these values to match your test environment.
 */
const CREDENTIALS = {
  admin: { email: 'admin@test.cl', password: 'password123' },
  profesor: { email: 'profesor@test.cl', password: 'password123' },
  estudiante: { email: 'estudiante@test.cl', password: 'password123' },
  apoderado: { email: 'apoderado@test.cl', password: 'password123' },
  coordinador: { email: 'coordinador@test.cl', password: 'password123' },
  inspector: { email: 'inspector@test.cl', password: 'password123' },
  bibliotecario: { email: 'bibliotecario@test.cl', password: 'password123' },
  psicologo: { email: 'psicologo@test.cl', password: 'password123' },
  soporte: { email: 'soporte@test.cl', password: 'password123' },
};

/**
 * Logs in as a given role and waits for the dashboard redirect.
 *
 * @param {import('@playwright/test').Page} page - Playwright page
 * @param {keyof typeof CREDENTIALS} role - One of the predefined roles
 * @param {Object} [options]
 * @param {boolean} [options.skipDashboardWait=false] - Skip waiting for dashboard redirect
 *
 * @example
 *   import { loginAs } from './helpers/auth.js';
 *
 *   test('admin flow', async ({ page }) => {
 *     await loginAs(page, 'admin');
 *     // now on /dashboard
 *   });
 */
export async function loginAs(page, role, { skipDashboardWait = false } = {}) {
  const creds = CREDENTIALS[role];
  if (!creds) {
    throw new Error(`Unknown role: "${role}". Available: ${Object.keys(CREDENTIALS).join(', ')}`);
  }

  await page.goto('/login');
  await page.fill('input[name="email"]', creds.email);
  await page.fill('input[name="password"]', creds.password);
  await page.click('button[type="submit"]');

  if (!skipDashboardWait) {
    await page.waitForURL('**/dashboard**', { timeout: 10000 });
    expect(page.url()).toContain('/dashboard');
  }
}

/**
 * Logs out by clearing localStorage and navigating to /login.
 *
 * @param {import('@playwright/test').Page} page
 */
export async function logout(page) {
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  await page.goto('/login');
}
