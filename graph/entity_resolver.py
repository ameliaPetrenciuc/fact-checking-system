import re
import unicodedata
from rapidfuzz import fuzz


FUZZY_ENTITY_THRESHOLD = 95

CANONICAL_ALIASES = {
    # COVID-19 variants
    "coronavirus":       "covid19",
    "coronavirus19":     "covid19",
    "covid":             "covid19",
    "sarscov2":          "covid19",
    "2019ncov":          "covid19",
    "novelcoronavirus":  "covid19",
    "newcoronavirus":    "covid19",
    "coronavirusdisease": "covid19",
    "wuhanvirus":        "covid19",
    "chinavirus":        "covid19",
    # WHO variants
    "worldhealthorg":             "who",
    "worldhealthorganization":    "who",
    "worldhealthorganisation":    "who",
    # CDC variants
    "centersfordiseasecontrol":            "cdc",
    "centersfordiseasecontrolandprevention": "cdc",
    # NIH variants
    "nationalinstitutesofhealth":  "nih",

    "death":      "mortality",
    "deaths":     "mortality",
    "fatality":   "mortality",
    "fatalities": "mortality",

    # Vaccine variants
    "vaccination": "vaccine",
    "vaccine":     "vaccine",
    "vaccines":    "vaccine",

    # Population variants
    "worldpopulation":  "globalpopulation",
    "globalpopulation": "globalpopulation",

}

# Canonical display names for known canonical keys
CANONICAL_DISPLAY = {
    "covid19": "covid-19",
    "who": "who",
    "cdc": "cdc",
    "nih": "nih",
    "mortality": "mortality",
    "vaccine": "vaccine",
    "globalpopulation": "global population",
}


def canonicalize_key(compact_key: str) -> str:
    return CANONICAL_ALIASES.get(compact_key, compact_key)


def normalize_entity_key(name: str) -> str:
    if not name:
        return ""

    name = name.lower().strip()
    name = unicodedata.normalize("NFKD", name)
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    return name


def compact_entity_key(name: str) -> str:
    return normalize_entity_key(name).replace(" ", "")


def _add_entity_alias(tx, name_key: str, raw_alias: str):

    raw_alias_clean = raw_alias.strip()
    alias_key = compact_entity_key(raw_alias_clean)

    tx.run("""
        MATCH (e:Entity {name_key: $name_key})
        SET e.aliases =
            CASE
                WHEN e.aliases IS NULL THEN [$raw_alias]
                WHEN $raw_alias IN e.aliases THEN e.aliases
                ELSE e.aliases + $raw_alias
            END,
            e.alias_keys =
            CASE
                WHEN e.alias_keys IS NULL THEN
                    CASE
                        WHEN $alias_key = $name_key THEN [$name_key]
                        ELSE [$name_key, $alias_key]
                    END
                WHEN $name_key IN e.alias_keys AND $alias_key IN e.alias_keys THEN e.alias_keys
                WHEN $name_key IN e.alias_keys THEN e.alias_keys + $alias_key
                WHEN $alias_key IN e.alias_keys THEN e.alias_keys + $name_key
                ELSE e.alias_keys + $name_key + $alias_key
            END
    """, name_key=name_key, raw_alias=raw_alias_clean, alias_key=alias_key)

