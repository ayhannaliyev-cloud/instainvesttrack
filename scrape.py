"""Collect public Instagram numbers for the accounts in accounts.json.

Opens each profile in a real (headless) Chromium without logging in, the
same way a visitor sees it: reads the follower/post counts from the page
and the likes/comments of every post visible on the profile.

Writes docs/data/latest.json (what the page shows) and appends one row per
account per day to docs/data/history.json. If an account can't be read,
its last good numbers are kept and marked with the date they are from.
"""
import html
import json
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
WINDOW_DAYS = 14
BAKU = timezone(timedelta(hours=4))

# Runs inside the profile page: fetch each visible post's page and read its
# description meta ("42 likes, 5 comments - abb.invest on October 14, 2026: "...").
READ_POSTS_JS = """
async () => {
  const links = [...new Set([...document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]')]
    .map(a => a.getAttribute('href')))];
  const out = [];
  for (const u of links) {
    try {
      const t = await fetch(u).then(r => r.text());
      const d = new DOMParser().parseFromString(t, 'text/html');
      out.push({u, meta: d.querySelector('meta[name="description"]')?.content || ''});
    } catch (e) { out.push({u, meta: ''}); }
  }
  return out;
}
"""

POST_RE = re.compile(
    r'^(?:([\d,.]+[KM]?) likes?, ([\d,.]+[KM]?) comments? - )?(\S+) on (\w+ \d{1,2}, \d{4}): "(.*)"',
    re.S,
)
PROFILE_RE = re.compile(r"([\d,.]+[KM]?) Followers, ([\d,.]+[KM]?) Following, ([\d,.]+[KM]?) Posts")


def num(s):
    """'6,917' -> 6917, '14K' -> 14000, '1.2M' -> 1200000."""
    if s is None:
        return None
    s = s.replace(",", "")
    mult = 1000 if s.endswith("K") else 1_000_000 if s.endswith("M") else 1
    return int(round(float(s.rstrip("KM")) * mult))


def topic(caption):
    text = re.sub(r"\s+", " ", html.unescape(caption or "")).strip()
    return text if len(text) <= 90 else text[:89].rstrip() + "…"


def read_account(page, account, name, today):
    page.goto(f"https://www.instagram.com/{account}/", wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_selector('a[href*="/p/"], a[href*="/reel/"]', timeout=20000)
    except Exception:
        pass  # a profile with no posts, or the grid did not load; counts may still be there
    meta = page.get_attribute('meta[name="description"]', "content") or ""
    m = PROFILE_RE.search(meta)
    if not m:
        raise RuntimeError(f"{account}: profil rəqəmləri tapılmadı (Instagram giriş tələb edə bilər)")
    followers, following, posts_total = (num(x) for x in m.groups())

    window_start = today - timedelta(days=WINDOW_DAYS - 1)
    posts, last_day = [], None
    for item in page.evaluate(READ_POSTS_JS):
        pm = POST_RE.match(item["meta"])
        if not pm:
            continue
        likes, comments, author, day_s, caption = pm.groups()
        day = datetime.strptime(day_s, "%B %d, %Y").date()
        last_day = day  # grid is newest first after pinned posts, so the last link is the oldest visible
        if day < window_start:
            continue
        kind = "Reels" if "/reel/" in item["u"] else "Post"
        code = item["u"].strip("/").split("/")[-1]
        posts.append({
            "key": f"{account}:{code}",
            "account": account,
            "date": day.isoformat(),
            "type": kind,
            "author": author,
            "collab": author != account,
            "likes": num(likes),
            "comments": num(comments),
            "topic": topic(caption),
            "url": f"https://www.instagram.com/{'reel' if kind == 'Reels' else 'p'}/{code}/",
        })

    visible_from = last_day or today
    row = {
        "account": account,
        "name": name,
        "followers": followers,
        "following": following,
        "posts_total": posts_total,
        "rounded": any(x.endswith(("K", "M")) for x in m.groups()[:1]),
        "visible_from": visible_from.isoformat(),
        "complete": visible_from <= window_start,
        "data_date": today.isoformat(),
    }
    return row, posts


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def main():
    accounts = json.loads((ROOT / "accounts.json").read_text(encoding="utf-8"))
    today = datetime.now(BAKU).date()
    prev = load(DATA / "latest.json", {"accounts": [], "posts": []})
    prev_acc = {a["account"]: a for a in prev.get("accounts", [])}
    rows, posts, failed = [], [], []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(locale="en-US", viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        for i, a in enumerate(accounts):
            if i:
                time.sleep(3)
            try:
                row, ps = read_account(page, a["account"], a["name"], today)
                rows.append(row)
                posts.extend(ps)
                print(f"ok   {a['account']}: {row['followers']} izləyici, {len(ps)} post (2 həftə)")
            except Exception as e:  # keep the last good numbers for this account
                failed.append(a["account"])
                print(f"FAIL {a['account']}: {e}", file=sys.stderr)
                if a["account"] in prev_acc:
                    rows.append(prev_acc[a["account"]])
                    posts.extend(x for x in prev.get("posts", []) if x["account"] == a["account"])
        browser.close()

    if len(failed) == len(accounts):
        print("Heç bir hesab oxunmadı; köhnə məlumat saxlanılır.", file=sys.stderr)
        sys.exit(1)

    latest = {
        "updated_at": datetime.now(BAKU).isoformat(timespec="minutes"),
        "window_start": (today - timedelta(days=WINDOW_DAYS - 1)).isoformat(),
        "window_end": today.isoformat(),
        "failed": failed,
        "accounts": rows,
        "posts": posts,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=1), encoding="utf-8")

    history = [h for h in load(DATA / "history.json", []) if h["date"] != today.isoformat()]
    history += [{"date": today.isoformat(), "account": r["account"], "followers": r["followers"],
                 "posts_total": r["posts_total"]} for r in rows if r.get("data_date") == today.isoformat()]
    (DATA / "history.json").write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
    print(f"Yazıldı: {len(rows)} hesab, {len(posts)} post; oxunmayan: {', '.join(failed) or 'yoxdur'}")


if __name__ == "__main__":
    main()
