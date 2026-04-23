import os
import smtplib
from email.mime.text import MIMEText
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import feedparser
from dotenv import load_dotenv

load_dotenv()
print("DEBUG SMTP:", os.getenv("SMTP_HOST"), os.getenv("SMTP_USER"), os.getenv("REPORT_TO"))
print("DEBUG PASS:", os.getenv("SMTP_PASS"))



SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
REPORT_TO = os.getenv("REPORT_TO")

BEDRIJFSNAAM = os.getenv("BEDRIJFSNAAM", "Vion")

RSS_FEEDS = [
    f"https://news.google.com/rss/search?q={BEDRIJFSNAAM}+Nederland&hl=nl&gl=NL&ceid=NL:nl"
]

analyzer = SentimentIntensityAnalyzer()


def fetch_articles():
    items = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            link = entry.get("link", "")
            text = f"{title}. {summary}"
            items.append({"title": title, "summary": summary, "link": link, "text": text})
    return items


def analyze_sentiment(items):
    results = []
    for item in items:
        scores = analyzer.polarity_scores(item["text"])
        item["sentiment"] = scores["compound"]
        results.append(item)
    return results


def summarize(results):
    if not results:
        return "Er zijn vandaag geen relevante berichten gevonden."

    scores = [r["sentiment"] for r in results]
    avg = sum(scores) / len(scores)

    positives = sorted(
        [r for r in results if r["sentiment"] > 0.2],
        key=lambda x: x["sentiment"],
        reverse=True,
    )[:3]
    negatives = sorted(
        [r for r in results if r["sentiment"] < -0.2],
        key=lambda x: x["sentiment"],
    )[:3]

    lines = []
    lines.append(f"Dagrapport sentiment rond werkgeversmerk: {BEDRIJFSNAAM}")
    lines.append("")
    lines.append(f"Aantal gevonden berichten: {len(results)}")
    lines.append(f"Gemiddelde sentiment-score: {avg:.3f}")
    lines.append("")

    lines.append("Top positieve berichten:")
    if positives:
        for p in positives:
            lines.append(f"- {p['title']} ({p['sentiment']:.3f})")
            lines.append(f"  {p['link']}")
    else:
        lines.append("- Geen duidelijke positieve uitschieters.")
    lines.append("")

    lines.append("Top negatieve berichten:")
    if negatives:
        for n in negatives:
            lines.append(f"- {n['title']} ({n['sentiment']:.3f})")
            lines.append(f"  {n['link']}")
    else:
        lines.append("- Geen duidelijke negatieve uitschieters.")
    lines.append("")

    return "\n".join(lines)


def send_email(body: str):
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = f"Dagrapport werkgeversmerk – {BEDRIJFSNAAM}"
    msg["From"] = SMTP_USER
    msg["To"] = REPORT_TO

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def main():
    items = fetch_articles()
    analyzed = analyze_sentiment(items)
    report = summarize(analyzed)
    print(report)

    if SMTP_HOST and SMTP_USER and SMTP_PASS and REPORT_TO:
        send_email(report)
    else:
        print("Geen SMTP-config gevonden, rapport alleen in console.")


if __name__ == "__main__":
    main()
