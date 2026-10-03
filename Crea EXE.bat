@echo off
title Doorman - creazione eseguibile
cd /d "%~dp0"

echo ==========================================
echo   Doorman - creazione di Doorman.exe
echo ==========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [X] Python non trovato. Installalo da https://www.python.org/downloads/
    pause
    exit /b 1
)

python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [*] Installazione di PyInstaller in corso...
    python -m pip install --user pyinstaller
    if errorlevel 1 (
        echo [X] Installazione non riuscita.
        pause
        exit /b 1
    )
)

echo [*] Compilazione in corso, attendere...
python -m PyInstaller --noconfirm --onefile --noconsole ^
    --name Doorman ^
    --icon "%~dp0icon.ico" ^
    app.py

if errorlevel 1 (
    echo.
    echo [X] Compilazione non riuscita.
    echo     Se usi Python dal Microsoft Store, disinstallalo e installa
    echo     Python da python.org: PyInstaller non funziona con la versione Store.
    pause
    exit /b 1
)

echo.
echo [OK] Eseguibile pronto:  "%~dp0dist\Doorman.exe"
echo      Avvialo con doppio clic (chiedera' i privilegi di amministratore).
echo.
pause
