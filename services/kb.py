# services/kb.py
import json
import logging
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)

_token_re = re.compile(r"[а-яa-z0-9\-]+" , re.IGNORECASE)

class KnowledgeBaseService:
    def __init__(self, filepath='knowledge_base.json'):
        self.filepath = filepath
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
        self.data = self._load_data()

    def _load_data(self):
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Knowledge Base loaded: {len(data)} categories.")
            return data
        except Exception as e:
            logger.critical(f"Could not load knowledge base '{self.filepath}': {e}")
            return []

    def _tokenize(self, text: str):
        if not text:
            return set()
        tokens = _token_re.findall(text.lower())
        return set(tokens)

    def _expand_terms(self, raw_terms):
        expanded = set()
        for term in raw_terms:
            expanded.add(term)
            if term in self.synonyms:
                for s in self.synonyms[term]:
                    expanded.add(s)
        return expanded

    def find_relevant_supplements(self, search_query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Returns up to top_k relevant supplements as a dict keyed by supplement name.
        """
        if not search_query or not self.data:
            return {}

        raw_tokens = self._tokenize(search_query)
        expanded = self._expand_terms(raw_tokens)

        logger.info(f"KB Search Query: '{search_query}' -> tokens: {list(raw_tokens)[:8]} expanded: {list(expanded)[:8]}")

        scored = []
        for entry in self.data:
            for supp in entry.get("supplements", []):
                name = supp.get('name', '') or ''
                mechanism = supp.get('mechanism', '') or ''
                keywords = ' '.join(supp.get('keywords', [])).lower()
                full_text = f"{name} {mechanism} {keywords}".lower()
                tokens_in_supp = self._tokenize(full_text)

                score = 0
                # Heuristic weighting:
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

        logger.info(f"KB Retrieval: returning {len(result)} items.")
        return result
