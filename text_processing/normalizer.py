import re
from typing import Any, List, Dict, Set, Tuple, Optional


class TripleNormalizer:

    def __init__(self):
        self.seen_triples: Set[Tuple[str, str, str]] = set()
        self.stats = {
            'original': 0,
            'empty': 0,
            'duplicates': 0,
            'final': 0
        }

    def normalize_string(self, text: str) -> str:
        if not text:
            return ""
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[.?!\-,]$', '', text)
        return text.strip()

    def normalize_triple(self, triple: Dict[str, Any]) -> Optional[Dict[str, str]]:

        s = self.normalize_string(str(triple.get('subject', '')))
        raw_p = str(triple.get('predicate', '')).upper().strip()
        p = re.sub(r'[\s\-]+', '_', raw_p)
        o = self.normalize_string(str(triple.get('object', '')))

        if not s or not p or not o:
            return None

        return {'subject': s, 'predicate': p, 'object': o}

    def normalize_and_deduplicate(self, triples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.reset()
        self.stats['original'] = len(triples)
        unique_triples = []

        for triple in triples:
            norm = self.normalize_triple(triple)

            if norm is None:
                self.stats['empty'] += 1
                continue

            triple_id = (norm['subject'], norm['predicate'], norm['object'])

            if triple_id not in self.seen_triples:
                self.seen_triples.add(triple_id)
                if 'chunk' in triple:
                    norm['chunk'] = triple['chunk']
                unique_triples.append(norm)
            else:
                self.stats['duplicates'] += 1

        self.stats['final'] = len(unique_triples)
        return unique_triples

    def get_summary(self) -> str:
        return (f"🧹 Normalization Summary: {self.stats['final']} kept, "
                f"{self.stats['duplicates']} duplicates removed, "
                f"{self.stats['empty']} empty/invalid removed.")

    def reset(self):
        self.seen_triples.clear()
        self.stats = {k: 0 for k in self.stats}