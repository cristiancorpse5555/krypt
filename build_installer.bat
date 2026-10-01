@echo off
chcp 65001 > nul
echo ========================================================
echo   Krypt v3.3 - Generador de Instalador para Windows
echo   Cristian Novoa - DMT Agencia
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/3] Verificando entorno virtual...
if not exist "venv\Scripts\python.exe" (
    echo ERROR: No se encontró venv\Scripts\python.exe.
    pause
    exit /b 1
)

echo [2/3] Compilando ejecutable con PyInstaller...
call venv\Scripts\activate.bat
pyinstaller --clean -y krypt.spec
if errorlevel 1 (
    echo ERROR durante la compilación con PyInstaller.
    pause
    exit /b 1
)

echo.
echo [3/3] Compilando instalador con Inno Setup...
set "ISCC_PATH=C:\Users\crist\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_PATH%" (
    set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if not exist "%ISCC_PATH%" (
    set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
)

"%ISCC_PATH%" installer.iss
if errorlevel 1 (
    echo ERROR durante la generación del instalador con Inno Setup.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   ¡INSTALADOR GENERADO CON ÉXITO!
echo   Ubicación: dist_installer\Krypt_Setup_v3.3.exe
echo ========================================================
echo.
pause
