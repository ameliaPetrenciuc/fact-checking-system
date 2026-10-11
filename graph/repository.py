from graph.entity_resolver import resolve_entity_pair
from server.ai_client import get_embedding

def get_claim_score(tx, claim_id):
    query = "MATCH (c:Claim {id: $id}) RETURN c.kg_score AS score"
    result = tx.run(query, id=claim_id)
    record = result.single()
    return record["score"] if record else None


def get_entities_for_claim(tx, claim_id):
    query = "MATCH (c:Claim {id: $id})-[:MENTIONS]->(e:Entity) RETURN e.name AS entity"
    result = tx.run(query, id=claim_id)
    return [record["entity"] for record in result]


def get_other_claim_labels_for_entity(tx, entity_name, current_claim_id):
    query = """
        MATCH (e:Entity {name: $name})<-[:MENTIONS]-(other:Claim)
        WHERE other.id <> $current_id
        RETURN other.label AS label
        """
    result = tx.run(query, name=entity_name, current_id=current_claim_id)
    return [record["label"] for record in result]


def get_claim_data(tx, claim_id):
    text_res = tx.run("MATCH (c:Claim {id: $id}) RETURN c.text AS text", id=claim_id)
    text = text_res.single()["text"]

    ent_res = tx.run(
        "MATCH (c:Claim {id: $id})-[:MENTIONS]->(e:Entity) RETURN e.name AS entity",
        id=claim_id
    )
    entities = [record["entity"] for record in ent_res]

    return text, entities


def get_claim_data_with_label(tx, claim_id):

    query = """
    MATCH (c:Claim {id: $id}) 
    RETURN c.text AS text, c.label AS label
    """

    result = tx.run(query, id=claim_id)
    record = result.single()

    if not record:
        return None, None

    text = record["text"]
    label = record["label"]

    return text, label


def get_claim_decision_data(tx, claim_id):
    query = """
    MATCH (c:Claim {id: $id})
    RETURN c.kg_score AS score, 
           c.decision AS decision
    """
    result = tx.run(query, id=claim_id)
    return result.single()


def get_knowledge_graph_facts(tx, subject_name, object_name):
    query = """
    MATCH (s:Entity {name: $sub})
    MATCH (o:Entity {name: $obj})
    // Căutăm orice relație între ele care a fost marcată ca verificată (din surse sigure)
    MATCH (s)-[r]->(o)
    WHERE r.verified = true
    RETURN type(r) AS predicate, 
           r.source AS source, 
           r.timestamp AS date
    """
    result = tx.run(query, sub=subject_name.lower().strip(), obj=object_name.lower().strip())

    return [dict(record) for record in result]


def store_decision(tx, claim_id, decision):
    query = """
    MATCH (c:Claim {id: $id})
    SET c.decision = $decision,
        c.decision_updated_at = datetime()
    """
    tx.run(query, id=claim_id, decision=decision)


def save_llm_verdict(tx, claim_id, verdict, explanation, source_url, claim_text):

    embedding_vector = get_embedding(claim_text)

    query = """
    MATCH (c:Claim {id: $id})
    SET c.verdict = $verdict,
        c.explanation = $explanation,
        c.source_url = $source_url,
        c.status = 'VERIFIED_BY_LLM',
        c.verified_at = datetime(),
        c.embedding = $embedding
    """
    tx.run(query, id=claim_id, verdict=verdict, explanation=explanation, source_url=source_url, embedding=embedding_vector)


