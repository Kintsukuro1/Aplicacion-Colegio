# Fase 5: UI/UX Nivel Producto - Guía Completa

## 📦 Componentes Creados

### 1. **Modal** (`components/ui/Modal.jsx`)
Diálogo modal reutilizable para CRUD, confirmaciones y forms.

**Props:**
```javascript
{
  isOpen: boolean,           // Mostrar/ocultar
  onClose: function,         // Callback al cerrar (ESC, overlay click)
  title: string,             // Título del modal
  children: JSX,             // Contenido principal
  footer: JSX,               // Botones de acción
  size: 'sm'|'md'|'lg'|'xl', // Tamaño (default: 'md')
  closeBtn: boolean,         // Mostrar botón X (default: true)
}
```

**Ejemplo:**
```jsx
import { Modal, Button } from '@/components/ui';
import { useState } from 'react';

function MyComponent() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setOpen(true)}>Abrir Modal</Button>
      
      <Modal
        isOpen={open}
        onClose={() => setOpen(false)}
        title="Crear Usuario"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button variant="primary" onClick={() => console.log('Guardar')}>
              Guardar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <input placeholder="Nombre" className="w-full px-3 py-2 border rounded" />
          <input placeholder="Email" className="w-full px-3 py-2 border rounded" />
        </div>
      </Modal>
    </>
  );
}
```

---

### 2. **Card** (`components/ui/Card.jsx`)
Componente de tarjeta con 3 variantes y header/body/footer.

**Variantes:**
- `default` - Neutral, sin hover
- `hover_lift` - Levanta en hover (clickeable)
- `interactive` - Click activo con feedback

**Subcomponentes:**
- `<Card>` - Contenedor principal
- `<CardHeader title="" subtitle="" icon="" />` - Encabezado
- `<CardBody>` - Contenido
- `<CardFooter>` - Acciones

**Ejemplo:**
```jsx
import { Card, CardHeader, CardBody, CardFooter, Button } from '@/components/ui';

function TaskCard() {
  return (
    <Card variant="hover_lift">
      <CardHeader 
        title="Mi Tarea" 
        subtitle="Entrega: 25 mayo"
        icon="✓"
      />
      <CardBody>
        Resumen de la tarea que debo entregar...
      </CardBody>
      <CardFooter>
        <Button variant="primary" size="sm">Entregar</Button>
      </CardFooter>
    </Card>
  );
}
```

---

### 3. **Badge** (`components/ui/Badge.jsx`)
Etiquetas para estados, categorías, filtros.

**Variantes:**
```
success, warning, error, info
gray, blue, green, red, yellow, purple
```

**Tamaños:** `sm` (pequeño), `md` (normal)

**Ejemplo:**
```jsx
import { Badge } from '@/components/ui';

<div className="space-y-2">
  <Badge variant="success">✓ Completado</Badge>
  <Badge variant="warning" dismissible onDismiss={handleDismiss}>
    ⚠️ Advertencia
  </Badge>
  <Badge variant="error" size="sm">✕ Error</Badge>
  <Badge icon="🔥" variant="purple">En Tendencia</Badge>
</div>
```

---

### 4. **Button** (`components/ui/Button.jsx`)
Botón reutilizable con estados y animaciones.

**Variantes:**
- `primary` - Azul, acción principal
- `secondary` - Gris, acción secundaria
- `danger` - Rojo, acciones destructivas
- `ghost` - Sin fondo, acciones sutiles

**Tamaños:** `sm`, `md`, `lg`

**Estados:** `loading`, `disabled`

**Ejemplo:**
```jsx
import { Button } from '@/components/ui';

<div className="flex gap-2">
  <Button variant="primary" onClick={handleSave}>
    Guardar
  </Button>
  <Button variant="secondary" disabled>
    Deshabilitado
  </Button>
  <Button variant="danger" loading>
    Eliminando...
  </Button>
  <Button variant="ghost" size="sm">
    Más opciones
  </Button>
</div>
```

---

### 5. **SidebarLayout** (`components/ui/SidebarLayout.jsx`)
Layout responsive con sidebar colapsable (desktop) o drawer (mobile).

**Props:**
```javascript
{
  children: JSX,                    // Contenido principal
  sidebar: JSX,                     // Contenido del sidebar
  mobileBreakpoint: 'sm'|'md'|'lg' // Punto de cambio (default: 'lg')
}
```

**Subcomponentes:**
- `<SidebarLayout>` - Contenedor
- `<SidebarMenu items={[]} />` - Menú

**Ejemplo:**
```jsx
import { SidebarLayout, SidebarMenu } from '@/components/ui';
import { useState } from 'react';

function Layout() {
  const [active, setActive] = useState('dashboard');

  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'tasks', label: 'Tareas', icon: '✓' },
    {
      id: 'messages',
      label: 'Mensajes',
      icon: '💬',
      children: [
        { id: 'inbox', label: 'Bandeja' },
        { id: 'archive', label: 'Archivo' },
      ],
    },
  ];

  const sidebar = (
    <div className="space-y-6 p-4">
      <h1 className="text-xl font-bold">🎓 Colegio</h1>
      <SidebarMenu items={menuItems} activeItem={active} onSelect={setActive} />
    </div>
  );

  return (
    <SidebarLayout sidebar={sidebar}>
      <div className="p-6">
        {/* Contenido por página aquí */}
      </div>
    </SidebarLayout>
  );
}
```

