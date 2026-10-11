class PromptTemplates:

    @staticmethod
    def get_system_prompt_for_ingestion() -> str:
        return """
    You are an advanced AI expert in Knowledge Graph Engineering and Semantic Analysis.
    Your task is to extract factual Subject-Predicate-Object (SPO) triples from the provided text.

    Your goals:
    - identify the main factual relations
    - normalize predicates into canonical forms
    - resolve pronouns to their actual entities
    - avoid vague, emotional, rhetorical, or meta statements
    - return only strict JSON
    """

    @staticmethod
    def get_user_prompt_template_for_ingestion() -> str:
        return """
    Extract Subject-Predicate-Object (S-P-O) triples from the text below.

    STRICT RULES:
    1. Output ONLY valid JSON.
    2. Use EXACTLY this structure:
    {{
      "triples": [
        {{ "subject": "...", "predicate": "...", "object": "..." }}
      ]
    }}
    3. Keys MUST be exactly: "subject", "predicate", "object".
    4. Subjects and objects MUST be lowercase. Predicates should be lowercase canonical forms; the system will normalize them to Neo4j relation format later.

    PREDICATE NORMALIZATION (CRITICAL):
    5. You MUST map the relationship to a CANONICAL PREDICATE.
    6. Preferred predicates: [
        supports, opposes, implements, causes, can_cause, criticizes, located_in,
        is_a, affects, acquired, banned, denies, rejects, confirms, refutes, spreads,
        does_not_spread, reduces, increases, recommends, treats, cures, prevents,
        helps_prevent, reduces_risk_of, protects, targets, validates, develops,
        ships, conducts, funds, approves, authorizes, sanctions,
        does_not_cure, does_not_prevent, does_not_protect, does_not_worsen,
        does_not_cause, reduces_mortality, increases_risk, does_not_increase_risk,
        sanitizes, decontaminates
    ]
    7. If none fit, create a 1-word or 2-word logical predicate.
    8. NEVER use quotes, apostrophes, or full sentences as predicates.
    9. NEVER use generic verbs as predicates. Specifically BANNED predicates:
       ✗ found, got, was, is, has, had, said, reported, announced, made, did, does, went, came,
         reports, discusses, discussed, talks, talked, mentions, mentioned, stated, says, told, added, noted, hosts
       Instead, replace with the specific meaning:
       ✗ "nih found X effective" → ✓ "nih validates X" or "nih recommends X"
       ✗ "team got tests" → ✓ "team received tests"
       ✗ "testing was sluggish" → DROP (vague adjective, not a factual relation)
       ✗ "company ships vaccine" → resolve "company" to actual name, keep "ships"
       ✗ "organization hosts call" → DROP (not a factual relation about the world)
       ✗ "california reports large tests" → ✓ "california conducts tests" or DROP if vague
    10. Prefer concrete factual predicates over generic reporting verbs.
    11. Negative predicates are allowed ONLY when they preserve factual meaning.
        Good examples: [denies, rejects, refutes, does_not_cure]

    ENTITY CLEANING & LITERALS (CRITICAL):
    12. Subjects and objects MUST be concrete nouns, noun phrases, named entities, or compact factual concepts.
    13. NEVER extract as subject or object:
        - Specific quantities, numbers, or percentages. You MUST generalize them (e.g., instead of "1492 people" extract "people"; instead of "58 tests" extract "tests").
        - Vague or overly broad concepts (e.g., "leaders", "transparency", "data", "things", "results").
        - Temporal expressions: "this month", "today", "last week" (unless part of a named event).
        - Standalone adjectives or adverbs: "sluggish", "effective", "quickly".
        - Full clauses, sentence fragments, or emotional states.
        - 'none', 'null', 'n/a', 'it', 'this', 'the article'.
    14. Objects MUST be compact (ideally 1-3 words). If an object exceeds 4 words, shorten it to the core concept.

    COREFERENCE RESOLUTION (CRITICAL):
    15. Resolve ALL referential expressions to their actual entity names based on context:
        - Pronouns: he, she, they, we, it → actual entity name
        - Generic nouns: "the company", "the organization", "the agency" → actual name (e.g., "moderna", "who", "cdc")
        - If "we" refers to an organization, write the organization's name.
    16. NEVER use "company", "the organization", "the agency", "the team" etc. as subjects or objects if the actual name is identifiable from context.

    FACTUALITY FILTER (VERY IMPORTANT):
    17. Extract only concrete factual relations that could help future fact-checking retrieval.
    18. Do NOT extract:
        - Emotional reactions or opinions
        - Vague state descriptions (e.g., "X was sluggish", "Y was bad")
        - Rhetorical or narrative filler
        - Meta-fact-checking statements unless they describe a concrete factual relation
    19. Prefer relations about: actors, medical treatments, policy actions, denials, confirmations, causes, locations, and measurable effects.
    20. If NO factual relationships exist, output EXACTLY:
    {{ "triples": [] }}

    REDUNDANCY CONTROL (CRITICAL):
    21. Do NOT extract multiple triples that express the same core fact with only minor wording differences.
    22. If several candidate triples are semantically equivalent, keep only the most specific and informative one.
        ✗ WRONG (near-duplicates):
          {{"subject": "utah jazz", "predicate": "received", "object": "58 coronavirus tests"}}
          {{"subject": "utah jazz", "predicate": "got", "object": "coronavirus tests in hours"}}
        ✓ CORRECT (keep only the best one):
          {{"subject": "utah jazz", "predicate": "received", "object": "58 coronavirus tests"}}
    23. When multiple agents perform the same action on the same target, prefer a SINGLE triple with a grouped subject or a consolidated predicate rather than N near-identical triples.
        ✗ WRONG (3 triples that are really 1 fact):
          {{"subject": "vaporized hydrogen peroxide", "predicate": "sanitizes", "object": "masks"}}
          {{"subject": "uv light", "predicate": "sanitizes", "object": "masks"}}
          {{"subject": "heat", "predicate": "sanitizes", "object": "masks"}}
        ✓ BETTER (1 consolidated triple + 1 attribution):
          {{"subject": "nih", "predicate": "recommends", "object": "mask sanitization methods"}}
        Or if individual methods matter, keep AT MOST 2-3 of the most informative triples.
    24. Aim for 1-4 high-quality triples per text chunk. More than 5 usually indicates redundancy.

    TEXT TO PROCESS:
    {text_chunk}

    OUTPUT JSON ONLY:
    """

    @staticmethod
    def get_prompts_for_chunk(text_chunk: str) -> tuple[str, str]:
        system_prompt = PromptTemplates.get_system_prompt_for_ingestion()
        user_prompt = PromptTemplates.get_user_prompt_template_for_ingestion().format(
            text_chunk=text_chunk
        )
        return system_prompt, user_prompt

    @staticmethod
    def get_system_prompt_for_live() -> str:
        return """
    You are an advanced AI expert in Knowledge Graph Engineering and Semantic Analysis.
    Your task is to extract factual Subject-Predicate-Object (SPO) triples from a user claim and its supporting evidence.

    A prior verification step already produced a verdict.
    You must respect that verdict and separate:
    1. what the user claimed (claimed_triples)
    2. what the evidence actually verifies (verified_triples)

    Your goals:
    - identify the main factual relations
    - normalize predicates into canonical forms
    - resolve pronouns to their actual entities
    - avoid vague, emotional, rhetorical, or meta statements
    - keep subjects and objects concise and canonical
    - return only strict JSON
    """

    @staticmethod
    def get_user_prompt_template_for_live() -> str:
        return """
Extract Subject-Predicate-Object (S-P-O) triples based on the provided CLAIM, VERDICT, EXPLANATION, and EVIDENCE.

PREVIOUS ANALYSIS CONTEXT:
- verdict: {verdict}
- explanation: {explanation}

STRICT RULES:
1. Output ONLY valid JSON.
2. Use EXACTLY this structure:
{{
  "claimed_triples": [
    {{ "subject": "...", "predicate": "...", "object": "..." }}
  ],
  "verified_triples": [
    {{ "subject": "...", "predicate": "...", "object": "..." }}
  ]
}}
3. Keys MUST be exactly: "subject", "predicate", "object".
4. Subjects and objects MUST be lowercase. Predicates should be lowercase canonical forms; the system will normalize them to Neo4j relation format later.


PREDICATE NORMALIZATION (CRITICAL):
5. You MUST map each relationship to a CANONICAL PREDICATE.
6. Preferred predicates: [
  supports, opposes, implements, causes, can_cause, criticizes, located_in,
  is_a, affects, acquired, banned, denies, rejects, confirms, refutes, spreads,
  does_not_spread, reduces, increases, recommends, treats, cures, prevents,
  helps_prevent, reduces_risk_of, protects, targets, validates, develops,
  ships, conducts, funds, approves, authorizes, sanctions,
  does_not_cure, does_not_prevent, does_not_protect, does_not_worsen,
  does_not_cause, reduces_mortality, increases_risk, does_not_increase_risk,
  sanitizes, decontaminates
]
7. If none fit, create a 1-word, 2-word, or compact canonical predicate. Prefer specific negative predicates like does_not_cure over generic forms like does_not.
8. NEVER use full sentences as predicates.
9. Negative predicates are allowed ONLY when they preserve factual meaning.
10. Prefer concrete factual predicates over generic reporting verbs.

ENTITY CLEANING & LITERALS (CRITICAL):
11. Subjects and objects MUST be concrete nouns, noun phrases, named entities, or compact factual concepts.
12. NEVER extract as subject or object:
    - Specific quantities, numbers, or percentages. You MUST generalize them (e.g., instead of "1492 people" extract "people"; instead of "58 tests" extract "tests").
    - Vague or overly broad concepts (e.g., "leaders", "transparency", "data", "things", "results").
    - Temporal expressions: "this month", "today", "last week" (unless part of a named event).
    - Standalone adjectives or adverbs: "sluggish", "effective", "quickly".
    - Full clauses, sentence fragments, or emotional states.
    - 'none', 'null', 'n/a', 'it', 'this', 'the article'.
13. Objects MUST be compact (ideally 1-3 words). If an object exceeds 4 words, shorten it to the core concept.

COREFERENCE RESOLUTION (CRITICAL):
14. Resolve pronouns (he, she, they, we, it) to their actual entity names.
15. If "we" refers to an organization, write the organization's name.

FACTUALITY FILTER (VERY IMPORTANT):
16. Extract only concrete factual relations.
17. Do NOT extract:
   - emotional reactions
   - rhetorical filler
   - vague narrative phrases
   - meta-fact-checking statements like "this claim is false"
18. Prefer relations about actors, actions, denials, confirmations, recommendations, causes, treatments, and disease-related effects.
19. If no factual relationships exist, return empty arrays.

REDUNDANCY CONTROL (CRITICAL):
20. Do NOT extract multiple triples that express the same core fact with only minor wording differences.
21. Keep only the most specific and informative version of each fact.
22. Prefer compact canonical objects over long descriptions.
23. Objects MUST be highly compact, ideally 1-3 words. Do NOT include long conditions, demographics, or prepositional phrases in the object.
BAD OBJECT: 'mortality in critically ill covid-19 patients'
GOOD OBJECT: 'mortality' (or 'covid-19 mortality')

EXTRACTION LOGIC:
24. "claimed_triples":
   - Extract what the user asserted from the CLAIM text.
   - If the user claim is false, still extract it here as the claimed version.
25. "verified_triples":
   - If verdict is TRUE: extract the true facts that support the claim.
   - If verdict is FALSE:
     * Extract ONLY from the CORRECTED CLAIM (provided below) and/or the evidence-supported correction.
     * Do NOT extract triples from the original false claim.
     * Use specific negative predicates (e.g., does_not_spread, does_not_cure) to express the corrected fact.
   - If verdict is NEUTRAL: return "verified_triples": [].
   - Prefer atomic factual triples.
   - Do NOT use generic negative predicates like "does_not" if a more specific form like "does_not_cure" is possible.
26. Do NOT restate the false claim inside "verified_triples".

META-TRIPLE PROHIBITION (CRITICAL):
27. NEVER extract triples where the subject or object is a meta-level concept about the fact-checking process itself.
28. FORBIDDEN subjects/objects: "evidence", "claim", "source", "passage", "proof", "studies", "research",
    "experts", "scientists", "findings", "data", "analysis", "lack of evidence", "link", "connection",
    "support", "lack of support", "no evidence", "scientific consensus".
29. Triples must describe REAL-WORLD entities and their relationships, NOT statements about what evidence shows.
    ✗ WRONG: {{"subject": "evidence", "predicate": "does_not_support", "object": "5g covid-19 link"}}
    ✓ CORRECT: {{"subject": "5g networks", "predicate": "does_not_spread", "object": "covid-19"}}
    ✗ WRONG: {{"subject": "studies", "predicate": "show", "object": "garlic ineffectiveness"}}
    ✓ CORRECT: {{"subject": "garlic", "predicate": "does_not_cure", "object": "covid-19"}}

TEXT TO PROCESS:
CLAIM: "{claim_text}"

CORRECTED CLAIM (use this as the source for verified_triples when verdict is FALSE):
{corrected_claim}

EVIDENCE:
{evidence_text}

OUTPUT JSON ONLY:
"""

    @staticmethod
    def format_live_extraction_prompt(
        claim_text: str,
        verdict: str,
        explanation: str,
        evidence_text: str,
        corrected_claim: str = ""
    ) -> str:
        template = PromptTemplates.get_user_prompt_template_for_live()
        return template.format(
            claim_text=claim_text,
            verdict=verdict,
            explanation=explanation,
            evidence_text=evidence_text,
            corrected_claim=corrected_claim or "N/A (verdict is not FALSE)"
        )

    @staticmethod
    def get_prompts_for_extraction(
        claim_text: str,
        verdict: str,
        explanation: str,
        evidence_text: str,
        corrected_claim: str = ""
    ) -> tuple[str, str]:
        system_prompt = PromptTemplates.get_system_prompt_for_live()
        user_prompt = PromptTemplates.format_live_extraction_prompt(
            claim_text=claim_text,
            verdict=verdict,
            explanation=explanation,
            evidence_text=evidence_text,
            corrected_claim=corrected_claim
        )
        return system_prompt, user_prompt

