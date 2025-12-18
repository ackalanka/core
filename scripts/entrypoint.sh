#!/bin/bash
# ============================================
# CardioVoice Backend - Docker Entrypoint
# ============================================
# This script runs on container startup to:
# 1. Wait for database to be ready
# 2. Initialize database tables
# 3. Start the application

set -e

echo "🚀 CardioVoice Backend - Starting up..."

# --------------------------
# Wait for PostgreSQL
# --------------------------
echo "⏳ Waiting for PostgreSQL to be ready..."

MAX_RETRIES=30
RETRY_INTERVAL=2
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if python -c "from database.connection import check_db_connection; exit(0 if check_db_connection() else 1)" 2>/dev/null; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "   Attempt $RETRY_COUNT/$MAX_RETRIES - waiting ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Could not connect to PostgreSQL after $MAX_RETRIES attempts"
    exit 1
fi

# --------------------------
# Initialize Database Tables
# --------------------------
echo "📦 Initializing database tables..."

python -c "
from database.connection import init_db
init_db()
print('✅ Database tables initialized')
"

# --------------------------
# Optional: Run Knowledge Base Migration
# --------------------------
# Check if supplements table is empty and knowledge_base.json exists
if [ -f "knowledge_base.json" ]; then
    SUPPLEMENT_COUNT=$(python -c "
from database.connection import get_db_session
from models import Supplement
with get_db_session() as db:
    count = db.query(Supplement).count()
    print(count)
" 2>/dev/null || echo "0")

    if [ "$SUPPLEMENT_COUNT" = "0" ]; then
        echo "📖 Migrating knowledge base data..."
        python scripts/migrate_knowledge_base.py 2>/dev/null || echo "⚠️  Knowledge base migration skipped (optional)"
    else
        echo "📖 Knowledge base already populated ($SUPPLEMENT_COUNT supplements)"
    fi
fi

# --------------------------
# Start Application
# --------------------------
echo "🎯 Starting Gunicorn server..."
exec "$@"
