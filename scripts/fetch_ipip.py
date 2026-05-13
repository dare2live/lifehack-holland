"""
fetch_ipip.py — Download IPIP (International Personality Item Pool) master items.

According to the blueprint:
We need the Jungian Personality Scale (or Big Five) which maps to MBTI preferences (E/I, S/N, T/F, J/P).
The IPIP site provides the item text and the keyed direction (+ or -) for the dimension.

Data Source: https://ipip.ori.org
"""

import os
import urllib.request
from pathlib import Path
from html.parser import HTMLParser

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
IPIP_DATA_DIR = PROJECT_ROOT / "backend" / "data" / "ipip"

# We target the proxy page for the Jungian (MBTI-like) scales or Big Five
# For the purpose of this script, we'll download the HTML page for the Jungian scale
IPIP_JUNGIAN_URL = "https://ipip.ori.org/newJungKeys.htm"

def download_file(url: str, dest_path: Path):
    print(f"Downloading {url} ...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        dest_path.write_bytes(response.read())
    print(f"✅ Saved to {dest_path} ({os.path.getsize(dest_path)} bytes)")

def fetch_ipip_data():
    IPIP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    jungian_path = IPIP_DATA_DIR / "IPIP_Jungian_Scale.html"
    
    try:
        download_file(IPIP_JUNGIAN_URL, jungian_path)
        print("\n🎉 IPIP master data successfully fetched!")
        print("Note: IPIP provides data in HTML format. The extraction script (`llm_translate.py` or a parser) will need to parse the + and - keyed items from this HTML file.")
        print("Next step (Phase 4): Parse this HTML and map it to MBTI dimensions (Extraversion, Openness/Intuition, Agreeableness/Feeling, Conscientiousness/Judging).")
    except Exception as e:
        print(f"❌ Failed to fetch IPIP data: {e}")

if __name__ == "__main__":
    fetch_ipip_data()
