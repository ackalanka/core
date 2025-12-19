# scripts/migrate_knowledge_base.py
"""
Migration script to transfer knowledge_base.json data to PostgreSQL database.

Run this script after setting up the database:
    python scripts/migrate_knowledge_base.py
"""
import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import check_db_connection, get_db_session, init_db  # noqa: E402
from models import Condition, Supplement  # noqa: E402

# Mapping of condition codes to full names
CONDITION_NAMES = {
    "АГ": ("Артериальная гипертензия", "Hypertension"),
    "СД2": ("Сахарный диабет 2 типа", "Type 2 Diabetes"),
    "ИБС": ("Ишемическая болезнь сердца", "Ischemic Heart Disease"),
    "Пост-ОИМ (1–3 мес)": ("Постинфарктное состояние", "Post-Myocardial Infarction"),
}


def load_knowledge_base(filepath: str = "knowledge_base.json") -> list:
    """Load knowledge base from JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def migrate_data():
    """Migrate knowledge base data to PostgreSQL."""

    # Check database connection
    if not check_db_connection():
        print("❌ Cannot connect to database. Is PostgreSQL running?")
        print("   Run: docker-compose up -d")
        return False

    # Initialize tables (creates if not exist)
    print("📦 Initializing database tables...")
    init_db()

    # Load JSON data
    print("📖 Loading knowledge_base.json...")
    try:
        kb_data = load_knowledge_base()
    except FileNotFoundError:
        print("❌ knowledge_base.json not found")
        return False

    print(f"   Found {len(kb_data)} conditions")

    # Migrate data
    with get_db_session() as db:
        # Track stats
        conditions_created = 0
        supplements_created = 0

        for entry in kb_data:
            condition_code = entry.get("condition", "")
            supplements_data = entry.get("supplements", [])

            # Get or create condition
            condition = (
                db.query(Condition).filter(Condition.code == condition_code).first()
            )

            if not condition:
                # Create new condition
                names = CONDITION_NAMES.get(condition_code, (condition_code, None))
                condition = Condition(
                    code=condition_code, name=names[0], name_en=names[1]
                )
                db.add(condition)
                db.flush()
                conditions_created += 1
                print(f"   ✅ Created condition: {condition_code}")

            # Create supplements
            for supp_data in supplements_data:
                # Check if supplement already exists
                existing = (
                    db.query(Supplement)
                    .filter(
                        Supplement.name == supp_data.get("name"),
                        Supplement.condition_id == condition.id,
                    )
                    .first()
                )

                if existing:
                    print(f"   ⏭️  Supplement exists: {supp_data.get('name')[:30]}...")
                    continue

                supplement = Supplement(
                    condition_id=condition.id,
                    name=supp_data.get("name", ""),
                    dosage=supp_data.get("dosage"),
                    mechanism=supp_data.get("mechanism"),
                    keywords=supp_data.get("keywords", []),
                    warnings=supp_data.get("warnings"),
                )
                db.add(supplement)
                supplements_created += 1

        # Commit all changes
        db.commit()

    print("\n✅ Migration complete!")
    print(f"   Conditions created: {conditions_created}")
    print(f"   Supplements created: {supplements_created}")

    return True


def verify_migration():
    """Verify data was migrated correctly."""
    print("\n🔍 Verifying migration...")

    with get_db_session() as db:
        conditions = db.query(Condition).all()
        supplements = db.query(Supplement).all()

        print(f"   Total conditions: {len(conditions)}")
        print(f"   Total supplements: {len(supplements)}")

        for cond in conditions:
            count = (
                db.query(Supplement).filter(Supplement.condition_id == cond.id).count()
            )
            print(f"   - {cond.code}: {count} supplements")

    return True


if __name__ == "__main__":
    print("=" * 50)
    print("CardioVoice Knowledge Base Migration")
    print("=" * 50)

    if migrate_data():
        verify_migration()
    else:
        print("\n❌ Migration failed")
        sys.exit(1)
