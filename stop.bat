@echo off
title Detener Todos los Procesos de War Room
echo =======================================================
echo     DETENIENDO TODOS LOS PROCESOS DE WAR ROOM
echo =======================================================
echo.

echo [*] Finalizando procesos de transmision y grabacion (ffmpeg.exe)...
taskkill /f /im ffmpeg.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Procesos de ffmpeg.exe finalizados.
) else (
    echo [.] No se encontraron procesos de ffmpeg.exe activos.
)

echo.
echo [*] Finalizando procesos de la aplicacion (python.exe / streamlit)...
taskkill /f /im python.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Procesos de python.exe finalizados.
) else (
    echo [.] No se encontraron procesos de python.exe activos.
)

echo.
echo =======================================================
echo     LIMPIEZA DE PROCESOS COMPLETADA
echo =======================================================
echo Se han cerrado todas las transmisiones de fondo y el
echo servidor de Streamlit. Ya puede iniciar de nuevo.
echo.
pause
