import requests
import feedparser
import smtplib
import ssl
import time
import hashlib
import os
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv

# ==================================================
# LOAD ENV
# ==================================================

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
MAIL_TO = os.getenv("MAIL_TO").split(",")

# ==================================================
# CONFIG
# ==================================================

# -------- COMPANY SCOPE --------
COMPANIES = {
    "vion": [
        "vion",
        "vion food group",
        "vion boxtel",
        "vion vlees",
        "slachthuis vion"
    ],
    "distrifresh": [
        "distrifresh",
        "encebe"
    ]
    # later eenvoudig uit te breiden
}

USER_AGENT = "empbot/1.0 (free-open-source)"

REDDIT_SUBREDDITS = ["osint", "netherlands", "ai"]
REDDIT_LIMIT = 5

RSS_FEEDS = [
    {"name": "X - OpenAI", "url": "https://nitter.net/OpenAI/rss"},
    {"name": "Reddit OSINT", "url": "https://www.reddit.com/r/osint/.rss"},
]

# -------- KEYWORDS --------
KEYWORDS_ANY = ["employer", "branding", "hr", "reputation" , "reputatie" , "werkgever" , "baan" , "vacature" , "werken" , "vion"]
KEYWORDS_ALL = []

WHITELIST = ["crisis", "lawsuit", "scandal"]

# -------- SENTIMENT --------
POSITIVE = ["good", "great", "innovative", "success", "👍", "win", "goed", "top", "geweldig", "innovatief", "leuk", "super"]
NEGATIVE = ["bad", "problem", "fail", "crisis", "angry", "lawsuit", "👎", "stom" , "probleem", "dood" , "slecht" , "mishandeling"]
NEGATIONS = ["not", "no", "never"]

# ==================================================
# HELPERS
# ==================================================

def normalize(text: str) -> str:
    return text.lower().strip()

def hash_item(title, url):
    return hashlib.sha256(f"{title}{url}".encode()).hexdigest()

def match_company(text: str):
    """
    Retourneert de bedrijfsnaam als er een match is,
    anders None
    """
    t = normalize(text)
    for company, aliases in COMPANIES.items():
        for a in aliases:
            if a in t:
                return company
    return None

# ==================================================
# INGEST
# ==================================================

def fetch_reddit(sub):
    url = f"https://www.reddit.com/r/{sub}/new.json?limit={REDDIT_LIMIT}"
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()["data"]["children"]
        results = []
        for p in data:
            d = p["data"]
            results.append({
                "source": "reddit",
                "origin": sub,
                "title": d.get("title", ""),
                "text": d.get("selftext", ""),
                "url": f"https://reddit.com{d.get('permalink')}",
                "created": datetime.utcfromtimestamp(d.get("created_utc"))
            })
        return results
    except Exception as e:
        print(f"[ERROR] Reddit {sub}: {e}")
        return []

def fetch_rss(feed):
    parsed = feedparser.parse(feed["url"])
    results = []
    for e in parsed.entries[:5]:
        results.append({
            "source": "rss",
            "origin": feed["name"],
            "title": e.get("title", ""),
            "text": e.get("summary", ""),
            "url": e.get("link"),
            "created": e.get("published", "unknown")
        })
    return results

# ==================================================
# FILTERS & SENTIMENT
# ==================================================

def keyword_match(text):
    t = normalize(text)
    if KEYWORDS_ANY and not any(k in t for k in KEYWORDS_ANY):
        return False
    if KEYWORDS_ALL and not all(k in t for k in KEYWORDS_ALL):
        return False
    return True

def is_whitelisted(text):
    t = normalize(text)
    return any(w in t for w in WHITELIST)

def analyze_sentiment(text):
    t = normalize(text)
    score = 0

    for w in POSITIVE:
        if w in t:
            score += 1

    for w in NEGATIVE:
        if w in t:
            score -= 1

    for n in NEGATIONS:
        if n in t:
            score *= -1

    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"

# ==================================================
# MAIL
# ==================================================

def send_mail(alerts, summary):
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(MAIL_TO)
    msg["Subject"] = f"EmpBot Alert – {len(alerts)} signalen"

    body = [summary, "-" * 50]

    for a in alerts:
        body.append(
f"[{a['company'].upper()} | {a['source']} | {a['sentiment']}]\n"
            f"{a['title']}\n{a['url']}\n"
        )

    msg.set_content("\n\n".join(body))

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.starttls(context=context)
        s.login(SMTP_USER, SMTP_PASSWORD)
        s.send_message(msg)

# ==================================================
# MAIN
# ==================================================

def main():
    print("EmpBot gestart")

    raw = []
    seen = set()

    for sub in REDDIT_SUBREDDITS:
        raw.extend(fetch_reddit(sub))
        time.sleep(1)

    for feed in RSS_FEEDS:
        raw.extend(fetch_rss(feed))

    alerts = []

    for item in raw:
        uid = hash_item(item["title"], item["url"])
        if uid in seen:
            continue
        seen.add(uid)

text = f"{item['title']} {item['text']}"

company = match_company(text)
if not company:
    continue  # niet relevant voor onze bedrijven

if not keyword_match(text) and not is_whitelisted(text):
    continue

sentiment = analyze_sentiment(text)
item["sentiment"] = sentiment
item["company"] = company


        if sentiment == "negative" or is_whitelisted(text):
            alerts.append(item)

    print(f"Alerts gevonden: {len(alerts)}")

    if alerts:
        summary = (
            f"Samenvatting:\n"
            f"- Totaal items: {len(raw)}\n"
            f"- Alerts: {len(alerts)}\n"
            f"- Datum: {datetime.utcnow().isoformat()}Z"
        )
        send_mail(alerts, summary)
        print("Mail verstuurd")

if __name__ == "__main__":
    main()

