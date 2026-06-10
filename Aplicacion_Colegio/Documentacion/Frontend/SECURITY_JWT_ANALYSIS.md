# Análisis de Seguridad JWT - Frontend React

## Estado Actual

### Almacenamiento
- **Ubicación**: `localStorage`
- **Keys**: `ac_access_token`, `ac_refresh_token`
- **Módulo**: `src/lib/authStore.js`

### Riesgos Identificados

1. **XSS (Cross-Site Scripting)**
   - localStorage es accesible desde JavaScript
   - Un XSS attack puede exfiltrar tokens
   - Malware o scripts inyectados pueden acceder directamente

2. **CSRF (Cross-Site Request Forgery)**
   - Tokens en localStorage pueden ser usados sin protección CSRF adicional
   - Aunque TanStack Query lo mitiga parcialmente

3. **Token Expiration**
   - No hay validación de expiración en el frontend
   - El refresh token se usa, pero sin verificar timestamps
   - Token expirado puede causar errores de UX pobres

4. **Multi-Tab Desincronización**
   - Logout en una tab no afecta a otras
   - Un tab puede mantener token válido mientras otro hace logout

5. **PWA / Offline Mode**
   - Service Worker puede cachear requests con tokens
   - Offline mode no valida token fresco

## Propuestas de Mejora (En orden de implementación)

### Mejora 1: Validación de Expiración Local
**Impacto**: Bajo (no impide XSS, pero mejora UX)
**Esfuerzo**: Bajo (1-2 horas)
**Riesgo**: Mínimo

Decodificar el JWT en el frontend para validar `exp` claim:
```javascript
function isTokenExpired(token) {
  const payload = JSON.parse(atob(token.split('.')[1]));
  return Date.now() >= payload.exp * 1000;
}
```

### Mejora 2: Multi-Tab Sincronización
**Impacto**: Medio (previene inconsistencias)
**Esfuerzo**: Bajo (1 hora)
**Riesgo**: Bajo

Usar `storage` event para sincronizar logout entre tabs:
```javascript
window.addEventListener('storage', (e) => {
  if (e.key === 'ac_access_token' && e.newValue === null) {
    clearTokens(); // Logout en esta tab también
  }
});
```

### Mejora 3: Migración a HttpOnly Cookies (RECOMENDADO)
**Impacto**: Alto (previene XSS exfiltración)
**Esfuerzo**: Medio (4-6 horas)
**Riesgo**: Medio (requiere cambios backend)

Ventajas:
- No accesibles desde JavaScript
- Backend maneja automáticamente via HTTP headers
- Protege contra XSS token theft
- Compatible con CSRF tokens

Desventajas:
- Requiere soporte CORS y credenciales
- Requiere cambios en backend (Django)
- No funciona con localStorage fallback

**Decisión**: Implementar Mejora 1 y 2 ahora. Evaluar Mejora 3 con backend en siguiente fase.

### Mejora 4: Content Security Policy (CSP)
**Impacto**: Alto (reduce XSS risk)
**Esfuerzo**: Bajo (vite.config.js)
**Riesgo**: Bajo (pero puede romper scripts inline)

### Mejora 5: Refresh Token Rotation
**Impacto**: Alto (previene token replay)
**Esfuerzo**: Alto (requiere backend)
**Riesgo**: Alto (cambios en Django)

---

## Plan de Implementación (Esta fase)

1. ✓ Auditar estado actual
2. → Implementar Mejora 1: Validación de expiración
3. → Implementar Mejora 2: Multi-tab sync
4. → Reforzar CSP en Vite
5. → Documentar en React_Mejoras.md

---

## Notas para Backend

Para Mejora 3 (HttpOnly cookies), Django debe:
1. Usar `django-cors-headers` con `credentials`
2. Setear cookies con flags: `HttpOnly`, `Secure`, `SameSite=Lax`
3. Enviar CSRF token en headers o cookies separadas
4. Implementar refresh token rotation

Esto está fuera del scope actual (frontend), pero es prerequisito para seguridad máxima.
