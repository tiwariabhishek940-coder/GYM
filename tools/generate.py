#!/usr/bin/env python3
"""Generate a gym website from sites/<slug>/gym.json.

Usage: python3 tools/generate.py <slug> [<slug> ...]
Writes index.html, assets/css|js, README.md in sites/<slug>/ and updates the
Sites table in the root README.md. Existing files in assets/images are kept.
"""
import html, json, re, shutil, sys
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "tools" / "site_template"

SERVICE_BLURBS = {
    "weight training": "Build strength with a full range of equipment.",
    "personal training": "One-to-one coaching built around your goals.",
    "crossfit": "High-intensity functional training.",
    "hiit": "Fast, fat-burning interval workouts.",
    "cycling": "Group cycling for stamina and cardio.",
    "aerobics": "Energetic classes for all levels.",
    "zumba": "Dance-based cardio that feels like a party.",
    "dance fitness": "Burn calories with music and movement.",
    "yoga": "Flexibility, balance and calm.",
    "nutrition consulting": "Diet guidance to match your goals.",
}
GENERIC_BLURB = "Ask our team for details."


def e(s):
    return html.escape(str(s), quote=True)


def tel(phone):
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10:
        digits = "91" + digits
    return "+" + digits


def render(g):
    img = g.get("images", {})
    phone = g.get("phone")
    loc = f'{g["area"]}, {g["city"]}'
    name = g["name"]
    maps_q = quote_plus(g.get("tagline_name") or f'{name} {g["area"]} {g["city"]}')

    hero_style = f' style="--hero:url(../images/{e(img["hero"])})"' if img.get("hero") else ""
    hero_cls = "hero" if img.get("hero") else "hero noimg"
    primary_cta = (f'<a class="btn" href="tel:{tel(phone)}">Call {e(phone)}</a>'
                   if phone else '<a class="btn" href="#contact">Contact us</a>')
    rating = ""
    if g.get("rating") and g.get("reviews"):
        rating = f'<p class="rating">&#9733; {g["rating"]} on Google &middot; {g["reviews"]} reviews</p>'

    about_img = (f'<img src="assets/images/{e(img["about"])}" alt="{e(name)} gym floor" loading="lazy">'
                 if img.get("about") else "")
    about_body = f'<div class="about"><p>{e(g["about"])}</p>{about_img}</div>' if about_img else f'<p>{e(g["about"])}</p>'

    cards = "\n".join(
        f'        <div class="card"><h3>{e(s)}</h3><p>{e(SERVICE_BLURBS.get(s.lower(), GENERIC_BLURB))}</p></div>'
        for s in g.get("services", []))

    team_imgs = img.get("team", [])
    team = ""
    if team_imgs:
        imgs = "\n".join(f'        <img src="assets/images/{e(t)}" alt="{e(name)} team" loading="lazy">' for t in team_imgs)
        team = f'''
    <section id="team" class="section alt">
      <h2>Our team &amp; community</h2>
      <div class="team">
{imgs}
      </div>
    </section>
'''
    team_nav = '\n      <a href="#team">Team</a>' if team else ""

    hours = ""
    if g.get("hours"):
        rows = "\n".join(f'        <li><span>{e(h["days"])}</span><span>{e(h["time"])}</span></li>' for h in g["hours"])
        hours = f'<p><strong>Hours:</strong></p>\n      <ul class="hours">\n{rows}\n      </ul>'
    phone_p = f'<p><strong>Phone:</strong> <a href="tel:{tel(phone)}">{e(phone)}</a></p>' if phone else ""
    plans_btn = (f'<p style="margin-top:16px"><a class="btn" href="tel:{tel(phone)}">Call for current offers</a></p>'
                 if phone else "")

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(name)} | {e(loc)}</title>
  <meta name="description" content="{e(name)} in {e(loc)}. {e(', '.join(g.get('services', [])[:5]))}.">
  <link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
  <header class="nav">
    <a class="logo" href="#top">{e(name)}</a>
    <nav>
      <a href="#about">About</a>
      <a href="#services">Services</a>{team_nav}
      <a href="#plans">Plans</a>
      <a href="#contact">Contact</a>
    </nav>
  </header>

  <main id="top">
    <section class="{hero_cls}"{hero_style}>
      <p class="eyebrow">{e(loc)}</p>
      <h1>Stronger every day at <span>{e(name)}</span></h1>
      <p class="lead">Strength, cardio and classes under one roof, with trainers who keep you on track.</p>
      <div class="cta">
        {primary_cta}
        <a class="btn ghost" href="#services">Explore services</a>
      </div>
      {rating}
    </section>

    <section id="about" class="section">
      <h2>About us</h2>
      {about_body}
    </section>

    <section id="services" class="section alt">
      <h2>Services</h2>
      <div class="grid">
{cards}
      </div>
    </section>
{team}
    <section id="plans" class="section">
      <h2>Membership plans</h2>
      <p class="note">Flexible monthly, quarterly and yearly memberships. Call us for current offers.</p>
      {plans_btn}
    </section>

    <section id="contact" class="section alt">
      <h2>Visit us</h2>
      <p><strong>Address:</strong> {e(g["address"])}</p>
      {hours}
      {phone_p}
      <a class="btn" target="_blank" rel="noopener" href="https://www.google.com/maps/search/?api=1&query={maps_q}">Get directions</a>
    </section>
  </main>

  <footer>&copy; <span id="year"></span> {e(name)}, {e(g["city"])}</footer>
  <script src="assets/js/main.js"></script>
