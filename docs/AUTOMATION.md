# Gym site pipeline

1. **Discover**: search a city area (e.g. "best gyms in Arera Colony Bhopal"), record results in
   `tools/prospects/<city>.json`. Data comes from aggregator listings and is unverified.
2. **Describe**: for one gym, create `sites/<slug>/gym.json` (see `sites/s3-fitness/gym.json`).
   Leave unknown fields out (no phone => no call buttons; no images => text-only hero).
3. **Generate**: `python3 tools/generate.py <slug>` writes `index.html`, assets, README and the
   root README row.
4. **Review**: open `sites/<slug>/index.html` in a browser.
5. **Publish only with the owner's OK.** Do not publish a site under a gym's name, or with
   photos taken from Google/Instagram, before the owner agrees. Use owner-supplied photos.
