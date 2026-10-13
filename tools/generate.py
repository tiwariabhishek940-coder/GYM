#!/usr/bin/env python3
"""Generate a gym website from sites/<slug>/gym.json.

Usage: python3 tools/generate.py <slug> [<slug> ...]   |   python3 tools/generate.py --all
Writes index.html, assets/css|js, README.md in sites/<slug>/ and updates the
Sites table in the root README.md. Existing files in assets/images are kept.

gym.json fields (all optional except slug-folder, name, area, city):
  name, tagline_name, area, city, address, phone, rating, reviews, rating_source,
  hours [{days,time}], services [..], blurbs (true = show short service blurbs),
  about, lead, accent (#hex), images {hero, about, team [file | {file, alt}]},
  status ("Prospect draft" | "Draft" | "Delivered"), live_url
Unknown facts must be left out: nothing is invented by the template.
"""
import html, json, re, shutil, sys
from pathlib import Path
from urllib.parse import quote, quote_plus

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
    "cardio": "Treadmills, bikes and cardio training.",
    "strength training": "Build strength with weights and machines.",
    "boxing": "Boxing-based conditioning.",
}
STOP_WORDS = {"the", "a", "an", "and", "of", "by"}


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


def _lum(rgb):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _on_accent(hexc):
    """Pick white or near-black text, whichever has the higher WCAG contrast against the accent."""
    l = _lum(_rgb(hexc))
    white = 1.05 / (l + 0.05)
    dark = (l + 0.05) / (_lum((11, 12, 16)) + 0.05)
    return "#ffffff" if white >= dark else "#0b0c10"


def _initials(name):
    words = [re.sub(r"[^A-Za-z0-9]", "", w) for w in name.split()]
    words = [w for w in words if w and w.lower() not in STOP_WORDS] or [w for w in words if w] or ["G"]
    if len(words[0]) <= 3:
        return words[0].upper()
    return "".join(w[0] for w in words[:2]).upper()


ICON_PHONE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/></svg>'
ICON_PIN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>'


ICON_ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 17 17 7M8 7h9v9"/></svg>'


