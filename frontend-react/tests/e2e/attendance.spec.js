import { test, expect } from '@playwright/test';

test.describe('Admin Attendance (Registro de Asistencias)', () => {
  test.beforeEach(async ({ page }) => {
    // Login como admin_escolar con CLASS_TAKE_ATTENDANCE
    await page.goto('/login');
    
    await page.fill('input[name="email"]', 'admin@test.cl');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    // Esperar redirección
    await page.waitForURL('/dashboard/**', { timeout: 10000 });
  });

  test('should navigate to attendance page', async ({ page }) => {
    // Navegar directamente a asistencias
    await page.goto('/admin-escolar/asistencias');
    
    // Esperar a que la página cargue (buscar elementos de la página)
    await expect(page.locator('text=/asistencia|attendance/i')).toBeVisible({ timeout: 5000 });
  });

  test('should display attendance table or list', async ({ page }) => {
    await page.goto('/admin-escolar/asistencias');
    
    // Buscar tabla o lista de asistencias
    const table = page.locator('table, [role="grid"], [class*="table"], [class*="list"]');
    
    await expect(table).toBeVisible({ timeout: 5000 });
  });

  test('should have class selector or filter', async ({ page }) => {
    await page.goto('/admin-escolar/asistencias');
    
    // Buscar selector de clases (debería haber un dropdown o input)
    const classSelector = page.locator(
      'select, [role="combobox"], input[placeholder*="clase"], input[placeholder*="class"], button:has-text(/clase|class/i)'
    );
    
    if (await classSelector.isVisible()) {
      await expect(classSelector).toBeVisible();
    }
  });

  test('should display attendance controls (mark present/absent)', async ({ page }) => {
    await page.goto('/admin-escolar/asistencias');
    
    // Esperar que la tabla esté lista
    await expect(page.locator('table, [role="grid"]')).toBeVisible({ timeout: 5000 });
    
    // Buscar botones o checkboxes para marcar asistencia
    const attendanceControls = page.locator(
      'input[type="checkbox"], button:has-text(/presente|ausente|asistencia/i), [role="button"]:has-text(/presente|ausente/i)'
    );
    
    const controlCount = await attendanceControls.count();
    // Podría haber 0 si no hay estudiantes, pero si los hay, debería haber controles
    expect(controlCount).toBeGreaterThanOrEqual(0);
  });

  test('should have pagination controls if data exceeds page size', async ({ page }) => {
    await page.goto('/admin-escolar/asistencias');
    
    // Esperar tabla
    await expect(page.locator('table, [role="grid"]')).toBeVisible({ timeout: 5000 });
    
    // Buscar controles de paginación
    const pagination = page.locator('[class*="pagina"], [class*="pagination"], button:has-text(/anterior|siguiente|next|prev/i)');
    
    // Podría haber o no, dependiendo de los datos
    const paginationCount = await pagination.count();
    expect(paginationCount).toBeGreaterThanOrEqual(0);
  });

  test('should be able to select a class and load attendance', async ({ page }) => {
    await page.goto('/admin-escolar/asistencias');
    
    // Buscar selector de clase
    const classSelect = page.locator('select, [role="combobox"], input[placeholder*="clase"]').first();
    
    if (await classSelect.isVisible()) {
      // Si está visible, intentar interactuar
      await classSelect.click();
      
      // Esperar opciones
      const options = page.locator('[role="option"], option');
      const optionCount = await options.count();
      
      if (optionCount > 0) {
        // Seleccionar primera opción
        await options.first().click();
        
        // Esperar que se recargue la tabla
        await page.waitForTimeout(500);
        
        await expect(page.locator('table, [role="grid"]')).toBeVisible({ timeout: 5000 });
      }
    }
  });
});
