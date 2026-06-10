# 📌 FASE5_CHECKLIST_INTEGRACION.md

## 🎯 Plan de Integración - Pasos Concretos

Este documento enumera exactamente dónde y cómo integrar los componentes UI nuevos en el proyecto existente.

---

## ✅ PASO 1: Verificar Instalación

**Comando:** 
```bash
npm install
```

**Verificar que en package.json existe:**
```json
"framer-motion": "^11.0.0"
```

---

## ✅ PASO 2: Imports Centralizados

En cualquier componente, importa así:
```jsx
// ❌ NO hacer esto
import Modal from '@/components/ui/Modal.jsx';

// ✅ HACER ESTO
import { Modal, Card, Button } from '@/components/ui';
```

---

## 📋 PASO 3: Reemplazos en Vistas Existentes

### **Vista: Dashboard / Home**
**Archivo:** `src/features/dashboard/pages/DashboardPage.jsx`

**Cambios:**
1. Reemplazar tarjetas antiguas con `<Card variant="hover_lift">`
2. Agregar `<SidebarLayout>` si no existe
3. Cambiar botones a `<Button variant="primary">`

**Antes:**
```jsx
<div className="p-6">
  <div className="bg-white p-4 rounded shadow">
    <h3>Tareas</h3>
    {tasks.length}
  </div>
</div>
```

**Después:**
```jsx
<SidebarLayout sidebar={<AppSidebar />}>
  <div className="p-6">
    <StatsGridExample />
  </div>
</SidebarLayout>
```

---

### **Vista: Tareas (Task List)**
**Archivo:** `src/features/tasks/pages/TaskListPage.jsx`

**Cambios:**
1. Agregar botón `+ Nueva Tarea` con `<Button>`
2. Mostrar tareas en grid con `<Card>`
3. Agregar `<Modal>` para crear/editar
4. Usar `<Badge>` para estados

**Componente a usar:** `CRUDTasksExample()` como referencia

---

### **Vista: Calificaciones**
**Archivo:** `src/features/grades/pages/GradesPage.jsx`

**Cambios:**
1. Tabla existente → `TasksTableExample()` pattern
2. Agregar `<Badge>` con color según nota
3. Botones de acción con `<Button variant="ghost" size="sm">`

---

### **Vista: Mensajes**
**Archivo:** `src/features/messages/pages/ConversationPage.jsx`

**Cambios:**
1. Usar `<Card>` para cada mensaje
2. Agregar `<Modal>` para nuevo mensaje
3. Agregar `<Button>` para enviar

---

### **Vista: Calendario**
**Archivo:** `src/features/calendar/pages/CalendarPage.jsx`

**Cambios:**
1. Eventos futuros en `<Card variant="hover_lift">`
2. Agregar `<Modal>` para crear evento
3. Usar `<Badge>` para tipo de evento

---

### **Vista: Administración (Multi-vistas)**
**Archivos:** `src/features/admin/pages/*.jsx`

**Cambios generales:**
1. Todas las tablas → `TasksTableExample()` pattern
2. Todos los botones → `<Button variant="primary">`
3. Confirmaciones destructivas → `ConfirmationModalExample()`
4. Agregar sidebar admin con `<SidebarLayout>`

**Ejemplo AdminStudentsPage:**
```jsx
// Antes: <button onClick={...}>Eliminar</button>
// Después:
<Button variant="danger" size="sm" onClick={...}>
  🗑️ Eliminar
</Button>
```

---

## 🏗️ PASO 4: Crear Sidebar Global (Opcional pero Recomendado)

**Archivo a crear:** `src/components/AppSidebar.jsx`

```jsx
import { SidebarMenu } from '@/components/ui';
import { useAuth } from '@/lib/hooks';
import { useNavigate } from 'react-router-dom';

export function AppSidebar() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'tasks', label: 'Mis Tareas', icon: '✓' },
    { id: 'grades', label: 'Calificaciones', icon: '📈' },
    // ... agregar según rol del usuario
  ];

  return (
    <div className="space-y-6 p-4 h-full flex flex-col">
      <h1 className="text-xl font-bold text-blue-600">🎓 Colegio</h1>
      
      <SidebarMenu 
        items={menuItems} 
        onSelect={(id) => navigate(`/${id}`)} 
      />

      {/* User section */}
      <div className="mt-auto pt-4 border-t border-gray-200">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-500 rounded-full text-white flex items-center justify-center text-xs">
            {user?.name?.[0]}
          </div>
          <div className="text-xs">
            <p className="font-bold">{user?.name}</p>
            <p className="text-gray-500">{user?.role}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
```

