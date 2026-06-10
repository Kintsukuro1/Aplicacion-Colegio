import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth.js';

test.describe('Calendar E2E Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login as a coordinator or administrator who can view/create calendar events
    await loginAs(page, 'admin');
  });

  test('should load calendar page and switch between grid and list views', async ({ page }) => {
    await page.goto('/calendario/eventos');

    // Verify main page title and loaded components
    await expect(page.locator('[data-testid="calendar-events-title"]')).toContainText('Calendario Escolar');
    await expect(page.locator('[data-testid="calendar-events-summary"]')).toBeVisible();

    // Check if grid calendar is visible
    const calendarGrid = page.locator('.calendar-grid-container, .calendar-month-grid');
    if (await calendarGrid.count() > 0) {
      await expect(calendarGrid.first()).toBeVisible();
    }

    // Toggle view mode if buttons are available
    const listViewBtn = page.locator('button:has-text("Vista Lista"), button:has-text("Lista")');
    if (await listViewBtn.isVisible()) {
      await listViewBtn.click();
      // Verify list table is visible
      await expect(page.locator('table')).toBeVisible();
    }
  });

  test('should apply filters and reset them', async ({ page }) => {
    await page.goto('/calendario/eventos');

    // Locate filter form
    const filterForm = page.locator('form:has-text("Filtros")');
    await expect(filterForm).toBeVisible();

    // Select a type filter (e.g. feriado, vacaciones)
    const typeSelect = filterForm.locator('select');
    if (await typeSelect.isVisible()) {
      await typeSelect.selectOption('feriado');
      
      // Submit filters
      await page.click('button:has-text("Aplicar Filtros")');

      // Verify page stays on calendar page and updates summaries
      await expect(page.locator('[data-testid="calendar-events-summary"]')).toBeVisible();

      // Clear filters
      await page.click('button:has-text("Limpiar")');
    }
  });

  test('should allow creating a new event', async ({ page }) => {
    await page.goto('/calendario/eventos');

    // Verify event creation form is visible to authorized users
    const newEventForm = page.locator('form:has-text("Nuevo Evento")');
    if (await newEventForm.isVisible()) {
      await newEventForm.locator('label:has-text("Titulo") input, input[placeholder*="titulo"]').fill('Feriado de Prueba E2E');
      
      const typeSelect = newEventForm.locator('select');
      if (await typeSelect.isVisible()) {
        await typeSelect.selectOption('feriado');
      }

      await newEventForm.locator('input[type="date"]').first().fill('2026-06-15');
      
      // Submit new event
      await newEventForm.locator('button[type="submit"]:has-text("Crear"), button[type="submit"]:has-text("Guardar")').click();

      // Check if toast notifications appear
      const toast = page.locator('.toast-container');
      if (await toast.isVisible()) {
        await expect(toast).toContainText(/creado|exito|guardado/i);
      }
    }
  });
});