def resolve_entity(tx, raw_name: str) -> dict:

    if not raw_name or not raw_name.strip():
        raise ValueError("Entity name cannot be empty.")

    raw_alias = raw_name.strip()
    raw_display_name = raw_alias.lower().strip()
    raw_compact_key = compact_entity_key(raw_alias)

    if not raw_compact_key:
        raise ValueError(f"Invalid entity name after normalization: {raw_name}")

    name_key = canonicalize_key(raw_compact_key)

    display_name = CANONICAL_DISPLAY.get(name_key, raw_display_name)
    name_norm = normalize_entity_key(display_name)

    if name_key != raw_compact_key or display_name != raw_display_name:
        print(
            f"[EntityResolver] Canonical alias: '{raw_display_name}' -> '{display_name}' "
            f"(key: {raw_compact_key} -> {name_key})"
        )

    result = tx.run("""
        MATCH (e:Entity)
        WHERE e.name_key = $name_key
           OR $name_key IN coalesce(e.alias_keys, [])
           OR $raw_alias_key IN coalesce(e.alias_keys, [])
        RETURN e.name AS name,
               e.name_norm AS name_norm,
               e.name_key AS name_key
        LIMIT 1
    """, name_key=name_key, raw_alias_key=raw_compact_key).single()

    if result:
        _add_entity_alias(tx, result["name_key"], raw_alias)
        return {
            "name": result["name"],
            "name_norm": result["name_norm"],
            "name_key": result["name_key"]
        }

    candidates = tx.run("""
        MATCH (e:Entity)
        WHERE e.name_key IS NOT NULL
          AND left(e.name_key, 1) = left($name_key, 1)
          AND abs(size(e.name_key) - size($name_key)) <= 3
        RETURN e.name AS name,
               e.name_norm AS name_norm,
               e.name_key AS name_key
        LIMIT 1000
    """, name_key=name_key).data()

    best_candidate = None
    best_score = 0

    for candidate in candidates:
        candidate_key = candidate["name_key"]
        score = fuzz.ratio(name_key, candidate_key)

        if score > best_score:
            best_score = score
            best_candidate = candidate

    if best_candidate and best_score >= FUZZY_ENTITY_THRESHOLD:
        _add_entity_alias(tx, best_candidate["name_key"], raw_alias)

        print(
            f"[EntityResolver] '{raw_display_name}' -> '{best_candidate['name']}' "
            f"(fuzzy score: {best_score})"
        )

        return {
            "name": best_candidate["name"],
            "name_norm": best_candidate["name_norm"],
            "name_key": best_candidate["name_key"]
        }

    tx.run("""
        MERGE (e:Entity {name_key: $name_key})
        ON CREATE SET
            e.name = $display_name,
            e.name_norm = $name_norm,
            e.aliases = [$raw_alias],
            e.alias_keys =
                CASE
                    WHEN $raw_alias_key = $name_key THEN [$name_key]
                    ELSE [$name_key, $raw_alias_key]
                END
        ON MATCH SET
            e.aliases =
                CASE
                    WHEN e.aliases IS NULL THEN [$raw_alias]
                    WHEN $raw_alias IN e.aliases THEN e.aliases
                    ELSE e.aliases + $raw_alias
                END,
            e.alias_keys =
                CASE
                    WHEN e.alias_keys IS NULL THEN
                        CASE
                            WHEN $raw_alias_key = $name_key THEN [$name_key]
                            ELSE [$name_key, $raw_alias_key]
                        END
                    WHEN $raw_alias_key IN e.alias_keys THEN e.alias_keys
                    ELSE e.alias_keys + $raw_alias_key
                END
    """,
        name_key=name_key,
        raw_alias_key=raw_compact_key,
        name_norm=name_norm,
        display_name=display_name,
        raw_alias=raw_alias
    )

    print(f"[EntityResolver] '{raw_display_name}' -> created new entity as '{display_name}'")

    return {
        "name": display_name,
        "name_norm": name_norm,
        "name_key": name_key
    }

def create_entity_key_index(tx):
    tx.run("""
        CREATE INDEX entity_name_key_index IF NOT EXISTS
        FOR (e:Entity) ON (e.name_key)
    """)

    tx.run("""
        CREATE INDEX entity_name_norm_index IF NOT EXISTS
        FOR (e:Entity) ON (e.name_norm)
    """)

    print("[✓] Entity indexes created or already exist.")


def resolve_entity_pair(tx, raw_subject: str, raw_object: str) -> tuple:

    subject_info = resolve_entity(tx, raw_subject)
    object_info = resolve_entity(tx, raw_object)
    return subject_info, object_info