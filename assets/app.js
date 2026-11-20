(() => {
  "use strict";

  const PAGE = 24;
  const SAVED_KEY = "tdb-saved";
  const els = {
    lead: document.getElementById("lead"),
    grid: document.getElementById("grid"),
    empty: document.getElementById("empty"),
    more: document.getElementById("more"),
    tabs: document.getElementById("tabs"),
    source: document.getElementById("source"),
    search: document.getElementById("search"),
    freshness: document.getElementById("freshness"),
    status: document.getElementById("source-status"),
  };

  const state = { articles: [], cat: "all", source: "", q: "", shown: PAGE };

  const store = {
    get() {
      try { return new Set(JSON.parse(localStorage.getItem(SAVED_KEY) || "[]")); }
      catch { return new Set(); }
    },
    set(set) {
      try { localStorage.setItem(SAVED_KEY, JSON.stringify([...set])); } catch { /* private mode */ }
    },
  };
  let saved = store.get();

  document.getElementById("today").textContent = new Date().toLocaleDateString(undefined, {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });

  function ago(iso) {
    const mins = Math.max(0, Math.round((Date.now() - new Date(iso)) / 60000));
    if (mins < 60) return `${mins || 1}m ago`;
    const hrs = Math.round(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.round(hrs / 24);
    if (days < 7) return `${days}d ago`;
    return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });
  }

  const LABELS = { products: "Product", materials: "Material", styles: "Style", companies: "Studio" };

  function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null) continue;
      if (k === "text") node.textContent = v;
      else node.setAttribute(k, v);
    }
    for (const child of [].concat(children)) if (child) node.append(child);
    return node;
  }

  function thumb(a) {
    const box = el("div", { class: "thumb" });
    const ph = el("span", { class: "ph", "aria-hidden": "true", text: a.source.charAt(0) });
    box.append(ph);
    if (a.image) {
      const img = el("img", { src: a.image, alt: "", loading: "lazy", decoding: "async", referrerpolicy: "no-referrer" });
      img.addEventListener("load", () => ph.remove());
      img.addEventListener("error", () => img.remove());
      box.append(img);
    }
    return box;
  }

  function saveButton(a) {
    const on = saved.has(a.id);
    const btn = el("button", {
      class: "save", type: "button", "aria-pressed": String(on),
      "aria-label": on ? "Remove from saved" : "Save for later",
    });
    const paint = on ? 'fill="currentColor"' : 'fill="none" stroke="currentColor" stroke-width="2"';
    btn.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true"><path ${paint} d="M6 3h12a1 1 0 0 1 1 1v17l-7-4.5L5 21V4a1 1 0 0 1 1-1z"/></svg>`;
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      saved.has(a.id) ? saved.delete(a.id) : saved.add(a.id);
      store.set(saved);
      render(false);
    });
    return btn;
  }

  function story(a, variant) {
    const tag = a.categories.find((c) => LABELS[c]);
    const heading = el(variant === "main" ? "h2" : "h3", { text: a.title });
    const meta = el("div", { class: "meta" }, [
      el("span", { class: "src", text: a.source }),
      tag ? el("span", { text: LABELS[tag] }) : null,
      el("time", { datetime: a.published, text: ago(a.published) }),
    ]);
    const card = el("a", { class: "story", href: a.link, target: "_blank", rel: "noopener noreferrer" }, [
      thumb(a),
      el("div", {}, [meta, heading, a.summary ? el("p", { class: "summary", text: a.summary }) : null]),
    ]);
    card.prepend(saveButton(a));
    return card;
  }

  function filtered() {
    const q = state.q.trim().toLowerCase();
    return state.articles.filter((a) => {
      if (state.cat === "saved" && !saved.has(a.id)) return false;
      if (state.cat !== "all" && state.cat !== "saved" && !a.categories.includes(state.cat)) return false;
      if (state.source && a.source !== state.source) return false;
      if (q && !`${a.title} ${a.summary} ${a.source}`.toLowerCase().includes(q)) return false;
      return true;
    });
  }

  function render(resetPaging = true) {
    if (resetPaging) state.shown = PAGE;
    const list = filtered();
    els.lead.replaceChildren();
    els.grid.replaceChildren();

    // Lead block only on the unfiltered front page, using stories that have images.
    let rest = list;
    if (state.cat === "all" && !state.source && !state.q) {
      const withImg = list.filter((a) => a.image);
      const leadItems = withImg.slice(0, 4);
      if (leadItems.length === 4) {
        const ids = new Set(leadItems.map((a) => a.id));
        const main = el("div", { class: "lead-main" }, [story(leadItems[0], "main")]);
        const side = el("div", { class: "lead-side" }, leadItems.slice(1).map((a) => story(a, "side")));
        els.lead.append(main, side);
        rest = list.filter((a) => !ids.has(a.id));
      }
    }

    rest.slice(0, state.shown).forEach((a) => els.grid.append(story(a)));
    els.more.hidden = rest.length <= state.shown;

    els.empty.hidden = list.length > 0;
    if (!list.length) {
      els.empty.textContent = !state.articles.length
        ? "The first refresh hasn't run yet. Stories appear within a few hours of setup."
        : state.cat === "saved"
          ? "Nothing saved yet. Use the bookmark on any story to keep it here."
          : "No stories match that filter.";
    }
  }

  function setTab(cat) {
    state.cat = cat;
    for (const b of els.tabs.querySelectorAll("button")) {
      b.setAttribute("aria-selected", String(b.dataset.cat === cat));
    }
    history.replaceState(null, "", cat === "all" ? location.pathname : `#${cat}`);
    render();
  }

  els.tabs.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-cat]");
    if (btn) setTab(btn.dataset.cat);
  });
  els.source.addEventListener("change", () => { state.source = els.source.value; render(); });
  let t;
  els.search.addEventListener("input", () => {
    clearTimeout(t);
    t = setTimeout(() => { state.q = els.search.value; render(); }, 150);
  });
  els.more.addEventListener("click", () => { state.shown += PAGE; render(false); });

  fetch(`data/articles.json?v=${Date.now()}`)
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((data) => {
      state.articles = data.articles || [];
      els.freshness.textContent = data.updated ? `Updated ${ago(data.updated)}` : "Waiting for first refresh";
      const names = [...new Set(state.articles.map((a) => a.source))].sort();
      for (const n of names) els.source.append(el("option", { value: n, text: n }));
      const sources = data.sources || [];
      if (sources.length) {
        const ok = sources.filter((s) => s.ok).map((s) => s.name);
        const down = sources.filter((s) => !s.ok).map((s) => s.name);
        els.status.textContent = `Sources: ${ok.join(", ")}.` + (down.length ? ` Not responding on the last refresh: ${down.join(", ")}.` : "");
      }
      const hash = location.hash.slice(1);
      if (hash && els.tabs.querySelector(`[data-cat="${hash}"]`)) setTab(hash); else render();
    })
    .catch(() => {
      els.freshness.textContent = "Couldn't load stories";
      els.empty.hidden = false;
      els.empty.textContent = "Couldn't load the story list. Try refreshing the page.";
    });
})();
