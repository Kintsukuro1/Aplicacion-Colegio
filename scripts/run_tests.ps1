# Script PowerShell para ejecutar tests por módulo

param(
    [string]$Module = ""
)

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "   TESTS AUTOMATIZADOS - BACKEND" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

function Run-ModuleTests {
    param([string]$ModuleName)
    
    Write-Host "[EJECUTANDO] Tests de módulo: $ModuleName" -ForegroundColor Yellow
    
    $result = & pytest "tests/unit/$ModuleName" -v --tb=short
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[✓ EXITOSO] Tests de $ModuleName pasaron`n" -ForegroundColor Green
        return $true
    } else {
        Write-Host "[✗ FALLIDO] Tests de $ModuleName fallaron`n" -ForegroundColor Red
        return $false
    }
}

if ([string]::IsNullOrEmpty($Module)) {
    Write-Host "Ejecutando TODOS los tests..." -ForegroundColor Cyan
    Write-Host ""
    
    # Tests unitarios de common
    Run-ModuleTests -ModuleName "common"
    
    # Tests de integración
    Write-Host "[EJECUTANDO] Tests de integración" -ForegroundColor Yellow
    & pytest tests/integration -v --tb=short

    # Tests de regresión crítica obligatoria
    Write-Host "[EJECUTANDO] Tests de regresión crítica obligatoria" -ForegroundColor Yellow
    & pytest tests/regression/test_critical_operations_minimum.py -v --tb=short
    
    # Reporte de cobertura
    Write-Host ""
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "   REPORTE DE COBERTURA" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    & pytest --cov --cov-config=.coveragerc --cov-report=term-missing --cov-report=html
    
    Write-Host ""
    Write-Host "Reporte HTML generado en: htmlcov/index.html" -ForegroundColor Green
    
} elseif ($Module -eq "common") {
    Run-ModuleTests -ModuleName "common"
    
} elseif ($Module -eq "accounts") {
    Run-ModuleTests -ModuleName "accounts"
    
} elseif ($Module -eq "academico") {
    Run-ModuleTests -ModuleName "academico"
    
} elseif ($Module -eq "cursos") {
    Run-ModuleTests -ModuleName "cursos"
    
} elseif ($Module -eq "institucion") {
    Run-ModuleTests -ModuleName "institucion"
    
} elseif ($Module -eq "integration") {
    Write-Host "[EJECUTANDO] Tests de integración" -ForegroundColor Yellow
    & pytest tests/integration -v --tb=short

} elseif ($Module -eq "regression") {
    Write-Host "[EJECUTANDO] Tests de regresión crítica obligatoria" -ForegroundColor Yellow
    & pytest tests/regression/test_critical_operations_minimum.py -v --tb=short
    
} else {
    Write-Host "Módulo desconocido: $Module" -ForegroundColor Red
    Write-Host "Módulos disponibles: common, accounts, academico, cursos, institucion, integration, regression"
    exit 1
}

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "   TESTS COMPLETADOS" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