def save_web_result_to_graph(
    tx,
    false_claim_text,
    true_claim_text,
    explanation,
    source_url,
    verified_triples
):
    false_claim_embedding = get_embedding(false_claim_text) if false_claim_text else None
    true_claim_embedding = get_embedding(true_claim_text) if true_claim_text else None

    enriched_triples = _resolve_and_enrich_triples(tx, verified_triples)

    # caz: salvăm doar claim adevărat
    if true_claim_text and not false_claim_text:
        query = """
        MERGE (true_claim:Claim {text: $true_claim_text})
        ON CREATE SET true_claim.created_at = datetime()
        SET true_claim.verdict = 'TRUE',
            true_claim.explanation = $explanation,
            true_claim.source_url = $source_url,
            true_claim.source_type = 'web_search',
            true_claim.verified_at = datetime(),
            true_claim.embedding = $true_claim_embedding

        WITH true_claim
        UNWIND CASE WHEN size($verified_triples) > 0 THEN $verified_triples ELSE [null] END AS triple
        WITH true_claim, triple WHERE triple IS NOT NULL

        WITH true_claim, triple,
             toLower(trim(triple.subject)) AS s_norm,
             toLower(trim(triple.object)) AS o_norm,
             toUpper(replace(replace(trim(triple.predicate), ' ', '_'), '-', '_')) AS p_norm

        MERGE (s:Entity {name_key: triple.subject_key})
        ON CREATE SET s.name = triple.subject, s.created_at = datetime()
        MERGE (o:Entity {name_key: triple.object_key})
        ON CREATE SET o.name = triple.object, o.created_at = datetime()

        MERGE (vf:Fact:VerifiedFact {
            subject_norm: s_norm,
            predicate_norm: p_norm,
            object_norm: o_norm
        })
        SET vf.subject = triple.subject,
            vf.predicate = triple.predicate,
            vf.object = triple.object,
            vf.text = triple.text,
            vf.truth_status = 'verified',
            vf.source_type = 'web_search',
            vf.source_claim_text = true_claim.text,
            vf.embedding = triple.embedding

        MERGE (true_claim)-[:JUSTIFIED_BY]->(vf)
        MERGE (vf)-[:ABOUT]->(s)
        MERGE (vf)-[:ABOUT]->(o)

        WITH s, o, p_norm, true_claim
        CALL apoc.merge.relationship(
            s,
            p_norm,
            {},
            {
                verified: true,
                source_claim_text: true_claim.text,
                source_type: 'web_search'
            },
            o
        ) YIELD rel

        RETURN count(rel) AS created_relationships
        """
        tx.run(
            query,
            true_claim_text=true_claim_text,
            true_claim_embedding=true_claim_embedding,
            explanation=explanation,
            source_url=source_url,
            verified_triples=enriched_triples
        )
        return

    # caz: salvăm claim fals + claim corectat
    if true_claim_text and false_claim_text:
        query = """
        MERGE (false_claim:Claim {text: $false_claim_text})
        ON CREATE SET false_claim.created_at = datetime()
        SET false_claim.verdict = 'FALSE',
            false_claim.explanation = $explanation,
            false_claim.source_url = $source_url,
            false_claim.source_type = 'web_search',
            false_claim.verified_at = datetime(),
            false_claim.embedding = $false_claim_embedding

        MERGE (true_claim:Claim {text: $true_claim_text})
        ON CREATE SET true_claim.created_at = datetime()
        SET true_claim.verdict = 'TRUE',
            true_claim.explanation = $explanation,
            true_claim.source_url = $source_url,
            true_claim.source_type = 'web_search',
            true_claim.verified_at = datetime(),
            true_claim.embedding = $true_claim_embedding

        MERGE (false_claim)-[:CORRECTED_BY]->(true_claim)

        WITH true_claim
        UNWIND CASE WHEN size($verified_triples) > 0 THEN $verified_triples ELSE [null] END AS triple
        WITH true_claim, triple WHERE triple IS NOT NULL

        WITH true_claim, triple,
             toLower(trim(triple.subject)) AS s_norm,
             toLower(trim(triple.object)) AS o_norm,
             toUpper(replace(replace(trim(triple.predicate), ' ', '_'), '-', '_')) AS p_norm

        MERGE (s:Entity {name_key: triple.subject_key})
        ON CREATE SET s.name = triple.subject, s.created_at = datetime()
        MERGE (o:Entity {name_key: triple.object_key})
        ON CREATE SET o.name = triple.object, o.created_at = datetime()

        MERGE (vf:Fact:VerifiedFact {
            subject_norm: s_norm,
            predicate_norm: p_norm,
            object_norm: o_norm
        })
        SET vf.subject = triple.subject,
            vf.predicate = triple.predicate,
            vf.object = triple.object,
            vf.text = triple.text,
            vf.truth_status = 'verified',
            vf.source_type = 'web_search',
            vf.source_claim_text = true_claim.text,
            vf.embedding = triple.embedding

        MERGE (true_claim)-[:JUSTIFIED_BY]->(vf)
        MERGE (vf)-[:ABOUT]->(s)
        MERGE (vf)-[:ABOUT]->(o)

        WITH s, o, p_norm, true_claim
        CALL apoc.merge.relationship(
            s,
            p_norm,
            {},
            {
                verified: true,
                source_claim_text: true_claim.text,
                source_type: 'web_search'
            },
            o
        ) YIELD rel

        RETURN count(rel) AS created_relationships
        """
        tx.run(
            query,
            false_claim_text=false_claim_text,
            true_claim_text=true_claim_text,
            false_claim_embedding=false_claim_embedding,
            true_claim_embedding=true_claim_embedding,
            explanation=explanation,
            source_url=source_url,
            verified_triples=enriched_triples
        )

