import { test, expect } from '@playwright/test';
import { loginAs, logout } from './helpers/auth.js';

test.describe('Role-based Access Control (RBAC) E2E Flow', () => {
  test('should allow student to access student portal but deny admin portal', async ({ page }) => {
    // 1. Login as student
    await loginAs(page, 'estudiante');

    // Can access student panel
    await page.goto('/estudiante/panel');
    await expect(page.locator('[data-testid="student-self-title"]')).toBeVisible();

    // Cannot access admin courses
    await page.goto('/admin-escolar/cursos');
    // Should be redirected or show unauthorized message
    await expect(page.locator('text=No tienes permisos|acceso denegado|unauthorized/i')).toBeVisible({ timeout: 5000 });

    await logout(page);
  });

  test('should allow admin to access admin portals but deny student portal', async ({ page }) => {
    // 2. Login as admin
    await loginAs(page, 'admin');

    // Can access admin courses
    await page.goto('/admin-escolar/cursos');
    await expect(page.locator('[data-testid="admin-courses-title"]')).toBeVisible();

    // Cannot access student panel
    await page.goto('/estudiante/panel');
    // Should be redirected or show unauthorized/lack of permission message
    await expect(page.locator('text=No tienes permisos|acceso denegado|unauthorized/i')).toBeVisible({ timeout: 5000 });

    await logout(page);
  });

  test('should restrict coordinators to coordinator panel', async ({ page }) => {
    // 3. Login as coordinator
    await loginAs(page, 'coordinador');

    // Can access coordinator panel
    await page.goto('/coordinador-academico/panel');
    await expect(page.locator('text=Panel academico|Coordinador Académico/i')).toBeVisible();

    // Cannot access student panel
    await page.goto('/estudiante/panel');
    await expect(page.locator('text=No tienes permisos|acceso denegado|unauthorized/i')).toBeVisible();

    await logout(page);
  });
});
