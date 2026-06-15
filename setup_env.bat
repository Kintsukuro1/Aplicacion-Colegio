@echo off
title Configuración de Entorno - Aplicacion Colegio
echo ==========================================================
echo Iniciando script de configuración de entorno...
echo ==========================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_env.ps1"
echo.
echo ==========================================================
echo Presione cualquier tecla para salir.
echo ==========================================================
pause > nul
