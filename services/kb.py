# services/kb.py
"""
Knowledge Base Service for supplement retrieval.
Uses PostgreSQL with pgvector for semantic RAG search.
"""
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_token_re = re.compile(r"[а-яa-z0-9\-]+", re.IGNORECASE)


class KnowledgeBaseService:
    """
    Service for finding relevant supplements using hybrid search.

    Combines:
    1. Vector similarity search (semantic understanding)
    2. Keyword matching (exact term matching)

    Database is preferred when available, with JSON fallback.
    """

    def __init__(
        self, filepath: str = "knowledge_base.json", use_database: bool = True
    ):
        self.filepath = filepath
        self.use_database = use_database
        self.synonyms = {
            "усталость": ["энергия", "митохондрии", "атф", "coq10", "l-карнитин"],
            "давление": ["аг", "гипертензия", "сосуды", "магний", "вазодилатация"],
            "сердце": ["миокард", "ибс", "кардио", "ритм", "таурин", "омега"],
            "сахар": ["глюкоза", "инсулин", "диабет", "сд2", "берберин", "хром"],
            "курение": [
                "антиоксидант",
                "легкие",
                "сосуды",
                "воспаление",
                "эндотелий",
                "nac",
            ],
            "стресс": ["магний", "кортизол", "нервная", "сон", "gaba", "мелатонин"],
            "активность": ["суставы", "энергия", "мышцы", "метаболизм"],
            "воспаление": ["crp", "nf-kb", "куркумин", "омега-3", "ресвератрол"],
        }

        # Check database availability
        self._db_available = False
        self._embeddings_available = False

        if use_database:
            self._db_available, self._embeddings_available = self._check_database()

        # Load JSON as fallback
        if not self._db_available:
            self.data = self._load_json_data()
        else:
            self.data = []
            mode = "with embeddings" if self._embeddings_available else "keyword only"
            logger.info(f"Knowledge Base using PostgreSQL ({mode})")

    def _check_database(self) -> tuple:
        """Check database and embedding availability."""
        try:
            from database.connection import check_db_connection, get_db_session
            from models import Supplement

            if not check_db_connection():
                return False, False

            with get_db_session() as db:
                total = db.query(Supplement).count()
                with_embeddings = (
                    db.query(Supplement)
                    .filter(Supplement.embedding.isnot(None))
                    .count()
                )

                if total == 0:
                    logger.warning(
                        "Database connected but no supplements found. Using JSON fallback."
                    )
                    return False, False

                has_embeddings = with_embeddings > 0
                logger.info(
                    f"Knowledge Base: {total} supplements, "
                    f"{with_embeddings} with embeddings"
                )
                return True, has_embeddings

        except Exception as e:
            logger.warning(f"Database not available: {e}. Using JSON fallback.")
            return False, False

    def _load_json_data(self) -> list[dict]:
        """Load knowledge base from JSON file."""
        try:
            with open(self.filepath, encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Knowledge Base loaded from JSON: {len(data)} categories.")
            return data
        except Exception as e:
            logger.critical(f"Could not load knowledge base '{self.filepath}': {e}")
            return []

    def _tokenize(self, text: str) -> set:
        """Tokenize text into lowercase terms."""
        if not text:
            return set()
        tokens = _token_re.findall(text.lower())
        return set(tokens)

    def _expand_terms(self, raw_terms: set) -> set:
        """Expand terms with synonyms."""
        expanded = set()
        for term in raw_terms:
            expanded.add(term)
            if term in self.synonyms:
                for s in self.synonyms[term]:
                    expanded.add(s)
        return expanded

    def find_relevant_supplements(
        self, search_query: str, top_k: int = 5
    ) -> dict[str, Any]:
        """
        Find relevant supplements using hybrid search.

        Args:
            search_query: Text query from ML service
            top_k: Maximum number of supplements to return

        Returns:
            Dict mapping supplement names to their data
        """
        if not search_query:
            return {}

        # Use database if available
        if self._db_available:
            if self._embeddings_available:
                return self._find_hybrid(search_query, top_k)
            else:
                return self._find_keyword_only(search_query, top_k)

        # Fall back to JSON
        return self._find_from_json(search_query, top_k)

    def _find_hybrid(self, search_query: str, top_k: int) -> dict[str, Any]:
        """
        Hybrid search: combine vector similarity with keyword scores.

        This is true RAG - semantic understanding + exact matching.
        """
        try:
            from database.connection import get_db_session
            from models import Condition, Supplement
            from services.embedding_service import embedding_service

            logger.info(f"KB Hybrid Search: '{search_query}'")

            # Generate query embedding
            query_embedding = embedding_service.generate_embedding(search_query)

            # Prepare keyword terms
            raw_tokens = self._tokenize(search_query)
            expanded = self._expand_terms(raw_tokens)

            with get_db_session() as db:
                # Get all supplements with embeddings
                supplements = (
                    db.query(Supplement)
                    .join(Condition)
                    .filter(Supplement.embedding.isnot(None))
                    .all()
                )

                scored = []
                for supp in supplements:
                    # Vector similarity score (0-1)
                    vector_distance = supp.embedding.cosine_distance(query_embedding)
                    vector_score = (1 - vector_distance) * 10  # Scale to 0-10

                    # Keyword score (existing logic)
                    name = (supp.name or "").lower()
                    mechanism = (supp.mechanism or "").lower()
                    keywords = " ".join(supp.keywords or []).lower()
                    condition_code = (
                        supp.condition.code.lower() if supp.condition else ""
                    )

                    keyword_score = 0
                    for term in expanded:
                        if term in name:
                            keyword_score += 5
                        if term in keywords:
                            keyword_score += 3
                        if term in mechanism:
                            keyword_score += 1
                        if term in condition_code:
                            keyword_score += 4

                    # Combined score: weight vector more for semantic understanding
                    combined_score = (vector_score * 0.6) + (keyword_score * 0.4)

                    if combined_score > 0.5:  # Minimum threshold
                        scored.append(
                            {
                                "name": supp.name,
                                "score": combined_score,
                                "vector_score": vector_score,
                                "keyword_score": keyword_score,
                                "data": supp.to_dict(),
                            }
                        )

                # Sort by combined score
                scored.sort(key=lambda x: x["score"], reverse=True)
                top = scored[:top_k]

                result = {}
                for item in top:
                    if item["name"] not in result:
                        result[item["name"]] = item["data"]
                        logger.debug(
                            f"  {item['name'][:30]}: total={item['score']:.2f} "
                            f"(vector={item['vector_score']:.2f}, keyword={item['keyword_score']})"
                        )

                logger.info(f"KB Hybrid Retrieval: returning {len(result)} items")
                return result

        except Exception as e:
            logger.error(f"Hybrid search error: {e}. Falling back to keyword search.")
            return self._find_keyword_only(search_query, top_k)

    def _find_keyword_only(self, search_query: str, top_k: int) -> dict[str, Any]:
        """Keyword-based search in database (fallback when no embeddings)."""
        try:
            from database.connection import get_db_session
            from models import Condition, Supplement

            raw_tokens = self._tokenize(search_query)
            expanded = self._expand_terms(raw_tokens)

            logger.info(f"KB Keyword Search: '{search_query}'")

            with get_db_session() as db:
                supplements = db.query(Supplement).join(Condition).all()

                scored = []
                for supp in supplements:
                    name = (supp.name or "").lower()
                    mechanism = (supp.mechanism or "").lower()
                    keywords = " ".join(supp.keywords or []).lower()
                    condition_code = (
                        supp.condition.code.lower() if supp.condition else ""
                    )

                    score = 0
                    for term in expanded:
                        if term in name:
                            score += 5
                        if term in keywords:
                            score += 3
                        if term in mechanism:
                            score += 1
                        if term in condition_code:
                            score += 4

                    if score > 0:
                        scored.append(
                            {"name": supp.name, "score": score, "data": supp.to_dict()}
                        )

                scored.sort(key=lambda x: x["score"], reverse=True)
                top = scored[:top_k]

                result = {}
                for item in top:
                    if item["name"] not in result:
                        result[item["name"]] = item["data"]

                logger.info(f"KB Keyword Retrieval: returning {len(result)} items")
                return result

        except Exception as e:
            logger.error(f"Database keyword search error: {e}. Falling back to JSON.")
            self._db_available = False
            self.data = self._load_json_data()
            return self._find_from_json(search_query, top_k)

    def _find_from_json(self, search_query: str, top_k: int) -> dict[str, Any]:
        """Find supplements from JSON data (original implementation)."""
        if not self.data:
            return {}

        raw_tokens = self._tokenize(search_query)
        expanded = self._expand_terms(raw_tokens)

        logger.info(f"KB JSON Search: '{search_query}'")

        scored = []
        for entry in self.data:
            for supp in entry.get("supplements", []):
                name = supp.get("name", "") or ""
                mechanism = supp.get("mechanism", "") or ""
                keywords = " ".join(supp.get("keywords", [])).lower()
                full_text = f"{name} {mechanism} {keywords}".lower()
                tokens_in_supp = self._tokenize(full_text)

                score = 0
                for term in expanded:
                    if term in name.lower():
                        score += 5
                    if term in keywords:
                        score += 3
                    if term in mechanism.lower():
                        score += 1
                    if term in tokens_in_supp:
                        score += 1

                if score > 0:
                    scored.append({"name": name, "score": score, "data": supp})

        scored.sort(key=lambda x: x["score"], reverse=True)
        top = scored[:top_k]

        result = {}
        for item in top:
            if item["name"] not in result:
                result[item["name"]] = item["data"]

        logger.info(f"KB JSON Retrieval: returning {len(result)} items")
        return result
