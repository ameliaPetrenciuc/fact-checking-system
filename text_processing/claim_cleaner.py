import re
import html
import unicodedata


MENTION_ENTITY_MAP = {
    "who": "WHO",
    "cdcgov": "CDC",
    "cdcdirector": "CDC Director",
    "caboraledirector": "CDC Director",
    "surgeon_general": "Surgeon General",
    "mohfw_india": "India Ministry of Health",
    "icmrdelhi": "ICMR",
    "drharshvardhan": "Dr. Harsh Vardhan",
    "drtedros": "Dr. Tedros",
    "pmoindia": "PMO India",
    "paboraindia": "PIB India",
    "pib_india": "PIB India",
    "realdonaldtrump": "Donald Trump",
    "govlancyhogan": "Governor Larry Hogan",
    "gavinnewsom": "Gavin Newsom",
    "followlasg": "Lagos State Government",
    "fmohnigeria": "Nigeria Federal Ministry of Health",
    "covnewsbymib": "COVID News MIB",
}


HASHTAG_CANONICAL = {
    "covid19": "COVID-19",
    "covid_19": "COVID-19",
    "covid__19": "COVID-19",
    "covidー19": "COVID-19",  # fullwidth dash variant
    "covid": "COVID",
    "covid19india": "COVID-19 India",
    "coronavirus": "coronavirus",
    "coronavirusupdates": "coronavirus updates",
    "coronavirusindia": "coronavirus India",
    "coronavirusfacts": "coronavirus facts",
    "coronaviruspandemic": "coronavirus pandemic",
    "coronavirusoutbreak": "coronavirus outbreak",
    "corona": "coronavirus",
    "coronaupdates": "coronavirus updates",
    "coronaupdatesinindia": "coronavirus updates in India",
    "coronavirusupdates": "coronavirus updates",
    "indiafightscorona": "India fights coronavirus",
    "indiaswillwin": "India will win",
    "indiawillwin": "India will win",
    "staysafe": "stay safe",
    "n95": "N95",
    "hydroxychloroquine": "hydroxychloroquine",
    "hcq": "HCQ",
    "lockdown": "lockdown",
    "facemasks": "face masks",
    "facemask": "face mask",
    "wearmask": "wear mask",
    "worldmaskweek": "World Mask Week",
    "socialdistance": "social distance",
    "socialdistancing": "social distancing",
    "handwashing": "handwashing",
    "flu": "flu",
    "fightflu": "fight flu",
    "hypertension": "hypertension",
    "donaldtrump": "Donald Trump",
    "mikepence": "Mike Pence",
    "maralago": "Mar-a-Lago",
    "kayleighmcenany": "Kayleigh McEnany",
    "rollingstonevaccineforcv": "",  # noise
    "keithholdskeytovirusvaccine": "",  # noise
    "rockandrollvaccine": "",  # noise
    "globalwarming": "global warming",
    "nashville": "Nashville",
    "zoo": "",  # noise
    "pandas": "", 
    "doyourpart": "",  # pure noise
    "maga": "",
    "cdnpoli": "",
    "wakeup": "",
    "christmas": "",
    "conspiracy": "",
    "toiletpaper": "",
    "georgeorwell": "",
    "government": "",
    "tipsadvice": "",
    "roadtrips": "",
    "list": "",
    "travel": "",
    "vacation": "",
    "health": "",
    "covid19science": "COVID-19 science",
    "covidnewsbymib": "",  # noise institutional
    "covidupdates": "",  # noise when not inline
    "covid19nz": "",  # noise region tag
    "hcps": "HCPs",
    "china": "",  # noise hashtag context
    "mask": "mask",
    "fourthofJuly": "Fourth of July",
    "fourthofjuly": "Fourth of July",
}

_CLICKBAIT_PATTERNS = [
    re.compile(r'^\s*BREAKING\s*(?:NEWS)?[#:!\s]*', re.IGNORECASE),
    re.compile(r'^\s*ALERT\s*[:!\s]+', re.IGNORECASE),
    re.compile(r'^\s*EXPOSED\s*[:!\s]+', re.IGNORECASE),
    re.compile(r'^\s*SHOCKING\s*[:!\s]*', re.IGNORECASE),
    re.compile(r'^\s*NEWS!\s*', re.IGNORECASE),
    re.compile(r'^\s*Great news!\s*', re.IGNORECASE),
    re.compile(r'^\s*NEW PUBLICATION\s*', re.IGNORECASE),
    re.compile(r'^\s*UPDATE:\s*', re.IGNORECASE),

    re.compile(r'\bRead more(?:\s+here)?[:\s]*', re.IGNORECASE),
    re.compile(r'\bTo read more(?:\s+click here)?[:\s]*', re.IGNORECASE),
    re.compile(r'\bLearn more(?:\s+at)?[:\s]*', re.IGNORECASE),
    re.compile(r'\bRead the study from[:\s\-]*', re.IGNORECASE),
    re.compile(r'\bClick (?:below|here)\b.*$', re.IGNORECASE),
    re.compile(r'\bClick (?:below|here)\s+to\b[:\s]*', re.IGNORECASE),
    re.compile(r'\bClick (?:below|here)[:\s]*', re.IGNORECASE),
    re.compile(r'\bFollow live updates[:\s]*', re.IGNORECASE),

    re.compile(r'\bvia\s+@\w+', re.IGNORECASE),
    re.compile(r'\bvia\s*$', re.IGNORECASE),
    re.compile(r'\bto\s*$', re.IGNORECASE),
    re.compile(r'\bfrom\s*$', re.IGNORECASE),
    re.compile(r'\bat\s*$', re.IGNORECASE),

    re.compile(r'\bNote\s*:\s*This message requires confirmation\s*', re.IGNORECASE),
    re.compile(r'\b#?DYK\s*:\s*', re.IGNORECASE),
]