def render(g):
    img = g.get("images") or {}
    name = g["name"]
    area, city = g["area"], g["city"]
    loc = f"{area}, {city}"
    phone = g.get("phone")
    address = g.get("address")
    accent = g.get("accent", "#d6ff4a")
    ar, ag, ab = _rgb(accent)
    on_accent = _on_accent(accent)
    services = g.get("services") or []
    blurbs = bool(g.get("blurbs"))
    rating, reviews = g.get("rating"), g.get("reviews")
    src = g.get("rating_source")
    status = str(g.get("status", ""))
    published = status.lower() == "delivered"
    prospect = status.lower().startswith("prospect")
    maps_q = quote_plus(g.get("tagline_name") or f"{name} {area} {city}")
    maps_link = f"https://www.google.com/maps/search/?api=1&query={maps_q}"
    maps_embed = f"https://www.google.com/maps?q={maps_q}&output=embed"
    tel_href = f"tel:{tel(phone)}" if phone else ""
    wa_href = f"https://wa.me/{tel(phone).lstrip('+')}" if phone else ""
    initials = _initials(name)
    has_hero_img = bool(img.get("hero"))
    lead = g.get("lead")
    whatsapp = bool(g.get("whatsapp")) and bool(phone)
    lead_html = f'<p class="lead">{e(lead)}</p>' if lead else ""
    team = img.get("team") or []

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="16" fill="{accent}"/>'
           f'<text x="32" y="42" font-family="Arial" font-weight="800" font-size="{26 if len(initials) < 3 else 20}" '
           f'text-anchor="middle" fill="{on_accent}">{html.escape(initials, quote=False)}</text></svg>')
    favicon = "data:image/svg+xml," + quote(svg, safe="")

    title = f"{name} | Design preview (unofficial)" if prospect else f"{name} | Gym in {loc}"
    desc = (f"Unofficial design preview for {name}, {loc}." if prospect else
            f"{name} in {loc}." + (f" {', '.join(services[:5])}." if services else ""))
    robots = "" if published else '  <meta name="robots" content="noindex, nofollow">\n'

    ld_block = ""
    if not prospect:
        ld = {"@context": "https://schema.org", "@type": "ExerciseGym", "name": name,
              "address": {"@type": "PostalAddress", "addressLocality": city, "addressCountry": "IN"}}
        if address:
            ld["address"]["streetAddress"] = address
        if phone:
            ld["telephone"] = tel(phone)
        ld_block = '  <script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"

    preview_bar = (f'<div class="preview-bar" role="region" aria-label="Design preview notice"><strong>Design preview</strong>'
                   f'<span class="pb-long"> &mdash; unofficial, not the website of {e(name)}.</span><span class="pb-short"> &middot; unofficial</span></div>'
                   if prospect else "")

    nav = []
    if g.get("about"):
        nav.append('<a href="#about">About</a>')
    if services:
        nav.append('<a href="#services">Services</a>')
    if team:
        nav.append('<a href="#gallery">Gallery</a>')
    nav.append('<a href="#visit">Visit</a>')
    nav_html = "\n        ".join(nav)
    has_menu = len(nav) > 1
    menu_html = ('<button class="menu-btn" type="button" aria-label="Menu" aria-expanded="false" aria-controls="nav-links"><span></span></button>\n'
                 f'      <nav id="nav-links" class="nav-links" aria-label="Main">\n        {nav_html}\n      </nav>') if has_menu else ""
    sparse = not (services or g.get("about") or team)
    nav_cta = (f'<a class="btn sm nav-cta" href="{tel_href}">Call now</a>' if phone
               else '<a class="btn sm nav-cta" href="#visit">Visit us</a>')

    # hero
    hero_img = (f'<img class="hero-img" src="assets/images/{e(img["hero"])}" alt="" fetchpriority="high">' if has_hero_img else "")
    hero_cls = "hero img" if has_hero_img else "hero"
    primary = (f'<a class="btn" href="{tel_href}">{ICON_PHONE}Call {e(phone)}</a>' if phone
               else f'<a class="btn" target="_blank" rel="noopener" href="{maps_link}">{ICON_PIN}Get directions</a>')
    second_href = "#services" if services else ("#about" if g.get("about") else "#visit")
    second_txt = "See services" if services else ("About" if g.get("about") else "Visit")
    secondary = "" if sparse else f'<a class="btn ghost" href="{second_href}">{second_txt}</a>'

    pass_card = ""
    if rating and reviews:
        pct = max(0, min(100, round(float(rating) / 5 * 100)))
        tag = f"{src} rating" if src else "Rating"
        meta = [f"<span><b>{reviews}</b> reviews</span>"]
        if g.get("hours"):
            h0 = g["hours"][0]
            meta.append(f'<span>{e(h0["days"])}: {e(h0["time"])}</span>')
        pass_card = (f'<aside class="pass reveal" aria-label="Rating"><div class="tag"><span>{e(tag)}</span><span>{e(area)}</span></div>'
                     f'<div class="score">{rating}</div>'
                     f'<div class="stars" style="--p:{pct}%" role="img" aria-label="Rated {rating} out of 5">&#9733;&#9733;&#9733;&#9733;&#9733;</div>'
                     f'<div class="meta">{"".join(meta)}</div></aside>')
    grid_cls = "wrap hero-grid" if pass_card else "wrap hero-grid one"

    sections = []
    if g.get("about"):
        side = (f'<img class="shot tall reveal" src="assets/images/{e(img["about"])}" alt="Inside {e(name)}" loading="lazy">'
                if img.get("about") else "")
        cls = "wrap about" if side else "wrap about solo"
        sections.append(f'''    <section id="about" class="section%%ALT%%">
      <div class="{cls}">
        <div class="reveal">
          <span class="eyebrow">About</span>
          <p class="statement">{e(g["about"])}</p>
        </div>
        {side}
      </div>
    </section>''')

    if services:
        rows = []
        for i, sv in enumerate(services, 1):
            b = SERVICE_BLURBS.get(sv.lower()) if blurbs else None
            rows.append(f'        <li class="reveal{"" if b else " nop"}"><span class="no" aria-hidden="true">{i:02d}</span><h3>{e(sv)}</h3>'
                        + (f'<p>{e(b)}</p>' if b else "") + f'<a class="go" href="#visit" aria-label="Contact {e(name)} about {e(sv)}">{ICON_ARROW}</a></li>')
        sections.append(f'''    <section id="services" class="section%%ALT%%">
      <div class="wrap">
        <div class="sec-head reveal"><h2 class="disp h2">Train <em class="serif">your</em> way</h2><span class="eyebrow">What&rsquo;s on offer</span></div>
        <ul class="list">
{chr(10).join(rows)}
        </ul>
      </div>
    </section>''')

    if team:
        figs = []
        for i, t in enumerate(team, 1):
            f_, alt = (t, f"{name} photo {i} of {len(team)}") if isinstance(t, str) else (t["file"], t.get("alt") or f"{name} photo {i} of {len(team)}")
            figs.append(f'          <figure class="reveal"><img src="assets/images/{e(f_)}" alt="{e(alt)}" loading="lazy"></figure>')
        grid = "bento" if len(team) >= 3 else "duo"
        sections.append(f'''    <section id="gallery" class="section%%ALT%%">
      <div class="wrap">
        <div class="sec-head reveal"><h2 class="disp h2">Inside the <em class="serif">gym</em></h2><span class="eyebrow">Gallery</span></div>
        <div class="{grid}">
{chr(10).join(figs)}
        </div>
      </div>
    </section>''')

    band_btns = (f'<a class="btn dark" href="{tel_href}">{ICON_PHONE}Call {e(phone)}</a>'
                 f'<a class="btn ghost" target="_blank" rel="noopener" href="{maps_link}">Directions</a>' if phone
                 else f'<a class="btn dark" target="_blank" rel="noopener" href="{maps_link}">{ICON_PIN}Directions</a>')
    if not sparse:
        sections.append(f'''    <section class="section">
      <div class="wrap">
        <div class="cta-block reveal">
          <h2 class="disp">Come see it <em class="serif">in person.</em></h2>
          <div class="cta">{band_btns}</div>
        </div>
      </div>
    </section>''')

    info = []
    if address:
        note = '<span class="note">As listed publicly, not yet confirmed with the gym.</span>' if prospect else ""
        info.append(f'<div><dt>Address</dt><dd>{e(address)}{note}</dd></div>')
    if prospect and rating and reviews:
        info.append(f'<div><dt>Rating</dt><dd>{rating} from {reviews} reviews<span class="note">{"Source: " + e(src) + " listing, not verified." if src else "From a public listing, not verified."}</span></dd></div>')
    if g.get("hours"):
        hrows = "\n".join(f'              <li><span>{e(h["days"])}</span><span>{e(h["time"])}</span></li>' for h in g["hours"])
        info.append(f'<div><dt>Hours</dt><dd><ul class="hours">\n{hrows}\n            </ul></dd></div>')
    if phone:
        info.append(f'<div><dt>Phone</dt><dd><a class="link" href="{tel_href}">{e(phone)}</a></dd></div>')
    contact_btns = (f'<a class="btn" href="{tel_href}">{ICON_PHONE}Call</a>'
                    f'<a class="btn ghost" target="_blank" rel="noopener" href="{wa_href}">WhatsApp</a>' if whatsapp else "")
    if phone and not whatsapp:
        contact_btns = f'<a class="btn" href="{tel_href}">{ICON_PHONE}Call</a>'
    contact_btns += f'<a class="btn{" ghost" if phone else ""}" target="_blank" rel="noopener" href="{maps_link}">{ICON_PIN}Directions</a>'
    info_html = "\n              ".join(info)
    sections.append(f'''    <section id="visit" class="section">
      <div class="wrap">
        <div class="sec-head reveal"><h2 class="disp h2">Visit <em class="serif">us</em></h2><span class="eyebrow">Find us</span></div>
        <div class="visit">
          <div class="info reveal">
            <dl>
              {info_html}
            </dl>
            <div class="cta">{contact_btns}</div>
          </div>
          <div class="map reveal"><iframe title="Map to {e(name)}" src="{maps_embed}" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe></div>
        </div>
      </div>
    </section>''')
    # services get the tinted band; the rest stay on the base colour
    sections_html = "\n\n".join(s.replace("%%ALT%%", " alt" if 'id="services"' in s else "") for s in sections)

    mobile_bar = (f'<nav class="mobile-bar" aria-label="Quick contact"><a class="btn" href="{tel_href}">{ICON_PHONE}Call</a>'
                  f'<a class="btn ghost" target="_blank" rel="noopener" href="{maps_link}">{ICON_PIN}Directions</a></nav>' if phone else
                  f'<nav class="mobile-bar" aria-label="Quick contact"><a class="btn" target="_blank" rel="noopener" href="{maps_link}">{ICON_PIN}Get directions</a></nav>')

    footer_p = (f'<p>Unofficial design preview of {e(name)} &mdash; not the gym&rsquo;s website.</p>' if prospect
                else f'<p>&copy; <span id="year"></span> {e(name)}, {e(city)}</p>')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(title)}</title>
  <meta name="description" content="{e(desc)}">
{robots}  <meta name="theme-color" content="#09090b">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{e(title)}">
  <meta property="og:description" content="{e(desc)}">
  <link rel="icon" href="{favicon}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,500..900&family=Instrument+Serif:ital@0;1&family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/css/style.css">
  <style>:root{{--accent:{accent};--accent-rgb:{ar},{ag},{ab};--on-accent:{on_accent}}}</style>
  <script>document.documentElement.classList.add("js");setTimeout(function(){{if(!window.__gymOk)document.documentElement.classList.add("reveal-all")}},2500)</script>
{ld_block}</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
  <div class="top">
  {preview_bar}
  <header class="site-header">
    <div class="wrap nav{"" if has_menu else " nomenu"}">
      <a class="brand" href="#" aria-label="{e(name)} home"><span class="brand-mark">{e(initials)}</span><span class="brand-name">{e(name)}</span></a>
      {menu_html}
      {nav_cta}
    </div>
  </header>
  </div>

  <main id="main">
    <section class="{hero_cls}">
      {hero_img}
      <div class="{grid_cls}">
        <div>
          <span class="pill"><i></i>{e(loc)}</span>
          <h1 class="disp h1"><span class="sr">{e(name)}: </span>Stronger<br><em class="serif">every</em> day.</h1>
          {lead_html}
          <div class="cta">
            {primary}
            {secondary}
          </div>
        </div>
        {pass_card}
      </div>
    </section>

