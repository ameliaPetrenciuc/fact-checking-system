import re


class TripleValidator:
    def __init__(self):
        self.required_keys = {'subject', 'predicate', 'object'}

        self.blacklist = {
            'this text', 'the article', 'the author', 'the source', 'it',
            'none', 'null', 'n/a', 'unknown', 'empty', 'na'
        }

        self.meta_blacklist = {
            'evidence', 'claim', 'source', 'passage', 'proof', 'studies',
            'research', 'experts', 'scientists', 'findings', 'data',
            'analysis', 'lack of evidence', 'link', 'connection', 'support',
            'lack of support', 'no evidence', 'scientific consensus',
            'the evidence', 'the claim', 'the study', 'the research',
            'the proof', 'the findings', 'the data', 'the analysis',
            'current evidence', 'available evidence', 'scientific evidence',
        }

        self.vague_blacklist = {
            'consequences', 'deadly consequences', 'things', 'stuff', 'issues',
            'problems', 'results', 'effects', 'impacts', 'call', 'calls',
            'event', 'events', 'meeting', 'meetings', 'large tests',
            'this', 'that', 'something', 'everything', 'nothing',
            'people', 'everyone', 'someone', 'activities', 'situation',
            'leaders', 'leadership', 'transparency',
            'data model projections',
        }

        self.banned_predicates = {
            'FOUND', 'GOT', 'WAS', 'IS', 'HAS', 'HAD',
            'SAID', 'REPORTED', 'ANNOUNCED', 'MADE',
            'DID', 'DOES', 'WENT', 'CAME',
            'REPORTS', 'DISCUSSES', 'DISCUSSED',
            'TALKS', 'TALKED', 'MENTIONS', 'MENTIONED',
            'STATED', 'SAYS', 'TOLD', 'ADDED', 'NOTED',
            'HOSTS', 'HOSTED',
            'BEGAN', 'STARTED', 'ENDED', 'FINISHED',
        }

        self._numeric_entity_re = re.compile(
            r'^\d[\d,.]*\s+'
            r'(?:people|persons|cases|deaths|patients|tests|recoveries|'
            r'doses|samples|infections|hospitalizations|victims|residents)$',
            re.IGNORECASE
        )

    def validate_triple(self, triple: dict) -> bool:
        if not isinstance(triple, dict): return False
        if not all(key in triple for key in self.required_keys): return False

        s = str(triple['subject']).strip().lower()
        p_raw = str(triple['predicate']).strip()
        p_normalized = re.sub(r'[\s\-]+', '_', p_raw.upper())
        o = str(triple['object']).strip().lower()

        if len(s) > 60 or len(o) > 60:
            print(f"[DEBUG] Rejected (too long) — S: '{s}', O: '{o}'")
            return False

        if len(p_normalized) < 2 or len(p_normalized) > 50:
            print(f"[DEBUG] Rejected (predicate length {len(p_normalized)}) — P: '{p_normalized}'")
            return False

        if s in self.blacklist or o in self.blacklist:
            print(f"[DEBUG] Rejected (blacklisted) — S: '{s}', O: '{o}'")
            return False

        if s in self.meta_blacklist or o in self.meta_blacklist:
            print(f"[DEBUG] Rejected (meta-entity) — S: '{s}', O: '{o}'")
            return False

        if s in self.vague_blacklist or o in self.vague_blacklist:
            print(f"[DEBUG] Rejected (vague abstraction) — S: '{s}', O: '{o}'")
            return False

        if p_normalized in self.banned_predicates:
            print(f"[DEBUG] Rejected (banned predicate) — P: '{p_normalized}'")
            return False

        if self._numeric_entity_re.match(s) or self._numeric_entity_re.match(o):
            print(f"[DEBUG] Rejected (numeric statistic entity) — S: '{s}', O: '{o}'")
            return False

        return True

    def validate_triples(self, triples: list, chunk_number: int = None, source_type: str = "unknown") -> list:
        if not isinstance(triples, list):
            return []

        valid_triples = []
        for triple in triples:
            if self.validate_triple(triple):
                triple['chunk'] = chunk_number
                triple['source_kind'] = source_type  
                valid_triples.append(triple)
            else:
                print(f"[DEBUG] Triplet respins de Validator: {triple}")

        return valid_triples