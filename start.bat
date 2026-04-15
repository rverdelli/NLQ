@echo off
:: Doppio click -> attiva venv e lancia l'app
:: Poi apre il browser su http://localhost:8000

cd /d "%~dp0"

:: Crea il venv se non esiste
if not exist ".venv\" (
    echo Creo il venv...
    python -m venv .venv
    .venv\Scripts\pip install -q --upgrade pip
    .venv\Scripts\pip install -q -r requirements.txt
)

:: Apri il browser dopo 2 secondi
start "" /b cmd /c "timeout /t 2 >nul && start http://localhost:8000"

echo Avvio il server su http://localhost:8000
echo Premi Ctrl+C per fermare
echo.
.venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000 --reload