{sections_html}
  </main>

  <footer>
    <div class="wrap">
      {footer_p}
    </div>
  </footer>
  {mobile_bar}
  <script src="assets/js/main.js"></script>
</body>
</html>
'''


def update_root_readme(g):
    p = ROOT / "README.md"
    lines = p.read_text().split("\n")
    link = f'[sites/{g["slug"]}](sites/{g["slug"]})'
    live = g.get("live_url") or "-"
    live_cell = f"[link]({live})" if live != "-" else "-"
    out, found = [], False
    for ln in lines:
        if ln.startswith("| - | _none yet_"):
            continue
        if f"sites/{g['slug']})" in ln:
            m = re.match(r"\| (\d+) \|", ln)
            ln = f'| {m.group(1) if m else "?"} | {g["name"]} | {link} | {live_cell} | {g.get("status", "Draft")} |'
            found = True
        out.append(ln)
    if not found:
        nums = [int(m.group(1)) for ln in out if (m := re.match(r"\| (\d+) \|", ln))]
        row = f'| {max(nums, default=0) + 1} | {g["name"]} | {link} | {live_cell} | {g.get("status", "Draft")} |'
        idx = max((i for i, ln in enumerate(out) if re.match(r"\| \d+ \|", ln)), default=None)
        if idx is None:
            idx = next(i for i, ln in enumerate(out) if ln.startswith("|---"))
        out.insert(idx + 1, row)
    p.write_text("\n".join(out))


def build(slug):
    d = ROOT / "sites" / slug
    cfg = d / "gym.json"
    if not cfg.exists():
        sys.exit(f"missing {cfg}")
    g = json.loads(cfg.read_text())
    g["slug"] = slug
    for sub in ("css", "js", "images"):
        (d / "assets" / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy(TPL / "style.css", d / "assets" / "css" / "style.css")
    shutil.copy(TPL / "main.js", d / "assets" / "js" / "main.js")
    (d / "index.html").write_text(render(g))
    (d / "README.md").write_text(
        f'# {g["name"]}\n\n- **Client / Gym:** {g["name"]}\n- **Location:** {g.get("address") or g["area"] + ", " + g["city"]}\n'
        + (f'- **Phone:** {g["phone"]}\n' if g.get("phone") else "")
        + '- **Stack:** HTML / CSS / JS (generated by `tools/generate.py` from `gym.json`)\n'
        f'- **Live URL:** {g.get("live_url", "")}\n- **Status:** {g.get("status", "Draft")}\n')
    update_root_readme(g)
    print("built", slug)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args == ["--all"]:
        args = sorted(p.parent.name for p in (ROOT / "sites").glob("*/gym.json"))
    for s in args:
        build(s)
