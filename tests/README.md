# 📋 Sistema de Tests - Aplicación Colegio

## 📁 Estructura de Tests

```
tests/
├── __init__.py                      # Inicialización del paquete de tests
├── run_all_tests.py                 # ⭐ Script principal para ejecutar tests
├── common/                          # Utilidades compartidas
│   ├── __init__.py
│   └── test_base.py                 # BaseTestCase con fixtures
├── estudiante/                      # Tests de módulo estudiante
│   ├── __init__.py
│   ├── test_estudiante_auth.py     # Autenticación y acceso
│   ├── test_estudiante_notas.py    # Visualización de notas
│   ├── test_estudiante_tareas.py   # Gestión de tareas
│   ├── test_estudiante_asistencia.py # Visualización de asistencia
│   └── test_estudiante_perfil.py   # Gestión de perfil
├── profesor/                        # Tests de módulo profesor
│   ├── __init__.py
│   ├── test_profesor_auth.py       # Autenticación y acceso
│   ├── test_profesor_clases.py     # Gestión de clases
│   ├── test_profesor_notas.py      # Ingreso de notas
│   └── test_profesor_asistencia.py # Registro de asistencia
└── administrador/                   # Tests de módulo administrador
    ├── __init__.py
    ├── test_admin_auth.py           # Autenticación y acceso
    ├── test_admin_estudiantes.py    # Gestión de estudiantes
    ├── test_admin_cursos.py         # Gestión de cursos
    └── test_admin_usuarios.py       # Gestión de usuarios
```

## 🚀 Cómo Ejecutar los Tests

### Ejecutar TODOS los tests
```bash
python tests/run_all_tests.py
```

### Ejecutar tests de un módulo específico
```bash
# Solo tests de estudiantes
python tests/run_all_tests.py estudiante

# Solo tests de profesores
python tests/run_all_tests.py profesor

# Solo tests de administradores
python tests/run_all_tests.py administrador
```

### Ejecutar con modo verbose (más detalle)
```bash
python tests/run_all_tests.py -v
python tests/run_all_tests.py estudiante -v
```

### Ejecutar tests individuales con Django
```bash
# Un archivo completo
python manage.py test tests.estudiante.test_estudiante_auth

# Una clase específica
python manage.py test tests.estudiante.test_estudiante_auth.EstudianteAuthTest

# Un test específico
python manage.py test tests.estudiante.test_estudiante_auth.EstudianteAuthTest.test_estudiante_puede_hacer_login
```

## 📊 Cobertura de Tests

### Módulo Estudiante (5 archivos, ~25 tests)
- ✅ Autenticación y control de acceso
- ✅ Visualización de notas con cálculo de promedios
- ✅ Gestión de tareas (ver, entregar, filtrar)
- ✅ Visualización de asistencia con porcentajes
- ✅ Gestión de perfil y actualización de datos

### Módulo Profesor (4 archivos, ~20 tests)
- ✅ Autenticación y control de acceso
- ✅ Gestión de clases y asignaturas
- ✅ Ingreso y edición de notas
- ✅ Registro de asistencia

### Módulo Administrador (4 archivos, ~20 tests)
- ✅ Autenticación y control de acceso
- ✅ Gestión completa de estudiantes
- ✅ Gestión de cursos y asignaturas
- ✅ Gestión de usuarios (profesores, apoderados)

## 🛠️ Clase Base: BaseTestCase

La clase `BaseTestCase` en `tests/common/test_base.py` proporciona:

### Fixtures Automáticos
- ✅ Institución de prueba
- ✅ Grupos de usuarios (Estudiantes, Profesores, Apoderados, Administradores)
- ✅ Curso de prueba

### Helper Methods
```python
# Crear usuarios de diferentes tipos
user, estudiante = self.crear_usuario_estudiante(username="...", email="...")
user, profesor = self.crear_usuario_profesor(username="...", email="...")
user, apoderado = self.crear_usuario_apoderado(username="...", email="...")
user, admin = self.crear_usuario_admin(username="...", email="...")

# Login
self.login_usuario(username)

# Assertions personalizadas
self.assertRedirectsToLogin(response)
```

## 📝 Ejemplo de Uso

```python
from tests.common.test_base import BaseTestCase

class MiNuevoTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Tu configuración adicional aquí
        self.user, self.estudiante = self.crear_usuario_estudiante()
        self.login_usuario(self.user.username)
    
    def test_algo(self):
        # Tu test aquí
        response = self.client.get('/alguna/url/')
        self.assertEqual(response.status_code, 200)
```

## 🎯 Buenas Prácticas

1. **Nombres descriptivos**: Los tests deben tener nombres que expliquen qué verifican
   ```python
   def test_estudiante_puede_ver_sus_notas(self):
   ```

2. **Un concepto por test**: Cada test debe verificar una sola cosa
   
3. **Usar fixtures**: Aprovechar los helpers de `BaseTestCase` para crear datos

4. **Limpiar después**: Django hace esto automáticamente con `TestCase`

5. **Tests independientes**: Cada test debe poder ejecutarse solo

## 📈 Interpretación de Resultados

El runner mostrará un resumen con colores:
- 🟢 **PASS** (verde): Test exitoso
- 🔴 **FAIL** (rojo): Assertion falló
- 🔴 **ERROR** (rojo): Excepción inesperada
- 🟡 **SKIP** (amarillo): Test omitido

### Ejemplo de salida:
```
======================================================================
  SISTEMA DE TESTS - APLICACIÓN COLEGIO
======================================================================

📋 Ejecutando TODOS los tests del sistema

..............................

======================================================================
  RESUMEN DE RESULTADOS
======================================================================

  Tests ejecutados: 65
  ✓ Exitosos: 63
  ✗ Fallidos: 2
  ✗ Errores: 0
  - Omitidos: 0

  Tasa de éxito: 96.9%

======================================================================
```

## 🐛 Debugging Tests Fallidos

Si un test falla:

1. **Lee el mensaje de error**: Indica qué assertion falló
2. **Revisa el traceback**: Muestra dónde ocurrió el error
3. **Ejecuta solo ese test**: Para iteración más rápida
   ```bash
   python manage.py test tests.estudiante.test_estudiante_notas.EstudianteNotasTest.test_calculo_promedio_correcto
   ```
4. **Usa print() o pdb**: Para debugging
   ```python
   print(f"DEBUG: {variable}")
   import pdb; pdb.set_trace()
   ```

## 🔄 Integración Continua

Para CI/CD, puedes ejecutar:

```bash
# Ejecutar tests y fallar si hay errores
python tests/run_all_tests.py || exit 1

# Con coverage
coverage run --source='.' tests/run_all_tests.py
coverage report
coverage html
```

## 📚 Próximos Pasos

- [ ] Agregar tests de integración (E2E)
- [ ] Configurar coverage.py para métricas de cobertura
- [ ] Tests de performance
- [ ] Tests de APIs (si se implementan)
- [ ] Tests de WebSockets (notificaciones en tiempo real)

## 💡 Tips

- Los tests usan una base de datos temporal que se elimina automáticamente
- Cada test tiene su propia transacción que se revierte
- Usa `@override_settings()` para cambiar configuración temporalmente
- Usa `@skip()` o `@skipIf()` para omitir tests temporalmente

---

**¿Preguntas?** Consulta la documentación de [Django Testing](https://docs.djangoproject.com/en/stable/topics/testing/)
