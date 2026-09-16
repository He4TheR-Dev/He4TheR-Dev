"""Refresh all profile stats widgets from live GitHub / public card APIs."""
from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
WIDGETS = ASSETS / "widgets"
README = ROOT / "README.md"
USER = os.environ.get("STATS_USER") or "He4TheR-Dev"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def font(size: int):
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        r"C:\Windows\Fonts\seguisb.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
    ):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def http_get(url: str, accept: str = "*/*") -> bytes:
    headers = {
        "Accept": accept,
        "User-Agent": "he4ther-stats-refresh",
    }
    if TOKEN and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def api_json(url: str):
    return json.loads(http_get(url, "application/vnd.github+json").decode("utf-8"))


def fetch_stats():
    user = api_json(f"https://api.github.com/users/{USER}")
    repos = api_json(
        f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&sort=updated"
    )
    own = [r for r in repos if not r.get("fork")]
    stars = sum(r.get("stargazers_count", 0) for r in own)
    langs: dict[str, int] = {}
    for r in own:
        # Prefer accurate language bytes from the Languages API
        try:
            detail = api_json(r["languages_url"])
            for lang, bytes_count in detail.items():
                langs[lang] = langs.get(lang, 0) + int(bytes_count)
        except Exception:
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
        "lang_bytes": langs,
    }


def render_hero(stats: dict):
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
    out = ASSETS / "stats-hero.png"
    img.save(out, optimize=True)
    print(f"hero repos={stats['repos']} primary={stats['primary']} langs={stats['langs']}")


def download_widgets():
    WIDGETS.mkdir(parents=True, exist_ok=True)
    sources = {
        "streak.svg": (
            "https://streak-stats.demolab.com"
            f"?user={USER}&hide_border=true&background=08080c&ring=c050ff&fire=c050ff"
            "&currStreakNum=e8e8f0&sideNums=e8e8f0&currStreakLabel=c050ff"
            "&sideLabels=a0a0b0&dates=707080&border_radius=12"
        ),
        "repos-per-language.svg": (
            "https://github-profile-summary-cards.vercel.app/api/cards/repos-per-language"
            f"?username={USER}&theme=radical"
        ),
        "most-commit-language.svg": (
            "https://github-profile-summary-cards.vercel.app/api/cards/most-commit-language"
            f"?username={USER}&theme=radical"
        ),
        "profile-details.svg": (
            "https://github-profile-summary-cards.vercel.app/api/cards/profile-details"
            f"?username={USER}&theme=radical"
        ),
        "contribution-stats.svg": (
            f"https://github-contribution-stats.vercel.app/api?username={USER}"
        ),
    }
    for name, url in sources.items():
        try:
            data = http_get(url)
            # reject tiny error payloads
            if len(data) < 800 or b"Maximum retries" in data or b"Something went wrong" in data:
                print(f"skip bad widget {name} len={len(data)}")
                continue
            path = WIDGETS / name
            path.write_bytes(data)
            print(f"saved {path.name} ({len(data)} bytes)")
        except Exception as exc:
            print(f"failed {name}: {exc}")


def patch_readme():
    """Ensure README points at local refreshed widget assets."""
    if not README.exists():
        return
    text = README.read_text(encoding="utf-8")
    replacements = [
        (
            r'https://streak-stats\.demolab\.com\?[^"\s]+',
            "assets/widgets/streak.svg",
        ),
        (
            r'https://github-profile-summary-cards\.vercel\.app/api/cards/repos-per-language\?[^"\s]+',
            "assets/widgets/repos-per-language.svg",
        ),
        (
            r'https://github-profile-summary-cards\.vercel\.app/api/cards/most-commit-language\?[^"\s]+',
            "assets/widgets/most-commit-language.svg",
        ),
        (
            r'https://github-profile-summary-cards\.vercel\.app/api/cards/profile-details\?[^"\s]+',
            "assets/widgets/profile-details.svg",
        ),
        (
            r'https://github-contribution-stats\.vercel\.app/api\?[^"\s]+',
            "assets/widgets/contribution-stats.svg",
        ),
    ]
    new = text
    for pattern, repl in replacements:
        new = re.sub(pattern, repl, new)
    # Also normalize already-local paths (no-op) and ensure block uses local widgets
    if "assets/widgets/streak.svg" not in new:
        # inject standard metrics block markers if missing
        pass
    if new != text:
        README.write_text(new, encoding="utf-8")
        print("README widget URLs updated to local assets")
    else:
        print("README already uses local widgets or unchanged")


if __name__ == "__main__":
    stats = fetch_stats()
    render_hero(stats)
    download_widgets()
    patch_readme()
