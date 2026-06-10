import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth.js';

test.describe('Student Portal E2E Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login as a student
    await loginAs(page, 'estudiante');
  });

  test('should load student panel and navigate through tabs', async ({ page }) => {
    await page.goto('/estudiante/panel');

    // Verify main page title and summaries
    await expect(page.locator('[data-testid="student-self-title"]')).toContainText('Estudiante: Mi Panel');

    // 1. Verify Profile Tab (default) is visible
    await expect(page.locator('text=Mi Perfil')).toBeVisible();

    // 2. Click "Mis Clases" tab and verify classes view renders
    const classesTabBtn = page.locator('.tabs button:has-text("Mis Clases")');
    if (await classesTabBtn.isVisible()) {
      await classesTabBtn.click();
      // Mis Clases content should be visible (e.g. table or list of subjects)
      await expect(page.locator('table, .classes-grid, text=Horario')).toBeVisible();
    }

    // 3. Click "Mis Notas" tab
    const gradesTabBtn = page.locator('.tabs button:has-text("Mis Notas")');
    if (await gradesTabBtn.isVisible()) {
      await gradesTabBtn.click();
      // Mis Notas content should load (e.g. table of qualifications)
      await expect(page.locator('table, .grades-summary, text=Asignatura')).toBeVisible();
    }

    // 4. Click "Mi Asistencia" tab
    const attendanceTabBtn = page.locator('.tabs button:has-text("Mi Asistencia")');
    if (await attendanceTabBtn.isVisible()) {
      await attendanceTabBtn.click();
      // Mi Asistencia content should render (e.g. attendance percentage or logs)
      await expect(page.locator('.attendance-rate, text=Justificaciones, table')).toBeVisible();
    }

    // 5. Click "Historial Académico" tab
    const historyTabBtn = page.locator('.tabs button:has-text("Historial Académico")');
    if (await historyTabBtn.isVisible()) {
      await historyTabBtn.click();
      // Academic history should show
      await expect(page.locator('.history-records, table, text=Ciclo')).toBeVisible();
    }
  });
});
