import os
import json
import feedparser
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

SOURCES = {
    "cybersecurity": [
        ("CISA Advisories", "[https://www.cisa.gov/cybersecurity-advisories/all.xml](https://www.cisa.gov/cybersecurity-advisories/all.xml)"),
        ("The Hacker News", "[https://feeds.feedburner.com/TheHackersNews](https://feeds.feedburner.com/TheHackersNews)")
    ],
    "tech": [
        ("Ars Technica", "[https://feeds.arstechnica.com/arstechnica/index](https://feeds.arstechnica.com/arstechnica/index)"),
        ("Hacker News (Top)", "[https://hnrss.org/frontpage?points=100](https://hnrss.org/frontpage?points=100)")
    ],
    "science": [
        ("Nature News", "[https://www.nature.com/nature.rss](https://www.nature.com/nature.rss)")
    ]
}

# --- Schemas ---
class StorySummary(BaseModel):
    title: str = Field(description="Direct, factual headline")
    category: str = Field(description="One of: cybersecurity, tech, science, world")
    source_name: str
    source_url: str
    summary: str = Field(description="Two clear sentences explaining what happened.")
    why_it_matters: str = Field(description="One clear sentence on technical or operational significance.")
    published_at: str

class DailyBriefing(BaseModel):
    stories: List[StorySummary]

# --- Quote Selection Logic ---
def get_daily_quote(quotes_file="data/quotes.json") -> dict:
    fallback = {
        "quote": "The superior person acts before speaking, and afterwards speaks according to their actions.",
        "author": "Confucius",
        "source": "The Analects 4.24"
    }

    if not os.path.exists(quotes_file):
        print(f"[!] {quotes_file} not found. Using fallback quote.")
        return fallback

    try:
        with open(quotes_file, "r", encoding="utf-8") as f:
            quotes = json.load(f)

        if not isinstance(quotes, list) or len(quotes) == 0:
            return fallback

        # Pick deterministically by day of the year
        day_of_year = datetime.now(timezone.utc).timetuple().tm_yday
        selected = quotes[day_of_year % len(quotes)]
        return {
            "quote": selected.get("quote", fallback["quote"]),
            "author": selected.get("author", fallback["author"]),
            "source": selected.get("source", None)
        }
    except Exception as e:
        print(f"[!] Error parsing quotes: {e}")
        return fallback

# --- RSS Collector ---
def collect_feed_items(max_per_feed=5):
    raw_candidates = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9"
    }

    for cat, feed_list in SOURCES.items():
        for name, url in feed_list:
            try:
                # Fetch raw text first to guarantee valid HTTP status
                resp = requests.get(url, headers=headers, timeout=12)
                if resp.status_code != 200:
                    print(f"[!] {name} returned HTTP {resp.status_code}")
                    continue

                parsed = feedparser.parse(resp.content)
                entries = parsed.entries[:max_per_feed]
                print(f"[+] {name}: Found {len(entries)} items")

                for entry in entries:
                    raw_candidates.append({
                        "category": cat,
                        "source_name": name,
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", datetime.now(timezone.utc).isoformat()),
                        "summary_raw": entry.get("summary", "")[:500]
                    })
            except Exception as e:
                print(f"[!] Error fetching {name}: {e}")

    return raw_candidates

# --- Pipeline Execution ---
def run_pipeline():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing.")

    daily_quote = get_daily_quote()
    print(f"[*] Assigned Quote for today: \"{daily_quote['quote'][:35]}...\" — {daily_quote['author']}")

    print("[*] Fetching RSS candidate stories...")
    candidates = collect_feed_items()
    if not candidates:
        print("[!] No candidates collected. Aborting.")
        return

    print(f"[*] Processing {len(candidates)} candidates through Gemini...")
    client = genai.Client(api_key=api_key)

    prompt = f"""
    You are an automated intelligence curator.
    Select the 10-15 most critical, high-impact stories from the candidates below.
    Prioritize zero-days, infrastructure security, core systems architecture, and scientific papers.
    Reject marketing promotions, product redesigns, and duplicates.

    Raw Candidates:
    {json.dumps(candidates, indent=2)}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DailyBriefing,
            temperature=0.2
        )
    )

    briefing_data = json.loads(response.text)

    output = {
        "edition_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "daily_quote": daily_quote,
        "stories": briefing_data.get("stories", [])
    }

    os.makedirs("data", exist_ok=True)
    with open("data/briefing.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"[✓] Generated data/briefing.json successfully with {len(output['stories'])} stories.")

if __name__ == "__main__":
    run_pipeline()
