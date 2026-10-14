@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python -m pip install -r requirements-dev.txt
if errorlevel 1 goto failed
.venv\Scripts\python -m pytest -q
if errorlevel 1 goto failed
.venv\Scripts\python collect_licenses.py
if errorlevel 1 goto failed
.venv\Scripts\python -m PyInstaller --noconfirm --clean --onedir --windowed --icon assets\app_icon.ico --add-data "assets;assets" --manifest windows.manifest --name QRScreenReader --collect-all zxingcpp --add-data "THIRD_PARTY_LICENSES;THIRD_PARTY_LICENSES" app.py
if errorlevel 1 goto failed
copy README.md dist\QRScreenReader\README.md >nul
copy LICENSE dist\QRScreenReader\LICENSE >nul
xcopy /E /I /Y THIRD_PARTY_LICENSES dist\QRScreenReader\THIRD_PARTY_LICENSES >nul
echo Build succeeded: dist\QRScreenReader\QRScreenReader.exe
pause
exit /b 0
:failed
echo Build failed. Read the error above.
pause
exit /b 1
