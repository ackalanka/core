# scripts/generate_embeddings.py
"""
Script to generate embeddings for all supplements in the database.

Run this after migrating knowledge base data:
    python scripts/generate_embeddings.py
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_db_session, check_db_connection, engine
from models import Supplement
from services.embedding_service import embedding_service
from sqlalchemy import text


def add_embedding_column():
    """Add embedding column if it doesn't exist."""
    print("📦 Checking embedding column...")
    
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'supplements' AND column_name = 'embedding'
        """))
        
        if result.fetchone():
            print("   ✅ Embedding column already exists")
            return
        
        # Add column
        print("   Adding embedding column...")
        conn.execute(text("""
            ALTER TABLE supplements 
            ADD COLUMN embedding vector(384)
        """))
        conn.commit()
        print("   ✅ Embedding column added")


def create_vector_index():
    """Create HNSW index for fast vector similarity search."""
    print("📦 Checking vector index...")
    
    with engine.connect() as conn:
        # Check if index exists
        result = conn.execute(text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'supplements' AND indexname = 'ix_supplements_embedding'
        """))
        
        if result.fetchone():
            print("   ✅ Vector index already exists")
            return
        
        # Create HNSW index for cosine distance
        print("   Creating HNSW index (this may take a moment)...")
        conn.execute(text("""
            CREATE INDEX ix_supplements_embedding 
            ON supplements 
            USING hnsw (embedding vector_cosine_ops)
        """))
        conn.commit()
        print("   ✅ HNSW index created")


def generate_embeddings():
    """Generate embeddings for all supplements."""
    print("\n🧠 Generating embeddings...")
    
    with get_db_session() as db:
        # Get supplements without embeddings
        supplements = db.query(Supplement).filter(
            Supplement.embedding.is_(None)
        ).all()
        
        if not supplements:
            # Check if any have embeddings
            total = db.query(Supplement).count()
            with_embeddings = db.query(Supplement).filter(
                Supplement.embedding.isnot(None)
            ).count()
            
            if with_embeddings > 0:
                print(f"   ✅ All {with_embeddings} supplements already have embeddings")
            else:
                print("   ⚠️ No supplements found in database")
            return
        
        print(f"   Found {len(supplements)} supplements without embeddings")
        
        # Get texts for embedding
        texts = []
        for supp in supplements:
            text = supp.get_embedding_text()
            texts.append(text)
            print(f"   - {supp.name[:50]}...")
        
        # Generate embeddings in batch
        print("\n   Generating embeddings (downloading model if needed)...")
        embeddings = embedding_service.generate_embeddings_batch(texts)
        
        # Update database
        print("\n   Saving embeddings to database...")
        for supp, emb in zip(supplements, embeddings):
            supp.embedding = emb
        
        db.commit()
        print(f"   ✅ Updated {len(supplements)} supplements with embeddings")


def verify_embeddings():
    """Verify embeddings were generated correctly."""
    print("\n🔍 Verifying embeddings...")
    
    with get_db_session() as db:
        total = db.query(Supplement).count()
        with_embeddings = db.query(Supplement).filter(
            Supplement.embedding.isnot(None)
        ).count()
        
        print(f"   Total supplements: {total}")
        print(f"   With embeddings: {with_embeddings}")
        
        if total == with_embeddings:
            print("   ✅ All supplements have embeddings!")
        else:
            print(f"   ⚠️ {total - with_embeddings} supplements missing embeddings")


def test_similarity_search():
    """Test vector similarity search."""
    print("\n🔎 Testing similarity search...")
    
    test_query = "сердце усталость энергия"
    print(f"   Query: '{test_query}'")
    
    # Generate query embedding
    query_embedding = embedding_service.generate_embedding(test_query)
    
    with get_db_session() as db:
        # Vector similarity search using pgvector
        from sqlalchemy import func
        
        results = db.query(
            Supplement.name,
            Supplement.embedding.cosine_distance(query_embedding).label('distance')
        ).filter(
            Supplement.embedding.isnot(None)
        ).order_by(
            'distance'
        ).limit(5).all()
        
        print("\n   Top 5 similar supplements:")
        for name, distance in results:
            similarity = 1 - distance  # Convert distance to similarity
            print(f"   - {name[:40]:<40} (similarity: {similarity:.4f})")


if __name__ == "__main__":
    print("=" * 50)
    print("CardioVoice Embedding Generation")
    print("=" * 50)
    
    # Check database connection
    if not check_db_connection():
        print("❌ Cannot connect to database. Is PostgreSQL running?")
        print("   Run: docker-compose up -d")
        sys.exit(1)
    
    # Add embedding column if needed
    add_embedding_column()
    
    # Generate embeddings
    generate_embeddings()
    
    # Create vector index
    create_vector_index()
    
    # Verify and test
    verify_embeddings()
    test_similarity_search()
    
    print("\n✅ Embedding generation complete!")
