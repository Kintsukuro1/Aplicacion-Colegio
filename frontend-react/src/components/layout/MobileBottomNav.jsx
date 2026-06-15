import { NavLink } from 'react-router-dom';

const BOTTOM_NAV_ITEMS = [
  { to: '/dashboard', icon: 'IN', label: 'Inicio' },
  { to: '/estudiante/panel', icon: 'MI', label: 'Mi panel' },
  { to: '/apoderado/panel', icon: 'AP', label: 'Pupilos' },
  { to: '/profesor/clases', icon: 'CL', label: 'Clases' },
  { to: '/admin-escolar/estudiantes', icon: 'AL', label: 'Alumnos' },
  { to: '/admin-escolar/asistencias', icon: 'AS', label: 'Asistencia' },
  { to: '/calendario/eventos', icon: 'CA', label: 'Calendario' },
  { to: '/admin-escolar/calificaciones', icon: 'NO', label: 'Notas' },
];
const EMPTY_ROUTES = [];

export default function MobileBottomNav({ visibleRoutes = EMPTY_ROUTES }) {
  const visiblePaths = new Set(visibleRoutes.map((route) => route.to));
  const items = BOTTOM_NAV_ITEMS.filter((item) => visiblePaths.has(item.to));



  if (items.length === 0) {
    return null;
  }

  return (
    <nav className="mobile-bottom-nav" aria-label="Navegacion principal movil">
      {items.slice(0, 5).map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) => `bottom-nav-item${isActive ? ' active' : ''}`}
        >
          <span className="bottom-nav-icon">{item.icon}</span>
          <span className="bottom-nav-label">{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

function buildInitials(label) {
  const words = String(label || '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);
  return words.map((word) => word[0]).join('').toUpperCase() || 'IR';
}
