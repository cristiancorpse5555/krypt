# crear_acceso_directo.ps1 — Crea acceso directo en el Escritorio
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Transcriptor.lnk"
$targetPath = Join-Path $scriptDir "Transcriptor.bat"

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($shortcutPath)
$sc.TargetPath = $targetPath
$sc.WorkingDirectory = $scriptDir
$sc.Description = "Grabador y Transcriptor de Reuniones"
$sc.IconLocation = "shell32.dll,18"
$sc.WindowStyle = 7
$sc.Save()

if (Test-Path $shortcutPath) {
    Write-Host ""
    Write-Host "============================================"
    Write-Host "  Acceso directo creado en el Escritorio!"
    Write-Host "============================================"
    Write-Host ""
    Write-Host "  Ubicacion: $shortcutPath"
} else {
    Write-Host "ERROR: No se pudo crear el acceso directo."
}
