@echo off
title Pulse Metrics - Anti-Suspension (Stay Awake)
echo =======================================================
echo     PULSE METRICS - PREVENCION DE SUSPENSION
echo =======================================================
echo.

if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe stay_awake.py
) else (
    python stay_awake.py
)

pause
