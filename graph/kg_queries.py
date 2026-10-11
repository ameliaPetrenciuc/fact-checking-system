def create_or_update_claim(tx, claim_id, text, raw_text, label, embedding):
    if not embedding or len(embedding) != 768:
        raise ValueError(
            f"Claim {claim_id}: embedding must be a list of 768 floats, "
            f"got {len(embedding) if embedding else 0} dimensions."
        )

    query = """
        MERGE (c:Claim {id: $id})
        SET c.text = $text,
            c.raw_text = $raw_text,
            c.label = $label,
            c.source_type = 'dataset',
            c.embedding = $embedding,
            c.created_at = coalesce(c.created_at, datetime()),
            c.updated_at = datetime()
        """
    tx.run(query, id=claim_id, text=text, raw_text=raw_text, label=label, embedding=embedding)



