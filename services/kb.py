# services/kb.py
"""
Knowledge Base Service for supplement retrieval.
Uses PostgreSQL database with fallback to JSON file.
"""
import json
import logging
import re
from typing import Dict, Any, List, Optional

from sqlalchemy import or_, func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_token_re = re.compile(r"[а-яa-z0-9\-]+", re.IGNORECASE)


class KnowledgeBaseService:
    """
    Service for finding relevant supplements based on search queries.
    
    Supports both database and JSON file as data sources.
    Database is preferred when available.
    """
    
    def __init__(self, filepath: str = 'knowledge_base.json', use_database: bool = True):
        self.filepath = filepath
        self.use_database = use_database
        self.synonyms = {
            "усталость": ["энергия", "митохондрии", "атф", "coq10", "l-карнитин"],
            "давление": ["аг", "гипертензия", "сосуды", "магний", "вазодилатация"],
            "сердце": ["миокард", "ибс", "кардио", "ритм", "таурин", "омега"],
            "сахар": ["глюкоза", "инсулин", "диабет", "сд2", "берберин", "хром"],
            "курение": ["антиоксидант", "легкие", "сосуды", "воспаление", "эндотелий", "nac"],
            "стресс": ["магний", "кортизол", "нервная", "сон", "gaba", "мелатонин"],
            "активность": ["суставы", "энергия", "мышцы", "метаболизм"],
            "воспаление": ["crp", "nf-kb", "куркумин", "омега-3", "ресвератрол"]
        }
        
        # Try database first, fall back to JSON
        self._db_available = False
        if use_database:
            self._db_available = self._check_database()
        
        # Load JSON as fallback
        if not self._db_available:
            self.data = self._load_json_data()
        else:
            self.data = []
            logger.info("Knowledge Base using PostgreSQL database")
    
    def _check_database(self) -> bool:
        """Check if database connection and data is available."""
        try:
            from database.connection import check_db_connection, get_db_session
            from models import Supplement
            
            if not check_db_connection():
                return False
            
            # Check if supplements exist
            with get_db_session() as db:
                count = db.query(Supplement).count()
                if count > 0:
                    logger.info(f"Knowledge Base loaded from database: {count} supplements")
                    return True
                else:
                    logger.warning("Database connected but no supplements found. Using JSON fallback.")
                    return False
        except Exception as e:
            logger.warning(f"Database not available: {e}. Using JSON fallback.")
            return False
    
    def _load_json_data(self) -> List[Dict]:
        """Load knowledge base from JSON file."""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
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
    
    def find_relevant_supplements(self, search_query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Find relevant supplements based on search query.
        
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
            return self._find_from_database(search_query, top_k)
        
        # Fall back to JSON
        return self._find_from_json(search_query, top_k)
    
    def _find_from_database(self, search_query: str, top_k: int) -> Dict[str, Any]:
        """Find supplements from PostgreSQL database."""
        try:
            from database.connection import get_db_session
            from models import Supplement, Condition
            
            raw_tokens = self._tokenize(search_query)
            expanded = self._expand_terms(raw_tokens)
            
            logger.info(f"KB Database Search: '{search_query}' -> tokens: {list(raw_tokens)[:8]}")
            
            with get_db_session() as db:
                # Query all supplements and score them
                supplements = db.query(Supplement).join(Condition).all()
                
                scored = []
                for supp in supplements:
                    name = (supp.name or '').lower()
                    mechanism = (supp.mechanism or '').lower()
                    keywords = ' '.join(supp.keywords or []).lower()
                    condition_code = supp.condition.code.lower() if supp.condition else ''
                    
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
                        scored.append({
                            "name": supp.name,
                            "score": score,
                            "data": supp.to_dict()
                        })
                
                # Sort by score and take top_k
                scored.sort(key=lambda x: x["score"], reverse=True)
                top = scored[:top_k]
                
                result = {}
                for item in top:
                    if item["name"] not in result:
                        result[item["name"]] = item["data"]
                
                logger.info(f"KB Database Retrieval: returning {len(result)} items.")
                return result
                
        except Exception as e:
            logger.error(f"Database query error: {e}. Falling back to JSON.")
            self._db_available = False
            self.data = self._load_json_data()
            return self._find_from_json(search_query, top_k)
    
    def _find_from_json(self, search_query: str, top_k: int) -> Dict[str, Any]:
        """Find supplements from JSON data (original implementation)."""
        if not self.data:
            return {}
        
        raw_tokens = self._tokenize(search_query)
        expanded = self._expand_terms(raw_tokens)
        
        logger.info(f"KB JSON Search: '{search_query}' -> tokens: {list(raw_tokens)[:8]}")
        
        scored = []
        for entry in self.data:
            for supp in entry.get("supplements", []):
                name = supp.get('name', '') or ''
                mechanism = supp.get('mechanism', '') or ''
                keywords = ' '.join(supp.get('keywords', [])).lower()
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
        
        logger.info(f"KB JSON Retrieval: returning {len(result)} items.")
        return result
