# The Design Blog

A live feed of industrial and product design news: new products, materials, styles, and the studios and companies behind them. It refreshes itself every three hours.

## How it works

- `scripts/sources.json` lists the RSS feeds it reads: Core77, Yanko Design, Designboom (design and technology), Dezeen (design and technology), Design Milk and Car Body Design. A source's feeds are backups tried in order, unless it sets `"combine": true`, which reads them all.
- `scripts/fetch_feeds.py` pulls every feed, keeps each story's headline, image, short summary and link, sorts it into Products, Automotive, Materials, Styles & trends and Studios & companies by keyword, and merges it into `data/articles.json`. The first time it reads a feed, it reads up to 8 pages back to fill in recent weeks. Stories older than 60 days drop off. A feed that's down never empties the site, because older stories are kept.
- `.github/workflows/refresh.yml` runs that script every three hours (and on every push to `main`), commits new stories, and publishes the site to GitHub Pages.
- `index.html` and `assets/` are the site itself: plain HTML, CSS and JavaScript, no build step.

Every card links to the original article. The site never republishes full articles.

## One-time setup

1. In the repo, go to **Settings → Pages** and set **Source** to **GitHub Actions**. Do this before merging, or the first publish run fails.
2. Merge this into `main`.
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
