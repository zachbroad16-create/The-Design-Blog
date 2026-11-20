# The Design Blog

A live feed of industrial and product design news: new products, materials, styles, and the studios and companies behind them. It refreshes itself every three hours.

## How it works

- `scripts/sources.json` lists the RSS feeds it reads (Core77, Yanko Design, Designboom, Dezeen, Design Milk, SolidSmack, MaterialDistrict, Design Week). Each source can list backup feed URLs, tried in order.
- `scripts/fetch_feeds.py` pulls every feed, keeps each story's headline, image, short summary and link, sorts it into Products, Materials, Styles & trends and Studios & companies by keyword, and merges it into `data/articles.json`. Stories older than 45 days drop off. A feed that's down never empties the site, because older stories are kept.
- `.github/workflows/refresh.yml` runs that script every three hours (and on every push to `main`), commits new stories, and publishes the site to GitHub Pages.
- `index.html` and `assets/` are the site itself: plain HTML, CSS and JavaScript, no build step.

Every card links to the original article. The site never republishes full articles.

## One-time setup

1. Merge this into `main`.
2. In the repo, go to **Settings → Pages** and set **Source** to **GitHub Actions**.
3. Go to **Actions → Refresh and deploy → Run workflow** to do the first refresh now instead of waiting up to three hours.

The site then lives at `https://<your-username>.github.io/<repo-name>/`.

GitHub Pages on a private repo needs a paid GitHub plan. On a free plan, the repo has to be public.

## Changing things

- **Add or remove a source:** edit `scripts/sources.json`.
- **Change how stories are sorted:** edit the `CATEGORIES` keyword lists in `scripts/fetch_feeds.py`. A trailing `*` matches any ending, so `recycl*` matches recycled and recycling.
- **Change how often it refreshes:** edit the `cron` line in `.github/workflows/refresh.yml`.

## Test locally

```
pip install -r requirements.txt
python tests/test_fetch.py      # parser test against a saved sample feed
python scripts/fetch_feeds.py   # pull the real feeds
python -m http.server            # then open http://localhost:8000
```
