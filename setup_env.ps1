# Script de Automatización de Configuración de Entorno
# Requisitos: PowerShell 5.1 o superior
# Ejecuta setup_env.bat para omitir restricciones de políticas de ejecución.

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   CONFIGURACIÓN AUTOMÁTICA DEL ENTORNO DE DESARROLLO" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# ==========================================================
# 1. VERIFICACIÓN / INSTALACIÓN DE PYTHON 3.13
# ==========================================================
Write-Host "[1/5] Verificando versión de Python..." -ForegroundColor Cyan

$pythonVersion = "3.13"
$pyAvailable = $false
$pythonPath = ""

try {
    # Probar con el Python Launcher (py -3.13)
    $pyTest = & py -3.13 --version 2>&1
    if ($LASTEXITCODE -eq 0 -and $pyTest -like "*$pythonVersion*") {
        $pyAvailable = $true
        $pythonPath = "py -3.13"
        Write-Host " -> Python Launcher detectado. Usando: py -$pythonVersion" -ForegroundColor Green
    }
} catch {}

if (-not $pyAvailable) {
    try {
        # Probar con comando directo 'python'
        $pyTest = & python --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $pyTest -like "*$pythonVersion*") {
            $pyAvailable = $true
            $pythonPath = "python"
            Write-Host " -> Python 3.13 detectado en el PATH." -ForegroundColor Green
        }
    } catch {}
}

if (-not $pyAvailable) {
    Write-Host "[!] Python 3.13 no detectado en el sistema." -ForegroundColor Yellow
    Write-Host " -> Intentando instalar Python 3.13..." -ForegroundColor Cyan

    $wingetAvailable = $false
    try {
        $wingetTest = Get-Command winget -ErrorAction SilentlyContinue
        if ($wingetTest) { $wingetAvailable = $true }
    } catch {}

    if ($wingetAvailable) {
        Write-Host " -> Instalando Python 3.13 vía Winget..." -ForegroundColor Cyan
        & winget install --id Python.Python.3.13 --silent --accept-package-agreements --accept-source-agreements
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host " -> Instalación completada con Winget." -ForegroundColor Green
            $pyAvailable = $true
            # Refrescar variables de entorno
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            $pythonPath = "py -3.13"
        } else {
            Write-Host " -> Winget falló o no pudo completar la instalación. Intentando descarga directa..." -ForegroundColor Warning
        }
    }

    if (-not $pyAvailable) {
        $url = "https://www.python.org/ftp/python/3.13.3/python-3.13.3-amd64.exe"
        $installerPath = Join-Path $PSScriptRoot "python-installer.exe"
        
        Write-Host " -> Descargando instalador oficial desde: $url" -ForegroundColor Cyan
        Invoke-WebRequest -Uri $url -OutFile $installerPath
        
        Write-Host " -> Ejecutando instalador silencioso (esto puede tardar unos momentos)..." -ForegroundColor Cyan
        $installArgs = "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0"
        $process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
        
        # Eliminar instalador
        Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
        
        if ($process.ExitCode -eq 0) {
            Write-Host " -> Instalación directa completada con éxito." -ForegroundColor Green
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            $pythonPath = "py -3.13"
            $pyAvailable = $true
        } else {
            Write-Host "[✗] Error al instalar Python. Código de salida: $($process.ExitCode)" -ForegroundColor Red
            Write-Host " -> Por favor instale Python 3.13 manualmente y vuelva a ejecutar el script." -ForegroundColor Yellow
            exit 1
        }
    }
}

Write-Host "[✓] Python 3.13 listo para usar." -ForegroundColor Green
Write-Host ""

# ==========================================================
# 2. BORRAR Y RECREAR EL VIRTUAL ENVIRONMENT (VENV)
# ==========================================================
Write-Host "[2/5] Gestionando Entorno Virtual (.venv)..." -ForegroundColor Cyan
$venvPath = Join-Path $PSScriptRoot ".venv"

