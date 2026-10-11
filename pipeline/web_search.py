from ddgs import DDGS


TRUSTED_DOMAINS = {
    # === FACT-CHECKERS DEDICAȚI  ===
    "politifact.com":       "https://www.politifact.com/",
    "factcheck.org":        "https://www.factcheck.org/",
    "fullfact.org":         "https://fullfact.org/",
    "snopes.com":           "https://www.snopes.com/",
    "leadstories.com":      "https://leadstories.com/",
    "boomlive.in":          "https://www.boomlive.in/",
    "factcrescendo.com":    "https://english.factcrescendo.com/",
    "healthfeedback.org":   "https://healthfeedback.org/",
    "altnews.in":           "https://www.altnews.in/",
    "thequint.com":         "https://www.thequint.com/news/webqoof/",
    "aap.com.au":           "https://www.aap.com.au/factcheck/",

    # === AGENȚII DE ȘTIRI / JURNALISM DE ÎNCREDERE ===
    "apnews.com":           "https://apnews.com/",
    "bbc.com":              "https://www.bbc.com/",
    "theguardian.com":      "https://www.theguardian.com/",
    "aljazeera.com":        "https://www.aljazeera.com/",
    "thehindu.com":         "https://www.thehindu.com/",
    "hindustantimes.com":   "https://www.hindustantimes.com/",
    "timesofindia.indiatimes.com": "https://timesofindia.indiatimes.com/",
    "indiatoday.in":        "https://www.indiatoday.in/",
    "euronews.com":         "https://www.euronews.com/",
    "npr.org":              "https://www.npr.org/sections/health/",
    "pbs.org":              "https://www.pbs.org/newshour/health",
    "scmp.com":             "https://www.scmp.com/coronavirus",
    "channelnewsasia.com":  "https://www.channelnewsasia.com/",
    "abc11.com":            "https://abc11.com/",
    "kxan.com":             "https://www.kxan.com/",

    # === ORGANIZAȚII DE SĂNĂTATE ȘI GUVERNAMENTALE ===
    "who.int":              "https://www.who.int/",
    "cdc.gov":              "https://www.cdc.gov/",
    "nih.gov":              "https://www.nih.gov/",
    "health.gov":           "https://health.gov/",
    "ecdc.europa.eu":       "https://www.ecdc.europa.eu/",
    "gov.uk":               "https://www.gov.uk/",
    "parliament.uk":        "https://www.parliament.uk/",
    "hcplive.com":          "https://www.hcplive.com/",
    "kff.org":              "https://www.kff.org/",
    "fda.gov":              "https://www.fda.gov/",
    "healthnz.govt.nz":     "https://www.healthnz.govt.nz/",
    "futurity.org":         "https://www.futurity.org/",
    "ourworldindata.org":   "https://ourworldindata.org/coronavirus",

    # === REVISTE ȘI INSTITUȚII ȘTIINȚIFICE (Standard Academic) ===
    "thelancet.com":        "https://www.thelancet.com/",
    "nature.com":           "https://www.nature.com/",
    "bmj.com":              "https://www.bmj.com/",
    "jhsph.edu":            "https://publichealth.jhu.edu/",
    "pubmed.ncbi.nlm.nih.gov": "https://pubmed.ncbi.nlm.nih.gov/",
    "pmc.ncbi.nlm.nih.gov":    "https://pmc.ncbi.nlm.nih.gov/",
    "hopkinsmedicine.org":  "https://www.hopkinsmedicine.org/health",
    "nejm.org":             "https://www.nejm.org/coronavirus",
    "onlinelibrary.wiley.com": "https://onlinelibrary.wiley.com/",
    "coronavirus.jhu.edu":  "https://coronavirus.jhu.edu/",
    "idsociety.org":        "https://www.idsociety.org/",
    "cochrane.org":         "https://www.cochrane.org/",
    "ictv.global":          "https://ictv.global/",
    "cidrap.umn.edu":       "https://www.cidrap.umn.edu/",
}

from urllib.parse import urlparse


def filter_trusted_sources(results):
    filtered = []

    for r in results:
        url = r["link"]

        parsed_domain = urlparse(url).netloc.lower()

        is_trusted = False
        for trusted_domain in TRUSTED_DOMAINS:
            if parsed_domain == trusted_domain or parsed_domain.endswith("." + trusted_domain):
                is_trusted = True
                break

        if is_trusted:
            filtered.append(r)

    return filtered

def search_web(query, max_results=25):
    results = []

    with DDGS() as ddgs:
        # search_results = ddgs.text(f"{query} fact check", region='wt-ads', max_results=40)
        search_results = ddgs.text(query, region='us-en', max_results=40)

        if search_results:
            for r in search_results:
                results.append({
                    "title": r.get("title", ""),
                    "link": r.get("href", ""),
                    "snippet": r.get("body", "")
                })

    return results