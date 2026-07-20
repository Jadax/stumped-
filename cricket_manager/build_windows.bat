@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Running automated tests...
python -m unittest discover -s tests -v
if errorlevel 1 goto :failed

echo [2/3] Cleaning previous PyInstaller output...
if exist build rmdir /s /q build
if exist dist\Stumped.exe del /q dist\Stumped.exe

echo [3/3] Building dist\Stumped.exe...
python -m PyInstaller --noconfirm --clean build.spec
if errorlevel 1 goto :failed

if not exist dist\Stumped.exe (
    echo ERROR: PyInstaller completed but dist\Stumped.exe was not found.
    exit /b 1
)

echo.
echo Build complete: %CD%\dist\Stumped.exe
exit /b 0

:failed
echo.
echo Build failed. Review the messages above and logs\error.log.
exit /b 1
