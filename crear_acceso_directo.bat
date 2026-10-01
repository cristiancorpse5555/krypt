@echo off
:: ============================================================
::  Crea un acceso directo de Transcriptor en el Escritorio
:: ============================================================
title Crear Acceso Directo - Transcriptor
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0crear_acceso_directo.ps1"
pause