def _resolve_and_enrich_triples(tx, triples):

    enriched_triples = []

    if not triples:
        return enriched_triples

    for t in triples:
        resolved_subject, resolved_object = resolve_entity_pair(
            tx,
            t["subject"],
            t["object"]
        )

        predicate = t["predicate"]

        fact_text = (
            f"{resolved_subject['name']} "
            f"{predicate} "
            f"{resolved_object['name']}"
        )

        fact_embedding = get_embedding(fact_text)

        enriched_triples.append({
            "subject": resolved_subject["name"],
            "subject_key": resolved_subject["name_key"],
            "predicate": predicate,
            "object": resolved_object["name"],
            "object_key": resolved_object["name_key"],
            "text": fact_text,
            "embedding": fact_embedding
        })

    return enriched_triples


def ingest_initial_claim(tx, claim_id, label, triples):
    if not triples:
        return 0

    normalized_label = str(label).lower().strip()

    enriched_triples = _resolve_and_enrich_triples(tx, triples)

    if normalized_label == "real":
        query = """
        MATCH (c:Claim {id: $claim_id})
        UNWIND $triples AS triple

        WITH c, triple,
             toLower(trim(triple.subject)) AS s_norm,
             toLower(trim(triple.object)) AS o_norm,
             toUpper(replace(replace(trim(triple.predicate), ' ', '_'), '-', '_')) AS p_norm,
             trim(triple.subject) AS s_raw,
             trim(triple.object) AS o_raw,
             trim(triple.predicate) AS p_raw

        MATCH (s:Entity {name_key: triple.subject_key})
        MATCH (o:Entity {name_key: triple.object_key})
        
        MERGE (vf:Fact:VerifiedFact {
            subject_norm: s_norm,
            predicate_norm: p_norm,
            object_norm: o_norm
        })
        SET vf.subject = s_raw,
            vf.predicate = p_raw,
            vf.object = o_raw,
            vf.text = triple.text,
            vf.source_type = 'dataset',
            vf.truth_status = 'verified',
            vf.embedding = triple.embedding

        MERGE (c)-[r:JUSTIFIED_BY]->(vf)
        SET r.source_claim_id = c.id,
            r.source_type = 'dataset',
            r.created_at = coalesce(r.created_at, datetime())
        MERGE (vf)-[:ABOUT]->(s)
        MERGE (vf)-[:ABOUT]->(o)

        WITH s, o, p_norm, c, vf
        CALL apoc.merge.relationship(
            s,
            p_norm,
            {},
            {
                verified: true,
                source_claim_id: c.id,
                source_type: 'dataset'
            },
            o
        ) YIELD rel

        RETURN count(vf) AS count_result
        """
    else:
        query = """
        MATCH (c:Claim {id: $claim_id})
        UNWIND $triples AS triple
        
        WITH c, triple,
             toLower(trim(triple.subject)) AS s_norm,
             toLower(trim(triple.object)) AS o_norm,
             toUpper(replace(replace(trim(triple.predicate), ' ', '_'), '-', '_')) AS p_norm,
             trim(triple.subject) AS s_raw,
             trim(triple.object) AS o_raw,
             trim(triple.predicate) AS p_raw
        
        MATCH (s:Entity {name_key: triple.subject_key})
        MATCH (o:Entity {name_key: triple.object_key})
        
        MERGE (cf:Fact:ClaimedFact {
            subject_norm: s_norm,
            predicate_norm: p_norm,
            object_norm: o_norm
        })
        SET cf.subject = s_raw,
            cf.predicate = p_raw,
            cf.object = o_raw,
            cf.text = triple.text,
            cf.source_type = 'dataset',
            cf.truth_status = CASE
                WHEN $label = 'fake' THEN 'claimed_false'
                ELSE 'unverified'
            END,
            cf.embedding = triple.embedding
        
        MERGE (c)-[r:ASSERTS]->(cf)
        SET r.source_claim_id = c.id,
            r.source_type = 'dataset',
            r.created_at = coalesce(r.created_at, datetime())
        MERGE (cf)-[:ABOUT]->(s)
        MERGE (cf)-[:ABOUT]->(o)
        
        RETURN count(cf) AS count_result
        """

    res = tx.run(
        query,
        claim_id=int(claim_id),
        triples=enriched_triples,
        label=normalized_label
    )
    record = res.single()
    return record["count_result"] if record else 0

