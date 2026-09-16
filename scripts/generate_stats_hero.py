"""Generate assets/stats-hero.png from live GitHub API data."""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
OUT = ASSETS / "stats-hero.png"
USER = os.environ.get("GITHUB_ACTOR") or os.environ.get("GH_USER") or "He4TheR-Dev"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def font(size: int):
    for p in (
        r"C:\Windows\Fonts\seguisb.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
    ):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def api(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "he4ther-stats",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_stats():
    user = api(f"https://api.github.com/users/{USER}")
    repos = api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&sort=updated")
    own = [r for r in repos if not r.get("fork")]
    stars = sum(r.get("stargazers_count", 0) for r in own)
    langs = {}
    for r in own:
        lang = r.get("language")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    primary = max(langs, key=langs.get) if langs else "—"
    return {
        "repos": len(own),
        "stars": stars,
        "followers": user.get("followers", 0),
        "langs": len(langs),
        "primary": primary,
        "name": user.get("name") or USER,
    }


def render(stats: dict):
    W, H = 1200, 220
    BG, CARD = (8, 8, 12), (14, 14, 20)
    PURPLE, CYAN = (192, 80, 255), (56, 189, 248)
    TEXT, MUTED = (245, 245, 250), (140, 140, 155)

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, W - 8, H - 8), radius=18, outline=(36, 24, 48), width=1)
    d.rounded_rectangle((12, 12, W - 12, H - 12), radius=16, fill=CARD)
    d.rectangle((12, 12, 18, H - 12), fill=PURPLE)

    d.text((40, 28), "PROFILE SIGNAL  ·  LIVE", font=font(16), fill=MUTED)
    d.text((40, 52), str(stats["name"]).upper(), font=font(36), fill=TEXT)
    d.text((40, 100), "Gaming software  ·  Windows  ·  Open source", font=font(16), fill=MUTED)

    metrics = [
        (f"{stats['repos']:02d}", "REPOS", PURPLE),
        (str(stats["primary"]), "PRIMARY", CYAN),
        (f"{stats['langs']}", "LANGS", PURPLE),
        (f"{stats['stars']}", "STARS", CYAN),
    ]
    x, y = 40, 140
    for value, label, color in metrics:
        box_w = 160
        d.rounded_rectangle(
            (x, y, x + box_w, y + 52),
            radius=12,
            fill=(22, 18, 32),
            outline=(48, 36, 64),
            width=1,
        )
        d.text((x + 16, y + 8), str(value)[:8], font=font(22), fill=color)
        d.text((x + 16, y + 32), label, font=font(12), fill=MUTED)
        x += box_w + 14

    cx, cy = 1040, 110
    for r, col in ((70, (40, 20, 60)), (52, (70, 30, 100)), (34, PURPLE)):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col, width=3)
    d.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), fill=PURPLE)
    d.text((968, 175), f"{stats['followers']} FOLLOWERS", font=font(13), fill=CYAN)

    ASSETS.mkdir(parents=True, exist_ok=True)
    img.save(OUT, optimize=True)
    print(f"wrote {OUT} repos={stats['repos']} primary={stats['primary']}")


if __name__ == "__main__":
    render(fetch_stats())