</body>
</html>
'''


def update_root_readme(g):
    p = ROOT / "README.md"
    text = p.read_text()
    row_link = f'[sites/{g["slug"]}](sites/{g["slug"]})'
    lines = text.split("\n")
    out, found, last_row = [], False, None
    for i, ln in enumerate(lines):
        if ln.startswith("| - | _none yet_"):
            continue
        if f"sites/{g['slug']})" in ln:
            m = re.match(r"\| (\d+) \|", ln)
            num = m.group(1) if m else "?"
            ln = f'| {num} | {g["name"]} | {row_link} | - | {g.get("status", "Draft")} |'
            found = True
        if ln.startswith("| ") and re.match(r"\| \d+ \|", ln):
            last_row = len(out)
        out.append(ln)
    if not found:
        nums = [int(m.group(1)) for ln in out if (m := re.match(r"\| (\d+) \|", ln))]
        row = f'| {max(nums, default=0) + 1} | {g["name"]} | {row_link} | - | {g.get("status", "Draft")} |'
        if last_row is None:
            idx = next(i for i, ln in enumerate(out) if ln.startswith("|---"))
            out.insert(idx + 1, row)
        else:
            out.insert(last_row + 1, row)
    p.write_text("\n".join(out))


def build(slug):
    d = ROOT / "sites" / slug
    cfg = d / "gym.json"
    if not cfg.exists():
        sys.exit(f"missing {cfg}")
    g = json.loads(cfg.read_text())
    g["slug"] = slug
    (d / "assets" / "css").mkdir(parents=True, exist_ok=True)
    (d / "assets" / "js").mkdir(parents=True, exist_ok=True)
    (d / "assets" / "images").mkdir(parents=True, exist_ok=True)
    shutil.copy(TPL / "style.css", d / "assets" / "css" / "style.css")
    shutil.copy(TPL / "main.js", d / "assets" / "js" / "main.js")
    (d / "index.html").write_text(render(g))
    (d / "README.md").write_text(
        f'# {g["name"]}\n\n- **Client / Gym:** {g["name"]}\n- **Location:** {g["address"]}\n'
        + (f'- **Phone:** {g["phone"]}\n' if g.get("phone") else "")
        + f'- **Stack:** HTML / CSS / JS (generated by `tools/generate.py` from `gym.json`)\n'
        f'- **Live URL:** \n- **Status:** {g.get("status", "Draft")}\n')
    update_root_readme(g)
    print("built", slug)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for s in sys.argv[1:]:
        build(s)
