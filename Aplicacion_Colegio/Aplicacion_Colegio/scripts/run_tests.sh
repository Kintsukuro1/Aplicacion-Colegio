#!/bin/bash
# Script para ejecutar tests por módulo

set -e

echo "======================================"
echo "   TESTS AUTOMATIZADOS - BACKEND"
echo "======================================"
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para ejecutar tests de un módulo
run_module_tests() {
    module=$1
    echo -e "${YELLOW}[EJECUTANDO]${NC} Tests de módulo: $module"
    
    if pytest tests/unit/$module -v --tb=short; then
        echo -e "${GREEN}[✓ EXITOSO]${NC} Tests de $module pasaron\n"
        return 0
    else
        echo -e "${RED}[✗ FALLIDO]${NC} Tests de $module fallaron\n"
        return 1
    fi
}

# Argumentos
MODULE=$1

if [ -z "$MODULE" ]; then
    echo "Ejecutando TODOS los tests..."
    echo ""
    
    # Tests unitarios de common
    run_module_tests "common"
    
    # Tests de integración
    echo -e "${YELLOW}[EJECUTANDO]${NC} Tests de integración"
    pytest tests/integration -v --tb=short

    # Tests de regresión crítica obligatoria
    echo -e "${YELLOW}[EJECUTANDO]${NC} Tests de regresión crítica obligatoria"
    pytest tests/regression/test_critical_operations_minimum.py -v --tb=short
    
    # Reporte de cobertura
    echo ""
    echo "======================================"
    echo "   REPORTE DE COBERTURA"
    echo "======================================"
    pytest --cov --cov-config=.coveragerc --cov-report=term-missing --cov-report=html
    
    echo ""
    echo -e "${GREEN}Reporte HTML generado en:${NC} htmlcov/index.html"
    
elif [ "$MODULE" == "common" ]; then
    run_module_tests "common"
    
elif [ "$MODULE" == "accounts" ]; then
    run_module_tests "accounts"
    
elif [ "$MODULE" == "academico" ]; then
    run_module_tests "academico"
    
elif [ "$MODULE" == "cursos" ]; then
    run_module_tests "cursos"
    
elif [ "$MODULE" == "institucion" ]; then
    run_module_tests "institucion"
    
elif [ "$MODULE" == "integration" ]; then
    echo -e "${YELLOW}[EJECUTANDO]${NC} Tests de integración"
    pytest tests/integration -v --tb=short

elif [ "$MODULE" == "regression" ]; then
    echo -e "${YELLOW}[EJECUTANDO]${NC} Tests de regresión crítica obligatoria"
    pytest tests/regression/test_critical_operations_minimum.py -v --tb=short
    
else
    echo -e "${RED}Módulo desconocido:${NC} $MODULE"
    echo "Módulos disponibles: common, accounts, academico, cursos, institucion, integration, regression"
    exit 1
fi

echo "======================================"
echo -e "${GREEN}   TESTS COMPLETADOS${NC}"
echo "======================================"