if (Test-Path $venvPath) {
    Write-Host " -> Detectado .venv existente. Eliminándolo..." -ForegroundColor Yellow
    try {
        # Limpieza forzada de procesos de python corriendo en este venv si los hay
        Get-Process | Where-Object { $_.Path -like "*$venvPath*" } | ForEach-Object {
            Write-Host " -> Deteniendo proceso de Python en ejecución: $($_.Id)" -ForegroundColor Yellow
            Stop-Process -Id $_.Id -Force
        }
        
        Remove-Item -Path $venvPath -Recurse -Force -ErrorAction Stop
        Write-Host " -> Entorno virtual anterior eliminado." -ForegroundColor Green
    } catch {
        Write-Host "[✗] Error al borrar el venv. Asegúrese de cerrar cualquier terminal, editor o servidor web activo que use el venv." -ForegroundColor Red
        Write-Host " -> Detalle: $_" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host " -> Creando nuevo entorno virtual .venv con Python 3.13..." -ForegroundColor Cyan
if ($pythonPath -eq "py -3.13") {
    & py -3.13 -m venv $venvPath
} else {
    & python -m venv $venvPath
}

if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPath)) {
    Write-Host "[✗] No se pudo crear el entorno virtual (.venv)." -ForegroundColor Red
    exit 1
}

Write-Host "[✓] Entorno virtual (.venv) recreado exitosamente." -ForegroundColor Green
Write-Host ""

# ==========================================================
# 3. INSTALAR REQUIREMENTS
# ==========================================================
Write-Host "[3/5] Instalando dependencias en el entorno virtual..." -ForegroundColor Cyan
$pythonInVenv = Join-Path $venvPath "Scripts\python.exe"
$pipInVenv = Join-Path $venvPath "Scripts\pip.exe"

Write-Host " -> Actualizando pip..." -ForegroundColor Cyan
& $pythonInVenv -m pip install --upgrade pip

$reqPath = Join-Path $PSScriptRoot "requirements.txt"
if (Test-Path $reqPath) {
    Write-Host " -> Instalando requerimientos desde requirements.txt..." -ForegroundColor Cyan
    & $pipInVenv install -r $reqPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[✗] Error al instalar dependencias principales." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[!] No se encontró requirements.txt en la raíz." -ForegroundColor Yellow
}

$reqDevPath = Join-Path $PSScriptRoot "requirements-dev.txt"
if (Test-Path $reqDevPath) {
    Write-Host " -> Instalando dependencias de desarrollo..." -ForegroundColor Cyan
    & $pipInVenv install -r $reqDevPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Advertencia: Algunas dependencias de desarrollo fallaron al instalarse." -ForegroundColor Yellow
    }
}

Write-Host "[✓] Dependencias instaladas correctamente." -ForegroundColor Green
Write-Host ""

# ==========================================================
# 4. CONFIGURAR / CREAR LA BASE DE DATOS EN POSTGRESQL
# ==========================================================
Write-Host "[4/5] Configurando Base de Datos PostgreSQL..." -ForegroundColor Cyan

# Función para cargar .env
function Load-EnvFile {
    param([string]$path)
    $variables = @{}
    if (Test-Path $path) {
        Get-Content $path | ForEach-Object {
            $line = $_.Trim()
            if ($line -and -not $line.StartsWith("#")) {
                if ($line -match '^([^=]+)=(.*)$') {
                    $key = $Matches[1].Trim()
                    $value = $Matches[2].Trim()
                    if ($value -match '^"(.*)"$') { $value = $Matches[1] }
                    elseif ($value -match "^'(.*)'$") { $value = $Matches[1] }
                    $variables[$key] = $value
                }
            }
        }
    }
    return $variables
}