**Uso en App.jsx:**
```jsx
import { SidebarLayout } from '@/components/ui';
import { AppSidebar } from '@/components/AppSidebar';

function App() {
  return (
    <SidebarLayout sidebar={<AppSidebar />}>
      <Routes>
        <Route path="/dashboard" element={<DashboardPage />} />
        {/* ... más rutas */}
      </Routes>
    </SidebarLayout>
  );
}
```

---

## 🎨 PASO 5: Personalización de Colores (Opcional)

Si quieres agregar colores específicos del colegio, crea:

**Archivo:** `src/styles/theme.css`

```css
:root {
  --color-primary: #2563eb;      /* Azul actual */
  --color-secondary: #64748b;    /* Gris */
  --color-success: #16a34a;      /* Verde */
  --color-warning: #ea580c;      /* Naranja */
  --color-danger: #dc2626;       /* Rojo */
  
  /* Sobrescribir en Tailwind si es necesario */
}
```

---

## 🧪 PASO 6: Pruebas de Componentes

**Archivo de ejemplo:** `src/components/ui/Button.test.jsx`

```jsx
import { render, screen } from '@testing-library/react';
import { Button } from '@/components/ui';

describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<Button loading>Saving...</Button>);
    expect(screen.getByText('Saving...')).toBeInTheDocument();
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
```

---

## 📊 PASO 7: Migración Gradual

**No hacer TODO a la vez.** Prioridad:

1. **Semana 1:** Dashboard + Stats Grid
2. **Semana 2:** Task CRUD (Modal + Cards)
3. **Semana 3:** Sidebar + Admin
4. **Semana 4:** Animaciones adicionales + Polish

---

## 🔍 PASO 8: Validación de Cambios

Después de cada integración, verificar:

- [ ] El componente se renderiza sin errores
- [ ] Las animaciones funcionan suave (sin lag)
- [ ] Responsivo en mobile (usa DevTools)
- [ ] Los datos se cargan correctamente (React Query)
- [ ] Los estados de loading/error se muestran
- [ ] Los modales se cierran con ESC
- [ ] Los botones tienen feedback visual

---

## 🛠️ Comandos Útiles

```bash
# Desarrollo
npm run dev

# Build de prueba
npm run build

# Previsualización de build
npm run preview

# Tests
npm test
npm test:run

# Formateo (si tienes Prettier)
npm run format
```

---

## 📝 Checklist por Vistas

### DashboardPage
- [ ] Reemplazar contenedor con `<SidebarLayout>`
- [ ] Usar `<StatsGridExample />` para stats
- [ ] Cambiar botones a `<Button>`
- [ ] Probar en mobile

### TaskListPage
- [ ] Grid de tareas con `<Card variant="hover_lift">`
- [ ] Modal para crear con `<Modal>`
- [ ] Estados con `<Badge>`
- [ ] Tabla alternativa con `TasksTableExample()`

### AdminPages (Students, Courses, Grades, etc.)
- [ ] Tablas con acciones (`TasksTableExample()`)
- [ ] Confirmaciones destructivas (`ConfirmationModalExample()`)
- [ ] Botones primarios/secundarios/danger
- [ ] Sidebar admin (si no existe)

### ConversationPage (Messages)
- [ ] Cada mensaje en `<Card>`
- [ ] Modal para nuevo mensaje
- [ ] Botón enviar con loading

### CalendarPage
- [ ] Eventos próximos en `<Card>`
- [ ] Modal para crear evento
- [ ] `<Badge>` para tipo/importancia

---

## 💡 Tips Importantes

### 1. **No romper lo existente**
Primero crea copias de componentes, prueba, y luego reemplaza:
```bash
cp DashboardPage.jsx DashboardPage.old.jsx
# ... hacer cambios ...
```

### 2. **Aprovechar React Query**
Los componentes de ejemplo ya incluyen hooks:
```jsx
const { tasks, isLoading } = useTasks();
```

### 3. **Tailwind ya está disponible**
Todos los componentes usan clases Tailwind. Si falta algo:
```bash
npm ls tailwindcss
```

### 4. **Animaciones habilitadas por defecto**
Framer Motion está listo. Si es muy lento en algún dispositivo:
```jsx
<motion.div 
  animate={shouldAnimate}  // Control condicional
>
```

### 5. **Testing de componentes UI**
Cada componente debe testearse:
```bash
npm test components/ui/Modal.test.jsx
```

---

## 🎯 Próxima Sesión

1. Integrar Dashboard con `<StatsGridExample>`
2. Reemplazar botones antiguos por `<Button>`
3. Crear `AppSidebar` global
4. Validar en mobile

---

**Documento creado:** Fase 5 Integración
**Estado:** Listo para implementación
**Estimado:** 2-3 semanas para migración completa

