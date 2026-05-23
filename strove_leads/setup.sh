#!/usr/bin/env bash
# Strove Leads — One-shot setup script
# Run from inside strove_leads/ directory

set -e

cd "$(dirname "$0")"

echo "╔══════════════════════════════════════════════╗"
echo "║   Strove Leads — Automated Setup             ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Check Python version
PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "→ Python version: $PY_VERSION"

# Detect venv
if [ ! -d ".venv" ]; then
  echo "→ Creating virtual environment..."
  python3 -m venv .venv
fi

# Activate venv
# shellcheck disable=SC1091
source .venv/bin/activate

# Upgrade pip
echo "→ Upgrading pip..."
pip install --upgrade pip -q

# Install dependencies
echo "→ Installing Python dependencies..."
pip install -r requirements.txt -q

# Install Playwright browsers
echo "→ Installing Playwright Chromium (this may take a minute)..."
if ! python -m playwright install chromium 2>&1 | tail -3; then
  echo "⚠  Playwright Chromium install had issues — scraping will fall back to requests-only mode"
fi

# Try installing system deps for Playwright (Linux only, optional)
if [[ "$OSTYPE" == "linux-gnu"* ]] && command -v sudo &> /dev/null; then
  echo "→ Installing Playwright system dependencies (may prompt for password)..."
  python -m playwright install-deps chromium 2>&1 | tail -3 || echo "⚠  System deps skipped"
fi

# Create .env if missing
if [ ! -f ".env" ]; then
  echo "→ Creating .env from template..."
  cp .env.example .env
  # Generate a random secret key
  SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|SECRET_KEY=change-this-to-a-random-secret-key|SECRET_KEY=$SECRET|" .env
  else
    sed -i "s|SECRET_KEY=change-this-to-a-random-secret-key|SECRET_KEY=$SECRET|" .env
  fi
  echo "✓ .env created with random SECRET_KEY"
else
  echo "✓ .env already exists — keeping yours"
fi

# Initialize the DB
echo "→ Initializing SQLite database..."
python -c "from database.db import init_db; init_db(); print('  database ready')"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   ✓ Setup complete                           ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. (Optional) Add API keys → see API_KEYS.md"
echo "     - SerpAPI for better Google coverage"
echo "     - Hunter.io / Snov.io for email enrichment"
echo "  2. Test API keys → python test_apis.py"
echo "  3. Run the app → python app.py"
echo "  4. Open http://localhost:5000"
echo ""
echo "To deploy → see DEPLOY.md"
echo ""
