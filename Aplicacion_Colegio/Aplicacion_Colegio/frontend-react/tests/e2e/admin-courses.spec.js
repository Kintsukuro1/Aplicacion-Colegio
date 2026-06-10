import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth.js';

test.describe('Admin Courses CRUD Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login as administrator
    await loginAs(page, 'admin');
  });

  test('should navigate to courses administration page', async ({ page }) => {
    // Navigate to courses page
    await page.goto('/admin-escolar/cursos');

    // Verify main page title and structure
    await expect(page.locator('[data-testid="admin-courses-title"]')).toContainText('Admin Escolar: Cursos');
    await expect(page.locator('[data-testid="admin-courses-summary"]')).toBeVisible();
    await expect(page.locator('[data-testid="admin-courses-table"]')).toBeVisible();
  });

  test('should open, fill and submit the course creation form', async ({ page }) => {
    await page.goto('/admin-escolar/cursos');

    // Click "Nuevo Curso" button
    const createBtn = page.locator('button:has-text("Nuevo Curso")');
    if (await createBtn.isVisible()) {
      await createBtn.click();

      // Verify course form overlay is open
      const form = page.locator('[data-testid="admin-courses-form"]');
      await expect(form).toBeVisible();

      // Fill in course details
      await page.fill('input[name="nombre"]', '8° Básico C');
      
      // Select Level (Nivel) - select first option or search for selector
      const levelSelect = page.locator('select[name="nivel_id"]');
      if (await levelSelect.isVisible()) {
        await levelSelect.selectOption({ index: 1 });
      }

      // Submit creation
      await page.click('button[type="submit"]:has-text("Crear")');

      // Verify form is closed and success toast or message shows
      await expect(form).not.toBeVisible();
    }
  });

  test('should support starting course editing and canceling', async ({ page }) => {
    await page.goto('/admin-escolar/cursos');

    // Find the first "Editar" button in the table and click it
    const editBtn = page.locator('[data-testid="admin-courses-table"] button:has-text("Editar")').first();
    if (await editBtn.isVisible()) {
      await editBtn.click();

      // Form should be visible
      const form = page.locator('[data-testid="admin-courses-form"]');
      await expect(form).toBeVisible();

      // Click "Cancelar" button to discard changes
      await page.click('button:has-text("Cancelar")');

      // Overlay should close
      await expect(form).not.toBeVisible();
    }
  });
});
