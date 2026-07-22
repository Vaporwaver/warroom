@echo off
title Iniciar Pulse Metrics - Monitoreo con IA
echo =======================================================
echo     INICIANDO PULSE METRICS - MONITOREO CON IA
echo =======================================================
echo.

:: 1. Start Ollama in the background if not running
echo [*] Iniciando Ollama...
tasklist | findstr /i "ollama" >nul
if %errorlevel% neq 0 (
    if exist "%LocalAppData%\Programs\Ollama\ollama app.exe" (
        start "" "%LocalAppData%\Programs\Ollama\ollama app.exe"
        echo [OK] Ollama iniciado.
    ) else if exist "%LocalAppData%\Programs\Ollama\ollamaapp.exe" (
        start "" "%LocalAppData%\Programs\Ollama\ollamaapp.exe"
        echo [OK] Ollama iniciado.
    ) else (
        echo [!] No se encontro la app de Ollama. Asegurate de haber corrido 'setup.bat'.
    )
) else (
    echo [OK] Ollama ya se esta ejecutando.
)

:: 2. Activate Python Environment and run Streamlit
echo.
echo [*] Cargando entorno virtual e iniciando Streamlit...
if not exist "venv\Scripts\activate.bat" (
    echo [!] No se detecto el entorno virtual 'venv'.
    echo Por favor, ejecuta primero el script de instalacion 'setup.bat'.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

:loop
echo [*] Iniciando Streamlit (Cierre la ventana o presione Ctrl+C para terminar)...
streamlit run app.py
echo.
echo [!] El servidor de Streamlit se ha cerrado o ha fallado.
echo [*] Reiniciando en 5 segundos...
timeout /t 5 >nul
goto loop
