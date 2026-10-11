import os

from dotenv import load_dotenv

load_dotenv()

# ── Neo4j ──
URI = os.getenv(
    "NEO4J_URI",
    "bolt://localhost:7687",
)

USER = os.getenv(
    "NEO4J_USER",
    "neo4j",
)

PASSWORD = os.getenv(
    "NEO4J_PASSWORD",
    "",
)

# DATABASE_NAME = os.getenv(
#     "NEO4J_DATABASE",
#     "licentafinalv2licentatest",
# )
DATABASE_NAME = os.getenv(
    "NEO4J_DATABASE",
    "licentafinalv2licentatest",
)

# ── Web evidence configuration ──
CHUNK_SIZE = 100
CHUNK_OVERLAP = 25

MAX_SOURCES = 5
MIN_CHARS = 300

# ── API keys ──
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

# ── Retrieval Thresholds ──
KG_CANDIDATE_THRESHOLD = 0.75
HIGH_SIMILARITY_THRESHOLD = 0.85

# Legacy alias
SIMILARITY_THRESHOLD = KG_CANDIDATE_THRESHOLD

SHORT_QUERY_WORD_LIMIT = 6
MICRO_PREFERENCE_GAP = 0.03

# ── Graph-Aware Confidence Thresholds ──
LOW_CONFIDENCE_THRESHOLD = 0.50
HIGH_CONFIDENCE_THRESHOLD = 0.75
NEUTRAL_CONFIDENCE_THRESHOLD = 0.62

NEUTRAL_NLI_MIN_SIMILARITY = 0.88
