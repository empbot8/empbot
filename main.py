import requests
import feedparser
import smtplib
import ssl
import time
from email.message import EmailMessage
from datetime import datetime

# ==================================================
# CONFIG
# ==================================================

USER_AGENT = "empbot/1.0 (free-open-source)"

# -------- Reddit --------
REDDIT_SUBREDDITS = ["osint", "netherlands", "ai"]
REDDIT_LIMIT = 5

# -------- RSS feeds (X / LinkedIn / Facebook) --------
RSS_FEEDS = [
    {
        "name": "X - OpenAI (via Nitter)",
        "url": "https://nitter.net/OpenAI/rss"
    },
    {
        "name": "Reddit OSINT RSS",
        "url": "https://www.reddit.com/r/osint/.rss"
    }
]

# -------- Sentiment --------
POSITIVE_WORDS = ["good", "great", "innovative", "success", "positive"]
NEGATIVE_WORDS = ["bad", "problem", "fail", "crisis", "negative", "angry"]

# -------- Mail --------
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587
SMTP_USER = "bot@example.com"
SMTP_PASSWORD = "password"
MAIL_TO = ["you@example.com"]

# ==================================================
# DATA INGEST
# ==================================================

def fetch_reddit(subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={REDDIT_LIMIT}"
    headers = {"User-Agent": USER_AGENT}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        posts = r.json()["data"]["children"]

        results = []
        for post in posts:
            p = post["data"]
            results.append({
                "source": "reddit",
                "origin": subreddit,
                "title": p.get("title", ""),
                "content": p.get("selftext", ""),
                "url": f"https://reddit.com{p.get('permalink')}",
                "created": datetime.utcfromtimestamp(p.get("created_utc"))
            })

        return results

    except Exception as e:
        print(f"[ERROR] Reddit {subreddit}: {e}")
        return []

def fetch_rss(feed):
    parsed = feedparser.parse(feed["url"])
    results = []

    for entry in parsed.entries[:5]:
        results.append({
            "source": "rss",
            "origin": feed["name"],
            "title": entry.get("title", ""),
            "content": entry.get("summary", ""),
            "url": entry.get("link"),
            "created": entry.get("published", "unknown")
        })

    return results

# ==================================================
# SENTIMENT
# ==================================================

def analyze_sentiment(text):
    text = text.lower()
    score = 0

    for w in POSITIVE_WORDS:
        if w in text:
            score += 1

    for w in NEGATIVE_WORDS:
        if w in text:
            score -= 1

    if score > 0:
        return "positive"
    elif score < 0:
        return "negative"
    return "neutral"

# ==================================================
# MAIL
# ==================================================

def send_mail(items):
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(MAIL_TO)
    msg["Subject"] = f"EmpBot alert ({len(items)} hits)"

    body = []
    for i in items:
        body.append(
            f"[{i['source'].upper()} | {i['origin']} | {i['sentiment']}]\n"
            f"{i['title']}\n{i['url']}\n"
        )

    msg.set_content("\n\n".join(body))

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

# ==================================================
# MAIN PIPELINE
# ==================================================

def main():
    print("EmpBot running...")

    collected = []

    # Reddit
    for sub in REDDIT_SUBREDDITS:
        collected.extend(fetch_reddit(sub))
        time.sleep(1)

    # RSS
    for feed in RSS_FEEDS:
        collected.extend(fetch_rss(feed))

    # Sentiment
    alerts = []
    for item in collected:
        text = f"{item['title']} {item.get('content','')}"
        item["sentiment"] = analyze_sentiment(text)

        # trigger rule
        if item["sentiment"] == "negative":
            alerts.append(item)

    # Output
    print(f"Collected {len(collected)} items")
    print(f"Alerts: {len(alerts)}")

    if alerts:
        send_mail(alerts)
        print("Mail sent")

if __name__ == "__main__":
    main()
