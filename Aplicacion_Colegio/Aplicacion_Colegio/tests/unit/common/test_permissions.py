"""
Tests unitarios para permissions
"""
import pytest
from backend.common.utils.permissions import get_paginas_por_rol


class TestGetPaginasPorRol:
    """Tests para la función get_paginas_por_rol"""
    
    def test_paginas_admin(self):
        """Test: Retorna páginas correctas para admin"""
        paginas = get_paginas_por_rol('admin')
        
        assert isinstance(paginas, dict)
        assert 'inicio' in paginas
        assert 'gestionar_escuelas' in paginas
        assert 'perfil' in paginas
        assert paginas['inicio'] == 'compartido/inicio_modulos.html'
        assert paginas['gestionar_escuelas'] == 'admin/seleccionar_escuela.html'
    
    def test_paginas_admin_escolar(self):
        """Test: Retorna páginas correctas para admin_escolar"""
        paginas = get_paginas_por_rol('admin_escolar')
        
        assert isinstance(paginas, dict)
        assert 'inicio' in paginas
        assert 'mi_escuela' in paginas
        assert 'gestionar_estudiantes' in paginas
        assert 'gestionar_cursos' in paginas
        assert 'gestionar_asignaturas' in paginas
        assert paginas['gestionar_estudiantes'] == 'admin_escolar/gestionar_estudiantes.html'
    
    def test_paginas_profesor(self):
        """Test: Retorna páginas correctas para profesor"""
        paginas = get_paginas_por_rol('profesor')
        
        assert isinstance(paginas, dict)
        assert 'mis_clases' in paginas
        assert 'asistencia' in paginas
        assert 'notas' in paginas
        assert 'libro_clases' in paginas
        assert 'reportes' in paginas
        assert 'disponibilidad' in paginas
        assert paginas['mis_clases'] == 'profesor/mis_clases.html'
    
    def test_paginas_estudiante(self):
        """Test: Retorna páginas correctas para estudiante"""
        paginas = get_paginas_por_rol('estudiante')
        
        assert isinstance(paginas, dict)
        assert 'inicio' in paginas
        assert 'mis_clases' in paginas
        assert 'mis_notas' in paginas
        assert 'asistencia' in paginas
        assert paginas['mis_clases'] == 'estudiante/mis_clases.html'
        assert paginas['mis_notas'] == 'estudiante/mis_notas.html'
    
    def test_paginas_apoderado(self):
        """Test: Retorna páginas correctas para apoderado"""
        paginas = get_paginas_por_rol('apoderado')
        
        assert isinstance(paginas, dict)
        assert 'inicio' in paginas
        assert 'mis_pupilos' in paginas
        assert 'notas' in paginas
        assert 'asistencia' in paginas
        assert paginas['mis_pupilos'] == 'apoderado/mis_pupilos.html'
    
    def test_paginas_asesor_financiero(self):
        """Test: Retorna páginas correctas para asesor_financiero"""
        paginas = get_paginas_por_rol('asesor_financiero')
        
        assert isinstance(paginas, dict)
        assert 'dashboard_financiero' in paginas
        assert 'estados_cuenta' in paginas
        assert 'pagos' in paginas
        assert 'cuotas' in paginas
        assert 'becas' in paginas
        assert paginas['dashboard_financiero'] == 'asesor_financiero/dashboard.html'
    
    def test_rol_desconocido(self):
        """Test: Rol desconocido retorna diccionario vacío"""
        paginas = get_paginas_por_rol('rol_inexistente')
        
        assert isinstance(paginas, dict)
        assert len(paginas) == 0
    
    def test_rol_vacio(self):
        """Test: String vacío retorna diccionario vacío"""
        paginas = get_paginas_por_rol('')
        
        assert isinstance(paginas, dict)
        assert len(paginas) == 0
    
    def test_todos_roles_tienen_perfil(self):
        """Test: Todos los roles (excepto admin) tienen página de perfil"""
        roles = ['admin', 'admin_escolar', 'profesor', 'estudiante', 'apoderado', 'asesor_financiero']
        
        for rol in roles:
            paginas = get_paginas_por_rol(rol)
            assert 'perfil' in paginas, f"Rol {rol} no tiene página de perfil"
    
    def test_paginas_son_strings(self):
        """Test: Todas las páginas son strings con rutas válidas"""
        roles = ['admin', 'admin_escolar', 'profesor', 'estudiante', 'apoderado', 'asesor_financiero']
        
        for rol in roles:
            paginas = get_paginas_por_rol(rol)
            for nombre_pagina, ruta in paginas.items():
                assert isinstance(ruta, str), f"Ruta de {nombre_pagina} no es string"
                assert ruta.endswith('.html'), f"Ruta de {nombre_pagina} no termina en .html"
                assert '/' in ruta, f"Ruta de {nombre_pagina} no tiene carpeta"
