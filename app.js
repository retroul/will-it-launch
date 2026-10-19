(() => {
  "use strict";

  const PLATFORMS = [
    { id: "windows", name: "Windows", short: "Windows", icon: "windows" },
    { id: "macos", name: "Mac", short: "Mac", icon: "apple" },
    { id: "linux", name: "Linux", full: "Linux & Steam Deck", short: "Linux", icon: "linux" },
    { id: "android", name: "Android", short: "Android", icon: "android" },
    { id: "ios", name: "iPhone & iPad", short: "iOS", icon: "phone" },
  ];

  // Order is the "works best → worst" ranking used for sorting.
  const STATUSES = [
    { id: "supported", label: "Works", desc: "Officially supported. There's a native version, or the developer turned on anti-cheat support (for example Proton on Linux and Steam Deck)." },
    { id: "running", label: "Works unofficially", desc: "Playable, but the developer doesn't support it. An update could break it." },
    { id: "planned", label: "Coming soon", desc: "The developer has said support is on the way." },
    { id: "broken", label: "Doesn't work", desc: "Won't run or can't go online right now, usually because the anti-cheat blocks it." },
    { id: "denied", label: "Blocked by devs", desc: "The developer chose to block this platform or refuses to support it." },
    { id: "unavailable", label: "Not released", desc: "There's no version for this platform. Notes may point to a separate mobile game." },
  ];
  const RANK = Object.fromEntries(STATUSES.map((s, i) => [s.id, i]));
  const LABEL = Object.fromEntries(STATUSES.map((s) => [s.id, s.label]));
  const PLAYABLE = new Set(["supported", "running"]);

  const data = window.AC_DATA || { games: [], generated: "" };
  const config = window.AC_CONFIG || {};
  const games = data.games;
  const bySlug = new Map(games.map((g) => [g.slug, g]));
  const $ = (sel) => document.querySelector(sel);

  const store = {
    get(key) { try { return localStorage.getItem("will-it-launch:" + key); } catch { return null; } },
    set(key, value) { try { localStorage.setItem("will-it-launch:" + key, value); } catch { /* storage blocked */ } },
  };

  const savedPlatform = store.get("platform");
  const state = {
    platform: PLATFORMS.some((p) => p.id === savedPlatform) ? savedPlatform : "linux",
    query: "",
    statuses: new Set(),
    genre: "",
    anticheat: "",
    sort: "name",
    open: new Set(),
  };

  // ---- helpers ---------------------------------------------------------------
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "");
  const link = (url, text) => {
    const u = safeUrl(url);
    return u ? `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(text)}</a>` : esc(text);
  };
  const icon = (name) => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
  const platform = (id) => PLATFORMS.find((p) => p.id === id);
  const fullName = (p) => p.full || p.name;
  const statusOf = (g, p = state.platform) => g.platforms[p].status;
  const verdict = (status, p) => (status === "unavailable" ? `Not on ${platform(p).short}` : LABEL[status]);
  const reach = (g) => PLATFORMS.filter((p) => PLAYABLE.has(statusOf(g, p.id))).length;
  const countBy = (list, p) => {
    const c = Object.fromEntries(STATUSES.map((s) => [s.id, 0]));
    list.forEach((g) => c[statusOf(g, p)]++);
    return c;
  };
  const bar = (counts, total) => `<div class="bar" aria-hidden="true">${STATUSES.filter((s) => counts[s.id])
    .map((s) => `<span data-status="${s.id}" style="width:${(counts[s.id] / total) * 100}%"></span>`).join("")}</div>`;
  const key = (counts) => `<div class="key">${STATUSES.filter((s) => counts[s.id])
    .map((s) => `<span data-status="${s.id}">${s.label} ${counts[s.id]}</span>`).join("")}</div>`;

  function hue(text) {
    let h = 0;
    for (const ch of text) h = (h * 31 + ch.codePointAt(0)) % 360;
    return h;
  }
  function cover(g) {
    const words = g.name.replace(/[^\p{L}\p{N} ]/gu, "").split(" ").filter(Boolean);
    const initials = (words.length > 1 ? words.slice(0, 2).map((w) => [...w][0]).join("") : [...(words[0] || "?")].slice(0, 2).join("")).toUpperCase();
    const mono = `<span class="monogram" style="background:linear-gradient(135deg,hsl(${hue(g.name)} 55% 46%),hsl(${(hue(g.name) + 40) % 360} 60% 36%))">${esc(initials)}</span>`;
    if (!g.image) return `<span class="cover">${mono}</span>`;
    // --img paints a blurred copy behind art that isn't wide (logos, square key art).
    return `<span class="cover" style="--img:url(&quot;${esc(g.image)}&quot;)"><img src="${esc(g.image)}" alt="" loading="lazy" decoding="async" data-fallback="${esc(mono)}"></span>`;
  }

  // GitHub repo: config wins, otherwise derive it from a GitHub Pages address.
  const repo = (() => {
    if (config.repo) return config.repo.replace(/\/+$/, "");
    const host = location.hostname;
    if (!host.endsWith(".github.io")) return "";
    const owner = host.split(".")[0];
    const first = location.pathname.split("/").filter(Boolean)[0];
    return `https://github.com/${owner}/${first && !first.includes(".") ? first : host}`;
  })();
  const issueUrl = (template, params) => `${repo}/issues/new?${new URLSearchParams({ template, ...params })}`;

  // ---- static parts ----------------------------------------------------------
  function initStatic() {
    $("#game-count").textContent = games.length;
    $("#built-date").textContent = data.generated || "recently";
    $("#legend-list").innerHTML = STATUSES.map((s) =>
      `<div data-status="${s.id}"><dt><span class="dot"></span>${s.label}</dt><dd>${esc(s.desc)}</dd></div>`).join("");

    const genres = [...new Set(games.map((g) => g.genre))].sort();
    $("#genre").insertAdjacentHTML("beforeend", genres.map((g) => `<option value="${esc(g)}">${esc(g)}</option>`).join(""));
    const acs = [...new Set(games.flatMap((g) => g.anticheats))].sort((a, b) => a.localeCompare(b));
    $("#anticheat").insertAdjacentHTML("beforeend", acs.map((a) => `<option value="${esc(a)}">${esc(a)}</option>`).join(""));

    if (repo) {
      const gh = $("#github-link");
      gh.href = repo;
      gh.hidden = false;
    }
  }

  // ---- hero ------------------------------------------------------------------
  function renderHero() {
    const total = games.length || 1;
    $("#platforms").innerHTML = PLATFORMS.map((p) => {
      const c = countBy(games, p.id);
      const pct = Math.round(((c.supported + c.running) / total) * 100);
      const on = p.id === state.platform;
      return `<button type="button" class="platform" role="radio" aria-checked="${on}" tabindex="${on ? 0 : -1}" data-platform="${p.id}">
        ${icon(p.icon)}<span class="p-name">${p.name}</span><span class="p-score">${pct}% playable</span></button>`;
    }).join("");

    const p = platform(state.platform);
    const c = countBy(games, p.id);
    const works = c.supported + c.running;
    $("#hero-platform").textContent = fullName(p);
    $("#summary").innerHTML = `<p class="summary-text"><strong>${works} of ${games.length}</strong> games work on ${esc(fullName(p))}.</p>${bar(c, total)}${key(c)}`;
    $("#ac-platform").textContent = fullName(p);
  }

  // ---- games -----------------------------------------------------------------
  function matchesBase(g) {
    const q = state.query;
    if (q && !(g.name.toLowerCase().includes(q) || g.genre.toLowerCase().includes(q) || g.anticheats.some((a) => a.toLowerCase().includes(q)))) return false;
    if (state.genre && g.genre !== state.genre) return false;
    if (state.anticheat && !g.anticheats.includes(state.anticheat)) return false;
    return true;
  }
  const isShown = (g) => matchesBase(g) && (!state.statuses.size || state.statuses.has(statusOf(g)));

  const SORTS = {
    name: (a, b) => a.name.localeCompare(b.name),
    best: (a, b) => RANK[statusOf(a)] - RANK[statusOf(b)] || a.name.localeCompare(b.name),
    worst: (a, b) => RANK[statusOf(b)] - RANK[statusOf(a)] || a.name.localeCompare(b.name),
    reach: (a, b) => reach(b) - reach(a) || a.name.localeCompare(b.name),
    updated: (a, b) => (b.updated || "").localeCompare(a.updated || "") || a.name.localeCompare(b.name),
  };

  function renderChips(base) {
    const c = countBy(base, state.platform);
    $("#status-chips").innerHTML = STATUSES.map((s) => {
      const on = state.statuses.has(s.id);
      return `<button type="button" class="chip" data-status="${s.id}" aria-pressed="${on}" ${c[s.id] || on ? "" : "disabled"}>${s.label} <span class="n">${c[s.id]}</span></button>`;
    }).join("");
  }

  function detailHtml(g) {
    const blocks = PLATFORMS.map((p) => {
      const pl = g.platforms[p.id];
      const notes = pl.notes.length ? `<ul>${pl.notes.map((n) => `<li>${link(n.url, n.text)}</li>`).join("")}</ul>` : "";
      return `<div class="dp${p.id === state.platform ? " current" : ""}" data-status="${pl.status}">
        <div class="dp-head">${icon(p.icon)}${p.name}</div>
        <span class="dp-verdict">${verdict(pl.status, p.id)}</span>${notes}</div>`;
    }).join("");

    const links = [
      g.url && link(g.url, "Official site"),
      g.steam && link(`https://store.steampowered.com/app/${encodeURIComponent(g.steam)}`, "Steam"),
      g.steam && link(`https://www.protondb.com/app/${encodeURIComponent(g.steam)}`, "ProtonDB"),
      g.steam && link(`https://steamdb.info/app/${encodeURIComponent(g.steam)}`, "SteamDB"),
    ].filter(Boolean).join("");

    const timeline = g.history.length
      ? `<div><span class="label">Linux timeline</span><ol class="timeline">${g.history.slice().reverse()
          .map((h) => `<li><time>${esc(h.date)}</time>${link(h.url, h.name)}</li>`).join("")}</ol></div>`
      : "";
    const report = repo
      ? `<a class="report" href="${esc(issueUrl("status-report.yml", { title: `[Status] ${g.name}`, game: g.name }))}" target="_blank" rel="noopener">${icon("flag")}Something wrong here? Tell us</a>`
      : "";

    return `<div class="detail" id="detail-${esc(g.slug)}">
      <div class="detail-platforms">${blocks}</div>
      <div class="facts">
        <div><span class="label">Anti-cheat</span><div class="tags">${g.anticheats.map((a) =>
          `<button type="button" class="tag" data-ac="${esc(a)}" title="Show every game using ${esc(a)}">${esc(a)}</button>`).join("") || "None listed"}</div></div>
        <div><span class="label">Genre</span>${esc(g.genre)}</div>
        ${links ? `<div><span class="label">Links</span><div class="links">${links}</div></div>` : ""}
      </div>
      ${timeline}
      ${report}
    </div>`;
  }

  function rowHtml(g) {
    const open = state.open.has(g.slug);
    const badges = PLATFORMS.map((p) => {
      const s = statusOf(g, p.id);
      const tip = `${p.name}: ${verdict(s, p.id)}`;
      return `<span class="badge${p.id === state.platform ? " current" : ""}" data-status="${s}" title="${esc(tip)}">${icon(p.icon)}<span class="sr-only">${esc(tip)}</span></span>`;
    }).join("");
    const s = statusOf(g);
    return `<li class="game${open ? " open" : ""}" id="${esc(g.slug)}">
      <button type="button" class="row" data-slug="${esc(g.slug)}" aria-expanded="${open}" aria-controls="detail-${esc(g.slug)}">
        ${cover(g)}
        <span class="g-text"><span class="g-name">${esc(g.name)}</span><span class="g-meta">${esc(g.genre)} · ${esc(g.anticheats.join(", ") || "No anti-cheat listed")}</span></span>
        <span class="badges">${badges}</span>
        <span class="verdict" data-status="${s}">${verdict(s, state.platform)}</span>
      </button>
      ${open ? detailHtml(g) : ""}
    </li>`;
  }

  function renderGames() {
    const base = games.filter(matchesBase);
    renderChips(base);
    const shown = base.filter(isShown).sort(SORTS[state.sort]);
    $("#game-list").innerHTML = shown.map(rowHtml).join("");
    $("#empty").hidden = shown.length > 0;
    const works = shown.filter((g) => PLAYABLE.has(statusOf(g))).length;
    $("#result-count").textContent = shown.length === games.length
      ? `Showing all ${games.length} games`
      : `Showing ${shown.length} of ${games.length} games (${works} work on ${platform(state.platform).name})`;
  }

  // ---- anti-cheats -----------------------------------------------------------
  function renderAnticheats() {
    const groups = new Map();
    games.forEach((g) => g.anticheats.forEach((a) => groups.set(a, [...(groups.get(a) || []), g])));
    const p = state.platform;
    $("#ac-list").innerHTML = [...groups.entries()]
      .sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]))
      .map(([name, list]) => {
        const c = countBy(list, p);
        const chips = list.slice().sort((a, b) => RANK[statusOf(a, p)] - RANK[statusOf(b, p)] || a.name.localeCompare(b.name))
          .map((g) => `<a class="ac-game" data-status="${statusOf(g, p)}" href="#${esc(g.slug)}" title="${esc(verdict(statusOf(g, p), p))}">${esc(g.name)}</a>`).join("");
        return `<li class="ac-item">
          <div><h3 class="ac-name">${esc(name)}</h3><p class="ac-count">${list.length} game${list.length === 1 ? "" : "s"}</p></div>
          <div class="ac-body">${bar(c, list.length)}${key(c)}<div class="ac-games">${chips}</div></div>
        </li>`;
      }).join("");
  }

  // ---- requests --------------------------------------------------------------
  const votes = {
    api: (config.voteApi || "").replace(/\/+$/, ""),
    items: [],
    loaded: false,
    async call(method, path, body) {
      const res = await fetch(this.api + path, {
        method,
        headers: body ? { "Content-Type": "application/json" } : {},
        body: body ? JSON.stringify(body) : undefined,
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(json.error || "The vote server didn't answer. Try again later.");
      return json;
    },
  };

  function initRequests() {
    if (votes.api) {
      $("#requests-live").hidden = false;
    } else if (repo) {
      $("#requests-github").hidden = false;
      $("#gh-new-request").href = issueUrl("game-request.yml", { title: "[Request] " });
      $("#gh-vote").href = `${repo}/issues?q=${encodeURIComponent('is:issue is:open "[Request]" in:title sort:reactions-+1-desc')}`;
    } else {
      $("#requests-offline").hidden = false;
    }
  }

  async function loadRequests() {
    if (!votes.api || votes.loaded) return;
    votes.loaded = true;
    $("#request-list").innerHTML = `<li class="request-empty">Loading requests…</li>`;
    try {
      votes.items = (await votes.call("GET", "/requests")).requests;
      renderRequests();
    } catch (err) {
      votes.loaded = false;
      $("#request-list").innerHTML = `<li class="request-empty">${esc(err.message)}</li>`;
    }
  }

  function renderRequests() {
    $("#request-list").innerHTML = votes.items.length
      ? votes.items.map((r) => `<li class="request">
          <span class="request-name">${esc(r.name)}</span>
          <button type="button" class="vote" data-id="${r.id}" aria-pressed="${r.voted}" aria-label="${r.voted ? "Remove your vote for" : "Vote for"} ${esc(r.name)}">${icon("up")}${r.votes}</button>
        </li>`).join("")
      : `<li class="request-empty">No requests yet. Be the first!</li>`;
  }

  function upsertRequest(r) {
    const i = votes.items.findIndex((x) => x.id === r.id);
    if (r.removed) { if (i >= 0) votes.items.splice(i, 1); }
    else if (i >= 0) votes.items[i] = r;
    else votes.items.push(r);
    votes.items.sort((a, b) => b.votes - a.votes);
    renderRequests();
  }

  function hint(text, isError = false) {
    const el = $("#request-hint");
    el.innerHTML = text;
    el.classList.toggle("error", isError);
  }

  function trackedMatch(name) {
    const n = name.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "");
    return n.length > 2 ? games.find((g) => g.name.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "") === n) : null;
  }

  // ---- routing (bare #tokens only) -----------------------------------------
  const VIEWS = ["games", "anticheats", "requests"];
  function route() {
    const token = decodeURIComponent(location.hash.slice(1));
    const view = VIEWS.includes(token) ? token : "games";
    VIEWS.forEach((v) => { $(`#${v}-view`).hidden = v !== view; });
    document.querySelectorAll(".nav a").forEach((a) => {
      if (a.dataset.view === view) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
    if (view === "requests") loadRequests();
    if (bySlug.has(token)) openGame(token);
  }

  function openGame(slug) {
    if (!isShown(bySlug.get(slug))) clearFilters(false);
    state.open.add(slug);
    renderGames();
    requestAnimationFrame(() => document.getElementById(slug)?.scrollIntoView({ block: "start" }));
  }

  function clearFilters(rerender = true) {
    Object.assign(state, { query: "", genre: "", anticheat: "" });
    state.statuses.clear();
    $("#search").value = ""; $("#genre").value = ""; $("#anticheat").value = "";
    if (rerender) renderGames();
  }

  // ---- theme -----------------------------------------------------------------
  const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
  const isDark = () => document.documentElement.dataset.theme
    ? document.documentElement.dataset.theme === "dark"
    : darkQuery.matches;
  function syncThemeButton() {
    const dark = isDark();
    const btn = $("#theme-toggle");
    btn.innerHTML = icon(dark ? "sun" : "moon");
    btn.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  }

  // ---- events ----------------------------------------------------------------
  function selectPlatform(id) {
    state.platform = id;
    store.set("platform", id);
    renderHero();
    renderGames();
    renderAnticheats();
    document.querySelector(`.platform[data-platform="${id}"]`)?.focus();
  }

  function bind() {
    $("#platforms").addEventListener("click", (e) => {
      const b = e.target.closest(".platform");
      if (b) selectPlatform(b.dataset.platform);
    });
    $("#platforms").addEventListener("keydown", (e) => {
      const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
      if (!step) return;
      e.preventDefault();
      const i = PLATFORMS.findIndex((p) => p.id === state.platform);
      selectPlatform(PLATFORMS[(i + step + PLATFORMS.length) % PLATFORMS.length].id);
    });

    let timer;
    $("#search").addEventListener("input", (e) => {
      clearTimeout(timer);
      timer = setTimeout(() => { state.query = e.target.value.trim().toLowerCase(); renderGames(); }, 120);
    });
    $("#genre").addEventListener("change", (e) => { state.genre = e.target.value; renderGames(); });
    $("#anticheat").addEventListener("change", (e) => { state.anticheat = e.target.value; renderGames(); });
    $("#sort").addEventListener("change", (e) => { state.sort = e.target.value; renderGames(); });
    $("#clear-filters").addEventListener("click", () => clearFilters());
    $("#status-chips").addEventListener("click", (e) => {
      const chip = e.target.closest(".chip");
      if (!chip) return;
      const s = chip.dataset.status;
      state.statuses.has(s) ? state.statuses.delete(s) : state.statuses.add(s);
      renderGames();
    });

    const list = $("#game-list");
    list.addEventListener("click", (e) => {
      const tag = e.target.closest(".tag");
      if (tag) {
        state.anticheat = tag.dataset.ac;
        $("#anticheat").value = state.anticheat;
        renderGames();
        $(".toolbar").scrollIntoView({ block: "start" });
        return;
      }
      const row = e.target.closest(".row");
      if (!row) return;
      const slug = row.dataset.slug;
      state.open.has(slug) ? state.open.delete(slug) : state.open.add(slug);
      renderGames();
      document.querySelector(`.row[data-slug="${CSS.escape(slug)}"]`)?.focus({ preventScroll: true });
    });
    // Covers that fail to load (no Steam art, blocked images) fall back to a monogram.
    list.addEventListener("error", (e) => {
      const img = e.target;
      if (img.tagName === "IMG" && img.dataset.fallback) img.outerHTML = img.dataset.fallback;
    }, true);

    $("#request-name").addEventListener("input", (e) => {
      const g = trackedMatch(e.target.value);
      hint(g ? `We already track <a href="#${esc(g.slug)}">${esc(g.name)}</a>.` : "");
    });
    $("#request-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const input = $("#request-name");
      const name = input.value.trim();
      if (name.length < 2) return hint("Type the name of a game first.", true);
      const tracked = trackedMatch(name);
      if (tracked) return hint(`We already track <a href="#${esc(tracked.slug)}">${esc(tracked.name)}</a>.`);
      const btn = e.target.querySelector("button");
      btn.disabled = true;
      try {
        const r = await votes.call("POST", "/requests", { name });
        upsertRequest(r);
        input.value = "";
        hint(r.existed ? `${esc(r.name)} was already requested, so we counted your vote.` : `Thanks! ${esc(r.name)} is on the list.`);
      } catch (err) {
        hint(esc(err.message), true);
      } finally {
        btn.disabled = false;
      }
    });
    $("#request-list").addEventListener("click", async (e) => {
      const btn = e.target.closest(".vote");
      if (!btn) return;
      const id = Number(btn.dataset.id);
      const voted = btn.getAttribute("aria-pressed") === "true";
      btn.disabled = true;
      try {
        upsertRequest(await votes.call(voted ? "DELETE" : "POST", `/requests/${id}/vote`));
        hint("");
      } catch (err) {
        hint(esc(err.message), true);
        btn.disabled = false;
      }
    });

    $("#theme-toggle").addEventListener("click", () => {
      const next = isDark() ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      store.set("theme", next);
      syncThemeButton();
    });
    darkQuery.addEventListener?.("change", syncThemeButton);
    window.addEventListener("hashchange", route);
  }

  // Apply a saved theme only if the visitor picked one; otherwise follow the system.
  const savedTheme = store.get("theme");
  if (savedTheme === "light" || savedTheme === "dark") document.documentElement.dataset.theme = savedTheme;

  initStatic();
  initRequests();
  bind();
  syncThemeButton();
  renderHero();
  renderGames();
  renderAnticheats();
  route();
})();
