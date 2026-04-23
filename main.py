import os
import csv
import smtplib
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO")

DATA_PATH = "data/sentiment_history.csv"
BRAND_QUERY = "Vion"
INDUSTRY_QUERY = "meat industry OR vleesindustrie OR slachterij"
GLOBAL_QUERY = "news"

analyzer = SentimentIntensityAnalyzer()


def fetch_news_sentiment(query: str, page_size: int = 20) -> float:
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "pageSize": page_size,
        "sortBy": "publishedAt",
        "apiKey": NEWSAPI_KEY,
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()

    articles = data.get("articles", [])
    if not articles:
        return 0.0

    scores = []
    for a in articles:
        text = f"{a.get('title', '')}. {a.get('description', '')}"
        vs = analyzer.polarity_scores(text)
        scores.append(vs["compound"])

    return sum(scores) / len(scores)


def ensure_csv_exists():
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["timestamp", "brand_sentiment", "industry_sentiment", "global_sentiment"]
            )


def append_to_csv(timestamp, brand, industry, global_s):
    with open(DATA_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, brand, industry, global_s])


def generate_plot():
    df = pd.read_csv(DATA_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    plt.figure(figsize=(10, 5))
    plt.plot(df["timestamp"], df["brand_sentiment"], label="Vion")
    plt.plot(df["timestamp"], df["industry_sentiment"], label="Vleesindustrie")
    plt.plot(df["timestamp"], df["global_sentiment"], label="Wereld")
    plt.axhline(0, color="grey", linewidth=0.8, linestyle="--")

    plt.title("Sentiment in de tijd")
    plt.xlabel("Datum")
    plt.ylabel("Sentiment (VADER compound)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("data/sentiment_plot.png")
    plt.close()


def send_email(timestamp, brand, industry, global_s):
    msg = MIMEMultipart("related")
    msg["Subject"] = f"Vion Sentiment Rapport – {timestamp}"
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO

    html = f"""
    <html>
      <body>
        <h2>Vion Sentiment Rapport – {timestamp}</h2>
        <ul>
          <li><b>Vion sentiment:</b> {brand:.3f}</li>
          <li><b>Vleesindustrie sentiment:</b> {industry:.3f}</li>
          <li><b>Wereldsentiment:</b> {global_s:.3f}</li>
        </ul>
        <p>Grafiek in de tijd:</p>
        <img src="cid:sentiment_plot">
      </body>
    </html>
    """

    msg_alt = MIMEMultipart("alternative")
    msg.attach(msg_alt)
    msg_alt.attach(MIMEText(html, "html"))

    with open("data/sentiment_plot.png", "rb") as f:
        img = MIMEImage(f.read())
        img.add_header("Content-ID", "<sentiment_plot>")
        msg.attach(img)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


def main():
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    print("Fetching sentiment for Vion...")
    brand_sentiment = fetch_news_sentiment(BRAND_QUERY)

    print("Fetching sentiment for meat industry...")
    industry_sentiment = fetch_news_sentiment(INDUSTRY_QUERY)

    print("Fetching global sentiment...")
    global_sentiment = fetch_news_sentiment(GLOBAL_QUERY)

    print("Ensuring CSV...")
    ensure_csv_exists()
    append_to_csv(timestamp, brand_sentiment, industry_sentiment, global_sentiment)

    print("Generating plot...")
    generate_plot()

    print("Sending email...")
    send_email(timestamp, brand_sentiment, industry_sentiment, global_sentiment)

    print("Done.")


if __name__ == "__main__":
    main()