---

## 🎨 Sistema de Colores (Tailwind)

| Variante | Color | Uso |
|----------|-------|-----|
| `primary` | Blue-600 | Acciones principales |
| `secondary` | Gray-200 | Acciones secundarias |
| `success` | Green-100 | Estados completados |
| `warning` | Yellow-100 | Advertencias |
| `danger` | Red-600 | Eliminaciones |
| `ghost` | Transparent | Acciones sutiles |

---

## 🎬 Animaciones (Framer Motion)

### Modal
- **Entrada:** Fade + Scale + Y (spring animation)
- **Salida:** Fade + Scale + Y inverso
- **Overlay:** Fade suave

### Card
- **Entrada:** Fade + Y en 200ms
- **Hover:** Levanta 2px (variante hover_lift)

### Button
- **Hover:** Scale 1.02 suave
- **Click:** Scale 0.98 (feedback táctil)
- **Loading:** Rotación infinita del ícono

### Sidebar (Desktop)
- **Colapso:** Ancho animado (256px → 80px)
- **Submenu:** Height expand/collapse

### Sidebar (Mobile)
- **Drawer:** Slide desde izquierda
- **Overlay:** Fade

---

## 📱 Responsividad

### Breakpoints
- `sm`: 640px (móvil pequeño)
- `md`: 768px (tablet pequeña)
- `lg`: 1024px (tablet)
- `xl`: 1280px (desktop)

### Patrones
```jsx
// Mobile first
<div className="space-y-6 md:grid md:grid-cols-2 lg:grid-cols-3">
  <Card />
</div>

// Sidebar toggle automático en lg
<SidebarLayout mobileBreakpoint="lg">
  {/* Desktop: sidebar fijo, Mobile: drawer */}
</SidebarLayout>
```

---

## ✅ Patrones de Uso

### 1. **CRUD Modal + React Query**
```jsx
import { Modal, Button } from '@/components/ui';
import { useCreateUser } from '@/lib/hooks';
import { useState } from 'react';

function UserForm() {
  const [open, setOpen] = useState(false);
  const { mutate: createUser, isPending } = useCreateUser();

  return (
    <>
      <Button onClick={() => setOpen(true)}>+ Crear Usuario</Button>

      <Modal
        isOpen={open}
        onClose={() => setOpen(false)}
        title="Nuevo Usuario"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button
              variant="primary"
              loading={isPending}
              onClick={() => {
                createUser({...}, {
                  onSuccess: () => setOpen(false),
                });
              }}
            >
              Crear
            </Button>
          </>
        }
      >
        <input name="email" placeholder="email@ejemplo.com" />
      </Modal>
    </>
  );
}
```

### 2. **Grid de Cards**
```jsx
import { Card, CardHeader, CardBody } from '@/components/ui';

function TaskList({ tasks }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {tasks.map(task => (
        <Card key={task.id} variant="hover_lift">
          <CardHeader title={task.title} icon="✓" />
          <CardBody>{task.description}</CardBody>
        </Card>
      ))}
    </div>
  );
}
```

### 3. **Estado con Badge**
```jsx
<div className="flex items-center gap-2">
  <span>Tarea: Ensayo</span>
  {task.status === 'completed' && (
    <Badge variant="success">✓ Hecho</Badge>
  )}
  {task.dueDate < today && (
    <Badge variant="danger">Vencida</Badge>
  )}
</div>
```

---

## 📊 DashboardModernExample

Ejemplo completo que integra:
- SidebarLayout (responsive)
- Cards con datos reales (useTasks)
- Modales para acciones
- Badges para estados
- Buttons con loading
- Stats grid

**Ubicación:** `src/components/DashboardModernExample.jsx`

---

## 🔧 Próximos Pasos

1. **Adaptar componentes existentes**
   - Reemplazar FormOverlay con Modal
   - Reemplazar tarjetas antiguas con Card
   - Agregar SidebarLayout a rutas principales

2. **Crear más componentes especializados**
   - Input (con validación y error)
   - Select (dropdown)
   - Checkbox, Radio
   - Form (wrapper automático)
   - Pagination mejorada

3. **Tema personalizado**
   - Variables CSS para colores
   - Dark mode support
   - Sistema de tipografía escalable

4. **Documentación visual**
   - Storybook para component testing
   - Design system website
   - Ejemplo de cada variante

---

## 📦 Instalaciones

```bash
# Framer Motion ya agregado a package.json
npm install

# Desarrollo
npm run dev

# Build
npm run build
```

**Versiones instaladas:**
- `framer-motion@^11.0.0`
- `react@^18.3.1`
- `tailwindcss@^3.4.19`

---

**Estado:** ✅ Componentes base completados
**Siguiente:** Fase 5.2 - Componentes especializados (Input, Form, Select)

