import { useMemo, useRef, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';

import { getUserRole } from '../../utils/capabilities';
import { useAuthStore } from '../../stores/useAuthStore';

const MODULE_ORDER = [
  'dashboard',
  'estudiante',
  'apoderado',
  'profesor',
  'admin-escolar',
  'calendario',
  'reuniones',
  'asesor-financiero',
  'coordinador-academico',
  'inspector-convivencia',
  'psicologo-orientador',
  'bibliotecario-digital',
  'soporte-tecnico',
  'seguridad',
  'pagos',
  'planes',
];
const EMPTY_ROUTES = [];

export function AppSidebar({ visibleRoutes = EMPTY_ROUTES, onLogout = () => {}, isOpen = false, onClose = () => {} }) {
  const location = useLocation();
  const user = useAuthStore((state) => state.user);
  const [expanded, setExpanded] = useState({});

  const activeModule = getRouteModule(location.pathname);
  const prevModuleRef = useRef(activeModule);

  if (activeModule !== prevModuleRef.current) {
    prevModuleRef.current = activeModule;
    setExpanded((current) => ({ ...current, [activeModule]: true }));
  }

  const menuGroups = useMemo(() => {
    const grouped = new Map();

    visibleRoutes.forEach((route) => {
      const module = route.path.split('/')[0] || 'dashboard';
      const current = grouped.get(module) || {
        id: module,
        label: getModuleLabel(module),
        icon: getModuleIcon(module),
        route: null,
        children: [],
      };

      if (route.path === module) {
        current.route = route;
      } else {
        current.children.push(route);
      }

      grouped.set(module, current);
    });

    return Array.from(grouped.values()).sort((a, b) => {
      const aIndex = MODULE_ORDER.indexOf(a.id);
      const bIndex = MODULE_ORDER.indexOf(b.id);
      if (aIndex !== -1 || bIndex !== -1) {
        return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
      }
      return a.label.localeCompare(b.label);
    });
  }, [visibleRoutes]);



  const role = getRoleDisplay(getUserRole(user));
  const displayName = user?.full_name || user?.user?.name || user?.email || 'Usuario';
  const schoolName = user?.school?.name || 'Colegio';

  return (
    <aside
      id="primary-sidebar"
      className={`app-sidebar${isOpen ? ' app-sidebar-visible' : ''}`}
      role="navigation"
      aria-label="Navegacion principal"
    >
      <div className="sidebar-content">
        <div className="sidebar-header">
          <div className="sidebar-logo-mark" aria-hidden="true">C</div>
          <div className="sidebar-brand">
            <h1>{schoolName}</h1>
            <span>Portal escolar</span>
          </div>
          <button type="button" className="sidebar-close-action" onClick={onClose} aria-label="Cerrar menu">
            X
          </button>
        </div>

        <nav className="sidebar-menu" aria-label="Secciones">
          {menuGroups.map((group) => {
            const isActive = activeModule === group.id;
            const hasChildren = group.children.length > 0;
            const isExpanded = Boolean(expanded[group.id]);
            const singleChild = !group.route && group.children.length === 1 ? group.children[0] : null;

            if ((!hasChildren && group.route) || singleChild) {
              const targetRoute = singleChild || group.route;
              return (
                <NavLink
                  key={group.id}
                  to={targetRoute.to}
                  className={({ isActive: linkActive }) => `sidebar-nav-link${linkActive ? ' active' : ''}`}
                  onClick={onClose}
                >
                  <span className="sidebar-nav-icon">{group.icon}</span>
                  <span>{targetRoute.label}</span>
                </NavLink>
              );
            }

            return (
              <div key={group.id} className={`sidebar-nav-group${isActive ? ' active' : ''}`}>
                <button
                  type="button"
                  className="sidebar-module-toggle"
                  onClick={() => setExpanded((current) => ({ ...current, [group.id]: !isExpanded }))}
                  aria-expanded={isExpanded}
                >
                  <span className="sidebar-nav-icon">{group.icon}</span>
                  <span className="sidebar-module-label">{group.label}</span>
                  <span className="sidebar-module-chevron" aria-hidden="true">&gt;</span>
                </button>

                <div className={`sidebar-submenu${isExpanded ? ' expanded' : ''}`}>
                  {group.route ? (
                    <NavLink
                      to={group.route.to}
                      className={({ isActive: linkActive }) => `sidebar-sub-link${linkActive ? ' active' : ''}`}
                      onClick={onClose}
                    >
                      {group.route.label}
                    </NavLink>
                  ) : null}
                  {group.children.map((route) => (
                    <NavLink
                      key={route.path}
                      to={route.to}
                      className={({ isActive: linkActive }) => `sidebar-sub-link${linkActive ? ' active' : ''}`}
                      onClick={onClose}
                    >
                      {route.label}
                    </NavLink>
                  ))}
                </div>
              </div>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="user-card">
            <div className="user-avatar" aria-hidden="true">{role.initials}</div>
            <div className="user-info">
              <p className="user-name">{displayName}</p>
              <p className="user-role">{role.label}</p>
            </div>
          </div>
          <button type="button" onClick={onLogout} className="logout-btn">
            Cerrar sesion
          </button>
        </div>
      </div>
    </aside>
  );
}

function getRouteModule(pathname) {
  const cleanPath = String(pathname || '').replace(/^\/+/, '');
  return cleanPath.split('/')[0] || 'dashboard';
}

function getRoleDisplay(role) {
  const labels = {
    administrador_general: { label: 'Administrador general', initials: 'AG' },
    administrador_escolar: { label: 'Administrador escolar', initials: 'AE' },
    admin_general: { label: 'Administrador general', initials: 'AG' },
    admin_escolar: { label: 'Administrador escolar', initials: 'AE' },
    profesor: { label: 'Profesor', initials: 'PR' },
    estudiante: { label: 'Estudiante', initials: 'ES' },
    alumno: { label: 'Estudiante', initials: 'ES' },
    apoderado: { label: 'Apoderado', initials: 'AP' },
    asesor_financiero: { label: 'Asesor financiero', initials: 'AF' },
    inspector_convivencia: { label: 'Inspector convivencia', initials: 'IC' },
    psicologo_orientador: { label: 'Psicologo orientador', initials: 'PO' },
    soporte_tecnico_escolar: { label: 'Soporte tecnico', initials: 'ST' },
    bibliotecario_digital: { label: 'Bibliotecario digital', initials: 'BD' },
    coordinador_academico: { label: 'Coordinador academico', initials: 'CA' },
  };
  return labels[role] || { label: 'Usuario', initials: 'US' };
}

function getModuleLabel(module) {
  const labels = {
    dashboard: 'Inicio',
    'admin-escolar': 'Administracion',
    profesor: 'Profesor',
    estudiante: 'Estudiante',
    apoderado: 'Apoderado',
    'asesor-financiero': 'Finanzas',
    'inspector-convivencia': 'Convivencia',
    'psicologo-orientador': 'Orientacion',
    'soporte-tecnico': 'Soporte',
    'bibliotecario-digital': 'Biblioteca',
    'coordinador-academico': 'Academico',
    calendario: 'Calendario',
    reuniones: 'Reuniones',
    seguridad: 'Seguridad',
    pagos: 'Pagos',
    planes: 'Planes',
  };
  return labels[module] || module.replace(/-/g, ' ');
}

function getModuleIcon(module) {
  const icons = {
    dashboard: 'IN',
    'admin-escolar': 'AD',
    profesor: 'PR',
    estudiante: 'ES',
    apoderado: 'AP',
    'asesor-financiero': 'FI',
    'inspector-convivencia': 'CO',
    'psicologo-orientador': 'OR',
    'soporte-tecnico': 'ST',
    'bibliotecario-digital': 'BI',
    'coordinador-academico': 'AC',
    calendario: 'CA',
    reuniones: 'RE',
    seguridad: 'SE',
    pagos: 'PA',
    planes: 'PL',
  };
  return icons[module] || 'MD';
}