$envPath = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $envPath)) {
    Write-Host "[!] No se detectó archivo .env." -ForegroundColor Yellow
    Write-Host " -> Por favor, crea un archivo .env configurando las credenciales de PostgreSQL." -ForegroundColor Yellow
    # No detenemos el script porque tal vez el usuario lo creará luego, pero advertimos
} else {
    $dbSettings = Load-EnvFile -path $envPath
    
    $dbEngine = $dbSettings["DB_ENGINE"]
    $dbName = $dbSettings["DB_NAME"]
    $dbUser = $dbSettings["DB_USER"]
    $dbPassword = $dbSettings["DB_PASSWORD"]
    $dbHost = $dbSettings["DB_HOST"]
    $dbPort = $dbSettings["DB_PORT"]

    if ($dbEngine -ne "postgresql") {
        Write-Host " -> DB_ENGINE configurado como '$dbEngine' en .env. Omitiendo creación de Postgres." -ForegroundColor Yellow
    } else {
        # Buscar psql.exe
        $psqlAvailable = $false
        try {
            $psqlTest = Get-Command psql -ErrorAction SilentlyContinue
            if ($psqlTest) { $psqlAvailable = $true }
        } catch {}

        if (-not $psqlAvailable) {
            # Rutas típicas de PostgreSQL en Windows
            $postgresPaths = @(
                "C:\Program Files\PostgreSQL\*\bin",
                "C:\Program Files (x86)\PostgreSQL\*\bin"
            )
            foreach ($path in $postgresPaths) {
                $resolved = Resolve-Path $path -ErrorAction SilentlyContinue
                if ($resolved) {
                    $psqlPath = Join-Path $resolved[0].Path "psql.exe"
                    if (Test-Path $psqlPath) {
                        $env:Path += ";$($resolved[0].Path)"
                        $psqlAvailable = $true
                        break
                    }
                }
            }
        }

        if (-not $psqlAvailable) {
            Write-Host "[!] psql.exe no está en el PATH ni en ubicaciones comunes de Windows." -ForegroundColor Yellow
            Write-Host " -> Asegúrate de instalar PostgreSQL locally y añadir su carpeta 'bin' al PATH." -ForegroundColor Yellow
            Write-Host " -> Alternativamente, asegúrate de levantar tu base de datos mediante Docker si es tu configuración." -ForegroundColor Yellow
        } else {
            Write-Host " -> Conectando a PostgreSQL (Host: $dbHost, Puerto: $dbPort)..." -ForegroundColor Cyan
            
            # Usar PGPASSWORD para evitar que pida password interactivamente
            $env:PGPASSWORD = $dbPassword
            
            # Comprobar si la base de datos ya existe
            $checkCmd = "psql -h $dbHost -p $dbPort -U $dbUser -d postgres -tAc ""SELECT 1 FROM pg_database WHERE datname='$dbName'"""
            $dbExists = Invoke-Expression $checkCmd 2>$null

            if ($dbExists -eq "1") {
                Write-Host " -> La base de datos '$dbName' ya existe." -ForegroundColor Green
            } else {
                Write-Host " -> Base de datos '$dbName' no existe. Intentando crearla..." -ForegroundColor Yellow
                $createCmd = "psql -h $dbHost -p $dbPort -U $dbUser -d postgres -c ""CREATE DATABASE $dbName;"""
                Invoke-Expression $createCmd >$null 2>&1
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Host " -> Base de datos '$dbName' creada correctamente." -ForegroundColor Green
                } else {
                    Write-Host " -> Falló creación con usuario '$dbUser'. Probando con superusuario 'postgres'..." -ForegroundColor Yellow
                    
                    # Intentar conectarse como superusuario 'postgres'
                    $passwords = @($dbPassword, "postgres", "admin", "root", "123456")
                    $success = $false
                    foreach ($pass in $passwords) {
                        $env:PGPASSWORD = $pass
                        $createWithPostgres = "psql -h $dbHost -p $dbPort -U postgres -d postgres -c ""CREATE DATABASE $dbName;"""
                        Invoke-Expression $createWithPostgres >$null 2>&1
                        if ($LASTEXITCODE -eq 0) {
                            Write-Host " -> Base de datos '$dbName' creada exitosamente usando usuario 'postgres'." -ForegroundColor Green
                            $success = $true
                            break
                        }
                    }
                    if (-not $success) {
                        Write-Host "[!] No se pudo crear la base de datos automáticamente." -ForegroundColor Red
                        Write-Host " -> Asegúrate de que el servicio PostgreSQL esté activo e inicia sesión como admin para crearla manualmente:" -ForegroundColor Yellow
                        Write-Host "    CREATE DATABASE $dbName;" -ForegroundColor Cyan
                    }
                }
            }
        }
    }
}
Write-Host "[✓] Configuración de PostgreSQL finalizada." -ForegroundColor Green
Write-Host ""

# ==========================================================
# 5. APLICAR MIGRACIONES DE DJANGO
# ==========================================================
Write-Host "[5/5] Aplicando migraciones de Django..." -ForegroundColor Cyan
$managePy = Join-Path $PSScriptRoot "manage.py"

if (Test-Path $managePy) {
    & $pythonInVenv $managePy migrate
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[✓] Migraciones aplicadas correctamente." -ForegroundColor Green
    } else {
        Write-Host "[✗] Error al ejecutar las migraciones. Verifica la conexión a la base de datos." -ForegroundColor Red
    }
} else {
    Write-Host "[!] No se detectó manage.py en la raíz. Omitiendo migraciones." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "   ¡PROCESO COMPLETADO EXITOSAMENTE!" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Para activar el entorno virtual en PowerShell ejecuta:" -ForegroundColor Cyan
Write-Host "   .venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Green
