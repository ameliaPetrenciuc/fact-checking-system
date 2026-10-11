import re
import os

from openai import OpenAI

TOGETHER_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

client = OpenAI(
    base_url="https://api.together.xyz/v1",
    api_key=os.getenv("TOGETHER_API_KEY"),
)


def clean_query_output(text: str) -> str:
    forbidden_phrases = ["i can help", "however", "i need to", "i'm sorry", "correction"]
    lowercase_text = text.lower()

    for phrase in forbidden_phrases:
        if phrase in lowercase_text:
            return ""

    return text.strip().replace('"', '').replace("'", "")


def generate_search_query(raw_claim: str) -> str:
    try:
        _client = OpenAI(
            base_url="https://api.together.xyz/v1",
            api_key=os.getenv("TOGETHER_API_KEY"),
        )
    except Exception as e:
        print(f"❌ Eroare la inițializarea clientului LLM: {e}")
        return f"covid-19 {' '.join(raw_claim.split()[:8])}"

    citate = re.findall(r'"([^"]*)"|\'([^\']*)\'', raw_claim)
    citat_ancora = ""

    for match in citate:
        text_citat = match[0] if match[0] else match[1]
        words = text_citat.split()
        if 3 <= len(words) <= 8:
            citat_ancora = f'"{text_citat}"'
            break

    system_instruction = """
        Role: You are an Investigative Query Optimizer for a Fact-Checking system.
    
        Task: Convert the claim into ONE high-precision search query, usually 5-12 keywords, designed to find reliable and scrapable evidence that supports or refutes the claim. 
        For numeric/statistical claims, preserving numbers, dates, locations, and measured outcomes is more important than keeping the query short.
        
        STRICT RULES:
        1. OUTPUT ONLY THE SEARCH KEYWORDS. No explanations, no filler, no quotation marks.
        2. Add words like fact check, debunk, reality check, or investigation ONLY if the claim is an accusation, conspiracy, viral rumor, image/video claim, or misinformation-style claim.
        3. For biomedical, scientific, clinical, or treatment claims, DO NOT add fact check, debunk, reality check, or investigation by default.
        4. For biomedical or treatment claims, preserve drug names, disease names, outcomes, numbers, dates, institutions, and technical terms.
        5. Include obvious medical synonyms when useful:
           - Actemra = tocilizumab
           - interleukin-6 = IL-6
           - risk of death = mortality death survival
           - SARS-CoV-2 = covid-19 coronavirus
        6. ACTION FOCUS: Do not extract only names. Keep the core factual relation or outcome.
        7. COVID-19 CONTEXT: For pandemic-related claims, 
        include covid-19 only if it does not replace more specific anchors such as exact numbers, dates, locations, outcomes, study terms, or institutions.
        8. GEOGRAPHIC/ENTITY PRECISION: Always keep specific entities such as WHO, CDC, countries, universities, hospitals, doctors, journals, or study names.
        9. NUMERIC PRECISION: Always keep exact numbers, percentages, dates, time periods, quantities, locations, and measured outcomes if present.
         For rounded numbers, keep the number from the claim, but also keep strong non-numeric anchors because the source may report a slightly different precise value.
        10. SEARCH OPERATOR: Use only space-separated terms.
        11. EXCESS MORTALITY CLAIMS: For claims about deaths higher than expected, include useful terms such as excess deaths, excess mortality, all-cause mortality, expected deaths.    
        12. DEMOGRAPHIC CLAIMS: For claims about births, birthrates, fertility, natality, pregnancy, miscarriage, stillbirth, infant outcomes, or population change, preserve the demographic outcome and include useful synonyms
         such as births, birth rate, natality, fertility, pregnancy, stillbirth when relevant.
        13. COMPARATIVE CLAIMS: For claims comparing two groups using greater than, less than, higher than, lower than, more than, fewer than, or compared with, preserve both groups but use neutral statistical terms such as proportion, percentage, prevalence, rate, comparison, estimate, systematic review, or meta-analysis. Do not only search the claimed direction; make the query able to find evidence for either direction.
        Examples:
        Claim: "NYT invented the video of a doctor fighting coronavirus in hospital."
        Query: NYT invented video doctor hospital coronavirus fact check debunk
    
        Claim: "The government is hiding the real number of cases in London."
        Query: UK government hiding covid-19 cases London reality check
    
        Claim: "Drinking bleach cures covid-19 according to a new study."
        Query: drinking bleach cure covid-19 study fact check debunk
    
        Claim: "Actemra lowers the risk of death in COVID-19 patients with high levels of interleukin-6."
        Query: Actemra tocilizumab covid-19 IL-6 mortality death risk
    
        Claim: "Researchers at the University of Hong Kong estimated around 232,000 COVID-19 cases in China by late February 2020."
        Query: University Hong Kong 232000 covid-19 cases China February 2020 Lancet
    
        Claim: "The SARS-CoV-2 particles found in infected patients' stools were not infectious."
        Query: SARS-CoV-2 stool particles infectious ability patients study
    """

    try:
        response = _client.chat.completions.create(
            model=TOGETHER_MODEL,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Claim: {raw_claim}"},
            ],
            temperature=0.0,
            max_tokens=30
        )

        query = response.choices[0].message.content.strip()

        if len(query.split()) > 15 or "help" in query.lower():
            query = " ".join(raw_claim.split()[:8])

        final_query = clean_query_output(query)

        if citat_ancora:
            final_query = f"{final_query} {citat_ancora}"

        return final_query

    except Exception as e:
        print(f"Error with LLM API in query generation: {repr(e)}")
        return f"covid-19 {' '.join(raw_claim.split()[:10])}"
