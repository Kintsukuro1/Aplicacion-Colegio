#!/usr/bin/env python
"""
Script principal para ejecutar todos los tests del sistema
Uso:
    python tests/run_all_tests.py                    # Ejecutar todos los tests
    python tests/run_all_tests.py estudiante        # Solo tests de estudiante
    python tests/run_all_tests.py profesor          # Solo tests de profesor
    python tests/run_all_tests.py administrador     # Solo tests de administrador
    python tests/run_all_tests.py -v                # Modo verbose
"""
import os
import sys
import django
import unittest
from io import StringIO

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.apps.core.settings')
django.setup()


class ColoredTextTestResult(unittest.TextTestResult):
    """Result class con colores para mejor visualización"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.success_count = 0
    
    def addSuccess(self, test):
        super().addSuccess(test)
        self.success_count += 1
        if self.showAll:
            self.stream.writeln(f"\033[92m✓ PASS\033[0m")
        elif self.dots:
            self.stream.write('\033[92m.\033[0m')
            self.stream.flush()
    
    def addError(self, test, err):
        super().addError(test, err)
        if self.showAll:
            self.stream.writeln(f"\033[91m✗ ERROR\033[0m")
        elif self.dots:
            self.stream.write('\033[91mE\033[0m')
            self.stream.flush()
    
    def addFailure(self, test, err):
        super().addFailure(test, err)
        if self.showAll:
            self.stream.writeln(f"\033[91m✗ FAIL\033[0m")
        elif self.dots:
            self.stream.write('\033[91mF\033[0m')
            self.stream.flush()
    
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        if self.showAll:
            self.stream.writeln(f"\033[93m- SKIP: {reason}\033[0m")
        elif self.dots:
            self.stream.write('\033[93ms\033[0m')
            self.stream.flush()


class ColoredTextTestRunner(unittest.TextTestRunner):
    """Runner con resultados coloreados"""
    resultclass = ColoredTextTestResult


def discover_tests(module_name=None, verbose=False):
    """Descubre y carga los tests"""
    loader = unittest.TestLoader()
    
    if module_name:
        # Cargar tests de un módulo específico
        test_dir = os.path.join(os.path.dirname(__file__), module_name)
        if not os.path.exists(test_dir):
            print(f"\033[91mError: Módulo '{module_name}' no encontrado\033[0m")
            print(f"Módulos disponibles: estudiante, profesor, administrador, common")
            sys.exit(1)
        suite = loader.discover(start_dir=test_dir, pattern='test_*.py')
    else:
        # Cargar todos los tests
        suite = loader.discover(start_dir=os.path.dirname(__file__), pattern='test_*.py')
    
    return suite


def print_header():
    """Imprime el encabezado del script"""
    print("\n" + "="*70)
    print("  SISTEMA DE TESTS - APLICACIÓN COLEGIO")
    print("="*70 + "\n")


def print_summary(result):
    """Imprime un resumen de los resultados"""
    print("\n" + "="*70)
    print("  RESUMEN DE RESULTADOS")
    print("="*70)
    print(f"\n  Tests ejecutados: {result.testsRun}")
    print(f"  \033[92m✓ Exitosos: {result.success_count}\033[0m")
    print(f"  \033[91m✗ Fallidos: {len(result.failures)}\033[0m")
    print(f"  \033[91m✗ Errores: {len(result.errors)}\033[0m")
    print(f"  \033[93m- Omitidos: {len(result.skipped)}\033[0m")
    
    # Calcular porcentaje de éxito
    if result.testsRun > 0:
        success_rate = (result.success_count / result.testsRun) * 100
        if success_rate == 100:
            color = '\033[92m'  # Verde
        elif success_rate >= 80:
            color = '\033[93m'  # Amarillo
        else:
            color = '\033[91m'  # Rojo
        print(f"\n  Tasa de éxito: {color}{success_rate:.1f}%\033[0m")
    
    print("\n" + "="*70 + "\n")


def main():
    """Función principal"""
    print_header()
    
    # Parsear argumentos
    args = sys.argv[1:]
    verbose = '-v' in args or '--verbose' in args
    
    # Filtrar flags de los argumentos
    module_args = [arg for arg in args if not arg.startswith('-')]
    module_name = module_args[0] if module_args else None
    
    # Información sobre qué tests se ejecutarán
    if module_name:
        print(f"📋 Ejecutando tests del módulo: \033[94m{module_name}\033[0m\n")
    else:
        print("📋 Ejecutando \033[94mTODOS\033[0m los tests del sistema\n")
    
    # Descubrir tests
    suite = discover_tests(module_name, verbose)
    
    # Ejecutar tests
    verbosity = 2 if verbose else 1
    runner = ColoredTextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Imprimir resumen
    print_summary(result)
    
    # Retornar código de salida apropiado
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    main()
