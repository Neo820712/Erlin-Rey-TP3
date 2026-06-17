@echo off
REM Lanza la presentacion sirviendola por HTTP (no file://) para que cargue
REM la foto de portada y respete las rutas relativas.

cd /d "%~dp0"

set PORT=8080
set URL=http://localhost:%PORT%/presentacion/presentacion-final.html

echo Sirviendo la presentacion en %URL%
echo Para cerrar el servidor: cerra esta ventana o presiona Ctrl+C.

start "" "%URL%"
python -m http.server %PORT%
