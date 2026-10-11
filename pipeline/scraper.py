import time

import cloudscraper
from bs4 import BeautifulSoup

BOILERPLATE_PHRASES = [
    "belongs to an official government",
    "https:// means you've safely connected",
    "share sensitive information only",
    "an official website of the united states",
    "click here", "sign up", "log in", "subscribe now",
    "accept cookies", "privacy policy", "terms of service"
]

def _scrape_snopes(url):
    import requests
    try:
        slug = url.rstrip("/").split("/")[-1]
        api_url = f"https://www.snopes.com/wp-json/wp/v2/posts?slug={slug}"
        r = requests.get(api_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        data = r.json()
        if data:
            html = data[0].get("content", {}).get("rendered", "")
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup.find_all(["script", "style"]):
                tag.decompose()
            return soup.get_text(" ", strip=True)
    except Exception as e:
        pass
    return ""

def scrape_article(url, max_retries=2):
    if "snopes.com" in url:
        text = _scrape_snopes(url)
        if len(text) > 200:
            return text

    for attempt in range(max_retries):
        try:
            scraper = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True},
                delay=5
            )

            response = scraper.get(url, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            for tag in soup.find_all(["nav", "header", "footer", "aside",
                                       "button", "form", "input", "select",
                                       "script", "style", "noscript", "iframe"]):
                tag.decompose()

            for tag in soup.find_all(class_=lambda c: c and any(
                x in " ".join(c).lower() for x in
                ["nav", "menu", "header", "footer", "sidebar",
                 "cookie", "popup", "ad", "banner", "subscribe", "social"]
            )):
                tag.decompose()

            for tag in soup.find_all(id=lambda i: i and any(
                x in i.lower() for x in
                ["nav", "menu", "header", "footer", "sidebar", "cookie", "ad"]
            )):
                tag.decompose()

            text_elements = soup.find_all(['p', 'li', 'h2', 'h3', 'td', 'th'])

            article_text = " ".join(
                element.get_text(" ", strip=True)
                for element in text_elements
                if len(element.get_text(strip=True)) > 40
                and not any(phrase in element.get_text(strip=True).lower()
                            for phrase in BOILERPLATE_PHRASES)
            )

            return article_text.strip()

        except cloudscraper.exceptions.CloudflareChallengeError:
            return "Error: Cloudflare challenge prea avansat."
        except Exception as e:
            error_str = str(e).lower()
            # Retry only on network errors, not on 4xx
            if attempt < max_retries - 1 and any(k in error_str for k in ["connect", "timeout", "network"]):
                time.sleep(3)
                continue
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code in (401, 403):
                    return "Error: Access blocked."
            return f"Error: {e}"
    return "Error: Max retries exceeded."

