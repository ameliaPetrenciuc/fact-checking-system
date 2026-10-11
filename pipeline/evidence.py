from urllib.parse import urlparse

from pipeline.scraper import scrape_article
from config.settings import MIN_CHARS, MAX_SOURCES

def get_aggregated_evidence(trusted_results):
    scraped_articles = []
    successful_scrapes = 0

    used_domains = set()

    for r in trusted_results:
        url = r["link"]

        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()

        base_domain = ".".join(domain.split('.')[-2:])

        social_media = ["twitter.com", "facebook.com", "instagram.com", "t.me"]

        if url.endswith(".pdf") or any(sm in domain for sm in social_media) or base_domain in used_domains:
            continue

        print(f"    [→] Analizăm sursa nouă: {domain}...")
        content = scrape_article(url, max_retries=2)

        if content and "ERROR" not in content and len(content) >= MIN_CHARS:
            print(f"    [V] Sursă validată: {domain} ({len(content)} caractere)")

            scraped_articles.append({
                "url": url,
                "content": content
            })

            used_domains.add(base_domain)
            successful_scrapes += 1

            if successful_scrapes >= MAX_SOURCES:
                print(f"    [*] Limită atinsă: {MAX_SOURCES} surse din domenii unice.")
                break
        else:
            status = "Blocat/Eroare" if (content and "ERROR" in content) else "Conținut insuficient"
            print(f"    [X] Ignorat ({status}): {domain}")

    if successful_scrapes > 0:
        return ", ".join(used_domains), scraped_articles

    return None, None

