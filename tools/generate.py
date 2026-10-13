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


def _rgb(hexc):
    h = hexc.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _on_accent(hexc):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g_, b = (lin(v) for v in _rgb(hexc))
    lum = 0.2126 * r + 0.7152 * g_ + 0.0722 * b
    return "#0b0c10" if lum > 0.32 else "#ffffff"


def _initials(name):
    words = name.split()
    if words and len(words[0]) <= 3:
        return words[0].upper()
    return "".join(w[0] for w in words[:2]).upper()


ICON_PHONE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/></svg>'
ICON_PIN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>'


def render(g):
    img = g.get("images", {})
    name = g["name"]
    area, city = g["area"], g["city"]
    loc = f"{area}, {city}"
    phone = g.get("phone")
    accent = g.get("accent", "#ff4d2e")
    ar, ag, ab = _rgb(accent)
    on_accent = _on_accent(accent)
    services = g.get("services", [])
    rating, reviews = g.get("rating"), g.get("reviews")
    published = str(g.get("status", "")).lower() == "delivered"
    maps_q = quote_plus(g.get("tagline_name") or f"{name} {area} {city}")
    maps_link = f"https://www.google.com/maps/search/?api=1&query={maps_q}"
    maps_embed = f"https://www.google.com/maps?q={maps_q}&output=embed"
    tel_href = f"tel:{tel(phone)}" if phone else ""
    wa_href = f"https://wa.me/{tel(phone).lstrip('+')}" if phone else ""
    initials = _initials(name)
    lead = (f"A {area} gym, rated {rating} on Google by {reviews} members." if rating and reviews else g["about"])

    favicon = ("data:image/svg+xml," + quote_plus(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="16" fill="{accent}"/>'
        f'<text x="32" y="42" font-family="Arial" font-weight="800" font-size="{26 if len(initials) < 3 else 20}" text-anchor="middle" fill="{on_accent}">{initials}</text></svg>'))

    ld = {"@context": "https://schema.org", "@type": "ExerciseGym", "name": name,
          "address": {"@type": "PostalAddress", "streetAddress": g["address"], "addressLocality": city, "addressCountry": "IN"}}
    if phone:
        ld["telephone"] = tel(phone)
    ld_json = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")

    desc = f"{name} in {loc}." + (f" Rated {rating} on Google." if rating else "") + (f" {', '.join(services[:5])}." if services else "")
    robots = "" if published else '  <meta name="robots" content="noindex, nofollow">\n'

    preview_bar = (f'<div class="preview-bar"><strong>Design preview</strong> &mdash; not the official website of {e(name)}.</div>'
                   if str(g.get("status", "")).lower().startswith("prospect") else "")

    nav = ['<a href="#about">About</a>']
    if services:
        nav.append('<a href="#services">Services</a>')
    if img.get("team"):
        nav.append('<a href="#gallery">Gallery</a>')
    nav.append('<a href="#contact">Contact</a>')
    nav_html = "\n        ".join(nav)
    nav_cta = (f'<a class="btn sm nav-cta" href="{tel_href}">Call now</a>' if phone
               else '<a class="btn sm nav-cta" href="#contact">Visit us</a>')

    hero_img = (f'<img class="hero-img" src="assets/images/{e(img["hero"])}" alt="" fetchpriority="high">'
                if img.get("hero") else "")
    hero_cls = "hero" if img.get("hero") else "hero noimg"
    primary = (f'<a class="btn" href="{tel_href}">{ICON_PHONE}Call {e(phone)}</a>' if phone
               else f'<a class="btn" target="_blank" rel="noopener" href="{maps_link}">{ICON_PIN}Get directions</a>')
    secondary = f'<a class="btn ghost" href="#about">Explore</a>' if not services else '<a class="btn ghost" href="#services">Our services</a>'

    stats = []
    if rating:
        stats.append(f'<div class="stat reveal"><b><span class="star">&#9733;</span> {rating}</b><span>Google rating</span></div>')
    if reviews:
        stats.append(f'<div class="stat reveal"><b>{reviews}+</b><span>Member reviews</span></div>')
    stats.append(f'<div class="stat reveal"><b>{e(area)}</b><span>{e(city)}</span></div>')
    stats_html = "\n        ".join(stats)

    ticker = ""
    if len(services) >= 3:
        spans = "".join(f"<span>{e(s)}</span>" for s in (services * (2 if len(services) > 5 else 3)))
        ticker = f'<div class="ticker" aria-hidden="true"><div class="ticker-track">{spans}{spans}</div></div>'

    about_side = (f'<img class="about-img reveal" src="assets/images/{e(img["about"])}" alt="Inside {e(name)}" loading="lazy">'
                  if img.get("about") else
                  (f'<div class="rating-card reveal"><div class="big">{rating}</div><div class="stars" aria-hidden="true">&#9733;&#9733;&#9733;&#9733;&#9733;</div>'
                   f'<p>Google rating from {reviews} reviews</p></div>' if rating and reviews else ""))

    services_html = ""
    if services:
        cards = "\n".join(
            f'        <article class="card reveal"><span class="num" aria-hidden="true">{i:02d}</span><h3>{e(sv)}</h3>'
            f'<p>{e(SERVICE_BLURBS.get(sv.lower(), GENERIC_BLURB))}</p></article>'
            for i, sv in enumerate(services, 1))
        services_html = f'''
    <section id="services" class="section alt">
      <div class="container">
        <div class="section-head reveal"><span class="kicker">What we offer</span><h2>Train your way</h2></div>
        <div class="cards">
{cards}
        </div>
      </div>
    </section>
'''

    gallery_html = ""
    if img.get("team"):
        figs = "\n".join(f'          <figure class="reveal"><img src="assets/images/{e(t)}" alt="{e(name)} team and members" loading="lazy"></figure>' for t in img["team"])
        gallery_html = f'''
    <section id="gallery" class="section">
      <div class="container">
        <div class="section-head reveal"><span class="kicker">Our community</span><h2>The people behind the weights</h2></div>
        <div class="gallery">
{figs}
        </div>
      </div>
    </section>
'''

    band_btns = (f'<a class="btn" href="{tel_href}">{ICON_PHONE}Call {e(phone)}</a>' if phone
                 else f'<a class="btn" href="#contact">{ICON_PIN}Find us</a>')
    band_p = "Ask about current membership offers." if phone else "Drop in to ask about current membership offers."

    hours_html = ""
    if g.get("hours"):
        rows = "\n".join(f'              <li><span>{e(h["days"])}</span><span>{e(h["time"])}</span></li>' for h in g["hours"])
        hours_html = f'<div><dt>Hours</dt><dd><ul class="hours">\n{rows}\n            </ul></dd></div>'
    phone_html = (f'<div><dt>Phone</dt><dd><a class="link" href="{tel_href}">{e(phone)}</a></dd></div>' if phone else "")
    contact_btns = (f'<a class="btn" href="{tel_href}">{ICON_PHONE}Call</a>'
                    f'<a class="btn ghost" target="_blank" rel="noopener" href="{wa_href}">WhatsApp</a>' if phone else "")
    contact_btns += f'<a class="btn ghost" target="_blank" rel="noopener" href="{maps_link}">{ICON_PIN}Directions</a>'

    mobile_bar = (f'<div class="mobile-bar"><a class="btn" href="{tel_href}">{ICON_PHONE}Call</a>'
                  f'<a class="btn ghost" target="_blank" rel="noopener" href="{maps_link}">{ICON_PIN}Directions</a></div>' if phone else
                  f'<div class="mobile-bar"><a class="btn" target="_blank" rel="noopener" href="{maps_link}">{ICON_PIN}Get directions</a></div>')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(name)} | Gym in {e(loc)}</title>
  <meta name="description" content="{e(desc)}">
{robots}  <meta name="theme-color" content="#08090c">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{e(name)} | Gym in {e(loc)}">
  <meta property="og:description" content="{e(desc)}">
  <link rel="icon" href="{favicon}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/css/style.css">
  <style>:root{{--accent:{accent};--accent-rgb:{ar},{ag},{ab};--on-accent:{on_accent}}}</style>
  <script>document.documentElement.classList.add("js")</script>
  <script type="application/ld+json">{ld_json}</script>
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
  {preview_bar}
  <header class="site-header">
    <div class="container nav">
      <a class="brand" href="#top" aria-label="{e(name)} home"><span class="brand-mark">{e(initials)}</span>{e(name)}</a>
      <nav id="nav-links" class="nav-links" aria-label="Main">
        {nav_html}
      </nav>
      {nav_cta}
      <button class="menu-btn" type="button" aria-label="Menu" aria-expanded="false" aria-controls="nav-links"><span></span></button>
    </div>
  </header>

  <main id="main">
    <section id="top" class="{hero_cls}">
      {hero_img}
      <div class="container">
        <span class="pill"><i></i>{e(loc)}</span>
        <h1>Stronger every day at <em>{e(name)}</em></h1>
        <p class="lead">{e(lead)}</p>
        <div class="cta">
          {primary}
          {secondary}
        </div>
      </div>
    </section>

    <div class="stats"><div class="container stats-grid">
        {stats_html}
    </div></div>
    {ticker}

    <section id="about" class="section">
      <div class="container about">
        <div class="reveal">
          <span class="kicker">About</span>
          <h2>{e(name)}</h2>
          <p>{e(g["about"])}</p>
        </div>
        {about_side}
      </div>
    </section>
{services_html}{gallery_html}
    <section class="section{" alt" if not services else ""}">
      <div class="container">
        <div class="band reveal">
          <div><h2>Ready to start?</h2><p>{band_p}</p></div>
          <div class="cta">{band_btns}</div>
        </div>
      </div>
    </section>

    <section id="contact" class="section{" alt" if services else ""}">
      <div class="container">
        <div class="section-head reveal"><span class="kicker">Find us</span><h2>Visit {e(name)}</h2></div>
        <div class="contact">
          <div class="info reveal">
            <dl>
              <div><dt>Address</dt><dd>{e(g["address"])}</dd></div>
              {hours_html}
              {phone_html}
            </dl>
            <div class="cta">{contact_btns}</div>
          </div>
          <div class="map reveal"><iframe title="Map to {e(name)}" src="{maps_embed}" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe></div>
        </div>
      </div>
    </section>
  </main>

  <footer>
    <div class="container">
      {"<p>Design preview &mdash; not the official website of " + e(name) + ".</p>" if preview_bar else ""}
      <p>&copy; <span id="year"></span> {e(name)}, {e(city)}</p>
    </div>
  </footer>
  {mobile_bar}
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
