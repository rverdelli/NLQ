#!/usr/bin/env bash
# Doppio click (o terminale) → attiva venv e lancia l'app
# Poi apre il browser su http://localhost:8000

set -e
cd "$(dirname "$0")"

# Crea il venv se non esiste
if [ ! -d ".venv" ]; then
    echo "Creo il venv..."
    python3 -m venv .venv
    .venv/bin/pip install -q --upgrade pip
    .venv/bin/pip install -q -r requirements.txt
fi

# Apri il browser dopo 2 secondi (in background)
(sleep 2 && xdg-open http://localhost:8000 2>/dev/null || open http://localhost:8000 2>/dev/null || true) &

echo "Avvio il server su http://localhost:8000"
echo "Premi Ctrl+C per fermare"
echo ""
.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