_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F9FF"  # Misc symbols, emoticons, transport, map, etc.
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"  # Dingbats
    "\U0000FE00-\U0000FE0F"  # Variation selectors
    "\U0000200D"              # ZWJ
    "\U000025A0-\U000025FF"  # Geometric shapes
    "\U00002600-\U000026FF"  # Misc symbols
    "\U0000231A-\U0000231B"  # Watch, hourglass
    "\U00002B05-\U00002B55"  # Arrows and symbols (➡️ etc.)
    "\U0000203C-\U00003299"  # Enclosed CJK, misc
    "\U0001FA00-\U0001FA6F"  # Chess, extended-A
    "\U0001FA70-\U0001FAFF"  # Extended-A continued
    "]+",
    flags=re.UNICODE
)


def clean_claim_text(raw_text: str) -> str:

    if not raw_text or not isinstance(raw_text, str):
        return ""

    text = raw_text

    text = unicodedata.normalize("NFKC", text)
    text = html.unescape(text)

    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)

    text = re.sub(r'\bRT\s+@\w+\s*:?\s*', '', text)

    def _replace_mention(m):
        handle = m.group(1).lower()
        entity = MENTION_ENTITY_MAP.get(handle)
        if entity:
            return entity
        return ""

    text = re.sub(r'@(\w+)', _replace_mention, text)

    def _replace_hashtag(m):
        tag = m.group(1).strip()

        tag_key = tag.lower().replace("ー", "-")

        lookup_keys = [
            tag_key,
            tag_key.replace("-", "_"),
            tag_key.replace("-", ""),
            tag_key.replace("_", ""),
        ]

        for key in lookup_keys:
            canonical = HASHTAG_CANONICAL.get(key)
            if canonical is not None:
                return canonical

        spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', tag)
        spaced = spaced.replace("_", " ").replace("-", " ")
        spaced = re.sub(r"\s+", " ", spaced).strip()
        return spaced

    text = re.sub(r'#([A-Za-z0-9_ー\-]+)', _replace_hashtag, text)

    text = re.sub(r'\bCOVID\s*[- ]\s*19\b', 'COVID-19', text, flags=re.IGNORECASE)
    text = re.sub(r'\bcorona\s+virus\b', 'coronavirus', text, flags=re.IGNORECASE)

    text = _EMOJI_PATTERN.sub(' ', text)

    text = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'\1', text)
    text = text.strip('_')

    text = re.sub(r"([A-Za-z])\?{3}([A-Za-z])", r"\1'\2", text)

    text = re.sub(r'^\?{2,}', '', text)

    text = re.sub(r'\?{2,}~?', '', text)

    text = re.sub(r'\?{2,}', '?', text)

    text = re.sub(r'[\u2018\u2019]', "'", text)
    text = re.sub(r'[\u201c\u201d]', '"', text)

    text = re.sub(r'[~\u00bf\u00e2\u0080\u0099\u009c\u009d]+', '', text)

    for pattern in _CLICKBAIT_PATTERNS:
        text = pattern.sub(' ', text)

    text = re.sub(r'\b(COVID-19)(\s+\1\b)+', r'\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(coronavirus)(\s+\1\b)+', r'\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(coronavirus updates)(\s+\1\b)+', r'\1', text, flags=re.IGNORECASE)

    text = re.sub(r'…+', '.', text)

    text = re.sub(r'\s*-{2,}>\s*', ' ', text)
    text = re.sub(r'\s*(?:-->|->|>)\s*$', '', text)

    text = re.sub(r'\s*\.\s*\.+', '.', text)
    text = re.sub(r'[!]{2,}', '!', text)
    text = re.sub(r'[?]{2,}', '?', text)

    orphan_suffix_patterns = [
        r'\bLearn more\b[:\s]*$',
        r'\bRead more\b[:\s]*$',
        r'\bClick here\b[:\s]*$',
        r'\bClick below\b[:\s]*$',
        r'\bRead the study from\b[:\s]*$',
        r'\bHere are\s+\d+\s+things\s+to\b[:\s.]*$',
        r'\bto check if there are local restrictions in your area\b[:\s.]*$',
        r'\bcheck if there are local restrictions in your area\b[:\s.]*$',
        r'\bvia\b[:\s]*$',
        r'\bto\b[:\s]*$',
        r'\bfrom\b[:\s]*$',
        r'\bat\b[:\s]*$',
    ]

    for pattern in orphan_suffix_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    text = re.sub(r'\(\s*\)', '', text)

    text = re.sub(r'\s+([.,;:!?])', r'\1', text)

    text = re.sub(r'[,;:\-]\s*$', '', text)

    text = re.sub(r'\s+', ' ', text).strip()

    return text


def clean_claim_batch(texts: list) -> list:
    return [clean_claim_text(t) for t in texts]
