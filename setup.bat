@echo off
title Instalador de Dependencias - War Room Monitoreo
echo =======================================================
echo     INSTALADOR DE DEPENDENCIAS - WAR ROOM MONITOREO
echo =======================================================
echo.

:: 1. Check Python
echo [*] Comprobando instalacion de Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python no esta instalado.
    echo [*] Descargando e instalando Python 3.11 de forma silenciosa...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe' -OutFile 'python_installer.exe'"
    echo [*] Ejecutando instalador de Python - acepta los permisos si los solicita...
    python_installer.exe /quiet PrependPath=1
    del python_installer.exe
    echo [OK] Python instalado. Por favor, cierra este terminal y vuelve a ejecutar 'setup.bat'.
    pause
    exit
) else (
    echo [OK] Python detectado.
)

:: 1b. Check Git
echo.
echo [*] Comprobando instalacion de Git (requerido para actualizaciones)...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Git no esta instalado.
    echo [*] Intentando instalar Git de forma silenciosa via winget...
    winget install --id Git.Git -e --silent --accept-source-agreements --accept-package-agreements >nul 2>&1
    if %errorlevel% neq 0 (
        echo [*] Winget no disponible o falló. Descargando instalador oficial de Git...
        powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe' -OutFile 'git_installer.exe'"
        echo [*] Ejecutando instalador de Git de forma silenciosa - acepta permisos si lo solicita...
        git_installer.exe /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS
        del git_installer.exe
    )
    echo [OK] Git instalado. Es posible que debas reiniciar la consola o la app para usar Git.
) else (
    echo [OK] Git detectado.
)

:: 2. Create Virtual Environment
echo.
echo [*] Creando entorno virtual de Python (venv)...
python -m venv venv
call venv\Scripts\activate.bat
echo [OK] Entorno virtual configurado y activo.

:: 3. Install requirements
echo.
echo [*] Actualizando pip e instalando dependencias (requirements.txt)...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo [OK] Dependencias instaladas.

:: 4. Install Playwright Browsers
echo.
echo [*] Instalando binarios de Playwright (Chromium para Instagram)...
playwright install chromium
echo [OK] Playwright configurado.

:: 5. Install Ollama
echo.
echo [*] Comprobando instalacion de Ollama...
if exist "%LocalAppData%\Programs\Ollama\ollama.exe" (
    echo [OK] Ollama ya esta instalado en el sistema.
) else (
    echo [*] Buscando instalador local de Ollama...
    if exist "OllamaSetup.exe" (
        echo [*] Ejecutando instalador local de Ollama en segundo plano...
        start /wait OllamaSetup.exe /silent
        echo [OK] Ollama instalado.
    ) else (
        echo [*] Descargando e instalando Ollama en segundo plano...
        powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile 'OllamaSetup.exe'"
        start /wait OllamaSetup.exe /silent
        echo [OK] Ollama instalado.
    )
)

:: 6. Download Ollama model
echo.
echo [*] Iniciando aplicacion de Ollama y descargando modelo Gemma...
if exist "%LocalAppData%\Programs\Ollama\ollama app.exe" (
    start "" "%LocalAppData%\Programs\Ollama\ollama app.exe"
) else (
    start "" "%LocalAppData%\Programs\Ollama\ollamaapp.exe"
)
echo Esperando 10 segundos a que el servicio se inicialice...
timeout /t 10 >nul
if exist "%LocalAppData%\Programs\Ollama\ollama.exe" (
    "%LocalAppData%\Programs\Ollama\ollama.exe" pull gemma:2b
) else (
    ollama pull gemma:2b
)
echo [OK] Modelo gemma:2b descargado e instalado.

echo.
echo =======================================================
echo     INSTALACION COMPLETADA CON EXITO
echo =======================================================
echo El entorno esta listo. Para arrancar la aplicacion,
echo simplemente haz doble clic en 'run.bat'.
echo.
pause
