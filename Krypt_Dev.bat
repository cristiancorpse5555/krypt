@echo off
title Krypt (Modo Desarrollo)
cd /d "%~dp0"

:: Verificar si existe el entorno virtual
if not exist "venv\Scripts\python.exe" (
    echo.
    echo ============================================
    echo   Configurando Krypt por primera vez
    echo ============================================
    echo.

    :: Buscar Python
    set "PYTHON_CMD="
    where py >nul 2>&1 && set "PYTHON_CMD=py -3"
    if not defined PYTHON_CMD (
        for %%P in (
            "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
            "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
            "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        ) do (
            if exist %%P (
                set "PYTHON_CMD=%%~P"
                goto :found_python
            )
        )
    )

    :found_python
    if not defined PYTHON_CMD (
        echo ERROR: No se encontro Python 3.11+ en este PC.
        echo Descargalo de https://python.org/downloads/
        echo IMPORTANTE: Marca "Add Python to PATH" durante la instalacion.
        pause
        exit /b 1
    )

    echo Usando: %PYTHON_CMD%
    echo Creando entorno virtual venv...
    %PYTHON_CMD% -m venv venv
    if errorlevel 1 (
        echo ERROR: No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )

    echo Instalando dependencias de requirements.txt...
    venv\Scripts\pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Fallo la instalacion de dependencias.
        pause
        exit /b 1
    )

    echo.
    echo ============================================
    echo   Entorno listo!
    echo ============================================
    echo.
)

:: Ejecutar Krypt directamente desde el código fuente
start "" /B venv\Scripts\pythonw.exe main.py
