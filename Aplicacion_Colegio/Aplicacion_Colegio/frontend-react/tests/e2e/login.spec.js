import { test, expect } from '@playwright/test';

test.describe('Login Flow', () => {
  test('should render login page', async ({ page }) => {
    await page.goto('/login');
    
    // Verificar que el formulario está presente
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should show error on invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    // Ingresar credenciales inválidas
    await page.fill('input[name="email"]', 'invalid@test.cl');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    
    // Esperar error
    await expect(page.locator('text=/error|invalido/i')).toBeVisible({ timeout: 5000 });
  });

  test('should redirect to dashboard on valid login', async ({ page }) => {
    await page.goto('/login');
    
    // Ingresar credenciales válidas
    await page.fill('input[name="email"]', 'admin@test.cl');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    // Esperar redirección a dashboard
    await page.waitForURL('/dashboard/**', { timeout: 10000 });
    expect(page.url()).toContain('/dashboard');
  });

  test('should have email and password fields', async ({ page }) => {
    await page.goto('/login');
    
    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');
    
    await expect(emailInput).toHaveAttribute('type', 'email');
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });
});
