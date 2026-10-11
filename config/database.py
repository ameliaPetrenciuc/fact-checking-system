from neo4j import GraphDatabase
from config.settings import URI, USER, PASSWORD, DATABASE_NAME

try:
    neo4j_driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    print("[✓] Conexiunea globală la Neo4j a fost stabilită cu succes!")
except Exception as e:
    print(f"[X] Eroare la conectarea Neo4j: {e}")

def get_session():
    return neo4j_driver.session(database=DATABASE_NAME)