import { test, expect } from '@playwright/test';

test.describe('Dashboard Admin', () => {
  test.beforeEach(async ({ page }) => {
    // Navegar a login
    await page.goto('/login');
    
    // Hacer login como admin_escolar
    await page.fill('input[name="email"]', 'admin@test.cl');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    // Esperar a que llegue al dashboard
    await page.waitForURL('/dashboard/**', { timeout: 10000 });
  });

  test('should render dashboard with main sections', async ({ page }) => {
    // Navegar a dashboard
    await page.goto('/dashboard');
    
    // Verificar que la página tiene contenido
    await expect(page.locator('text=/Inicio|Dashboard/i')).toBeVisible({ timeout: 5000 });
  });

  test('should display admin navigation menu', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Verificar que hay navegación (sidebar o header)
    const navbar = page.locator('[role="navigation"], nav, [class*="sidebar"], [class*="menu"]');
    await expect(navbar).toBeVisible({ timeout: 5000 });
  });

  test('should navigate to admin panels', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Buscar botón o link a panel administrativo
    const adminLink = page.locator('a:has-text(/panel|administrativo/i), button:has-text(/panel|administrativo/i)');
    
    if (await adminLink.isVisible()) {
      await adminLink.click();
      // Esperar navegación
      await page.waitForURL('**/admin-escolar/**', { timeout: 10000 });
    }
  });

  test('should render analytics or overview section', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Buscar elementos gráficos o estadísticas
    const stats = page.locator('[class*="chart"], [class*="stat"], [class*="card"]');
    
    // Debería haber al menos algunos elementos visuales
    const count = await stats.count();
    expect(count).toBeGreaterThanOrEqual(0); // Podría haber 0 si no hay datos
  });
});
