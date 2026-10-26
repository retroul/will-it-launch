// Will It Launch? vote server (Cloudflare Worker + D1).
//
//   GET    /requests             list requests with vote counts (and whether you voted)
//   POST   /requests {name}      request a game (also votes for it)
//   POST   /requests/:id/vote    vote
//   DELETE /requests/:id/vote    remove your vote
//   DELETE /requests/:id         remove a request (needs "Authorization: Bearer <ADMIN_TOKEN>")
//
// Abuse protection: writes need a Cloudflare Turnstile token (when TURNSTILE_SECRET is set) and are
// rate limited per voter (when the WRITE_LIMITER binding exists).
//
// Privacy: the raw IP is never stored. Each voter is an HMAC of their IP with a
// secret (VOTER_SECRET), so votes can be limited to one per IP without keeping
// anything that identifies a person.

const MAX_LIST = 100;
const MAX_NEW_PER_DAY = 5;
const MAX_BODY = 4096;
const DAY = 86400;

export default {
  async fetch(request, env) {
    const cors = corsHeaders(request, env);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    try {
      // Stop other websites from making their visitors vote. (Scripts without an
      // Origin header are still limited to one vote per IP.)
      if (request.method !== "GET" && request.headers.get("Origin") && !cors["Access-Control-Allow-Origin"]) {
        return json({ error: "This site is not allowed to vote." }, 403, cors);
      }
      return await route(request, env, cors);
    } catch (err) {
      if (err instanceof HttpError) return json({ error: err.message }, err.status, cors);
      console.error(err);
      return json({ error: "Something went wrong. Try again in a minute." }, 500, cors);
    }
  },
};

async function route(request, env, cors) {
  if (!env.VOTER_SECRET) throw new Error("VOTER_SECRET is not set");
  const url = new URL(request.url);
  const parts = url.pathname.replace(/\/+$/, "").split("/").filter(Boolean);
  if (parts[0] !== "requests") throw new HttpError(404, "Not found.");

  const voter = await voterId(request, env.VOTER_SECRET);
  // Rate limit before reading the body, so floods cost as little as possible.
  if (request.method !== "GET" && env.WRITE_LIMITER && !(await env.WRITE_LIMITER.limit({ key: voter })).success) {
    throw new HttpError(429, "Too many votes in a short time. Wait a minute and try again.");
  }
  const body = request.method === "POST" ? await readBody(request) : {};
  if (request.method === "POST") await checkHuman(env, request, body.token);
  const id = parts[1] === undefined ? null : Number(parts[1]);
  if (parts[1] !== undefined && !Number.isInteger(id)) throw new HttpError(404, "Not found.");

  if (parts.length === 1 && request.method === "GET") return json({ requests: await list(env.DB, voter) }, 200, cors);
  if (parts.length === 1 && request.method === "POST") return json(await create(env.DB, voter, cleanName(body.name)), 200, cors);
  if (parts.length === 3 && parts[2] === "vote" && request.method === "POST") return json(await vote(env.DB, voter, id), 200, cors);
  if (parts.length === 3 && parts[2] === "vote" && request.method === "DELETE") return json(await unvote(env.DB, voter, id), 200, cors);
  if (parts.length === 2 && request.method === "DELETE") return json(await remove(env, request, id), 200, cors);
  throw new HttpError(405, "Method not allowed.");
}

// ---- handlers ---------------------------------------------------------------

async function list(db, voter) {
  const { results } = await db.prepare(
    `SELECT r.id, r.name, COUNT(v.voter) AS votes, COALESCE(MAX(v.voter = ?), 0) AS voted
       FROM requests r LEFT JOIN votes v ON v.request_id = r.id
      GROUP BY r.id
      ORDER BY votes DESC, r.created_at ASC
      LIMIT ?`).bind(voter, MAX_LIST).all();
  return results.map((r) => ({ id: r.id, name: r.name, votes: Number(r.votes), voted: Boolean(r.voted) }));
}

async function create(db, voter, name) {
  const slug = slugify(name);
  const existing = await db.prepare("SELECT id FROM requests WHERE slug = ?").bind(slug).first();
  if (existing) return { ...(await vote(db, voter, existing.id)), existed: true };

  const now = nowSeconds();
  const recent = await db.prepare("SELECT COUNT(*) AS n FROM requests WHERE created_by = ? AND created_at > ?")
    .bind(voter, now - DAY).first();
  if (Number(recent.n) >= MAX_NEW_PER_DAY) {
    throw new HttpError(429, `You can request up to ${MAX_NEW_PER_DAY} games a day. Vote for existing ones in the meantime.`);
  }
  const inserted = await db.prepare("INSERT INTO requests (name, slug, created_by, created_at) VALUES (?, ?, ?, ?) RETURNING id")
    .bind(name, slug, voter, now).first();
  return { ...(await vote(db, voter, inserted.id)), existed: false };
}

async function vote(db, voter, id) {
  await requireRequest(db, id);
  await db.prepare("INSERT OR IGNORE INTO votes (request_id, voter, created_at) VALUES (?, ?, ?)")
    .bind(id, voter, nowSeconds()).run();
  return state(db, voter, id);
}

async function unvote(db, voter, id) {
  await requireRequest(db, id);
  await db.prepare("DELETE FROM votes WHERE request_id = ? AND voter = ?").bind(id, voter).run();
  const result = await state(db, voter, id);
  if (result.votes === 0) {
    // Nobody wants it any more: drop the request so the list stays tidy.
    // Only if still empty: someone may have voted in the meantime.
    const { meta } = await db.prepare("DELETE FROM requests WHERE id = ? AND NOT EXISTS (SELECT 1 FROM votes WHERE request_id = ?)")
      .bind(id, id).run();
    if (meta?.changes) return { ...result, removed: true };
    return state(db, voter, id);
  }
  return result;
}

async function remove(env, request, id) {
  const token = (request.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
  if (!env.ADMIN_TOKEN || !(await sameSecret(token, env.ADMIN_TOKEN))) throw new HttpError(401, "Admin token required.");
  await requireRequest(env.DB, id);
  await env.DB.prepare("DELETE FROM votes WHERE request_id = ?").bind(id).run();
  await env.DB.prepare("DELETE FROM requests WHERE id = ?").bind(id).run();
  return { id, removed: true };
}

async function state(db, voter, id) {
  const row = await db.prepare(
    `SELECT r.id, r.name, COUNT(v.voter) AS votes, COALESCE(MAX(v.voter = ?), 0) AS voted
       FROM requests r LEFT JOIN votes v ON v.request_id = r.id
      WHERE r.id = ? GROUP BY r.id`).bind(voter, id).first();
  return { id: row.id, name: row.name, votes: Number(row.votes), voted: Boolean(row.voted) };
}

async function requireRequest(db, id) {
  const row = await db.prepare("SELECT id FROM requests WHERE id = ?").bind(id).first();
  if (!row) throw new HttpError(404, "That request no longer exists.");
}

// ---- input ------------------------------------------------------------------

async function readBody(request) {
  // Real requests are a game name plus a bot-check token: well under 4 KB.
  if (Number(request.headers.get("Content-Length")) > MAX_BODY) throw new HttpError(413, "That request is too big.");
  const text = await request.text();
  if (text.length > MAX_BODY) throw new HttpError(413, "That request is too big.");
  if (!text) return {};
  try {
    const body = JSON.parse(text);
    if (body && typeof body === "object" && !Array.isArray(body)) return body;
  } catch { /* fall through */ }
  throw new HttpError(400, "Send JSON like {\"name\": \"Game name\"}.");
}

async function checkHuman(env, request, token) {
  if (!env.TURNSTILE_SECRET) return;
  if (typeof token !== "string" || !token || token.length > 2048) throw new HttpError(403, "Please complete the check that you're not a bot.");
  const form = new FormData();
  form.append("secret", env.TURNSTILE_SECRET);
  form.append("response", token);
  const ip = request.headers.get("CF-Connecting-IP");
  if (ip) form.append("remoteip", ip);
  let result;
  try {
    const res = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", { method: "POST", body: form });
    result = await res.json();
  } catch {
    throw new HttpError(503, "Couldn't check that you're not a bot. Try again in a minute.");
  }
  if (!result.success) throw new HttpError(403, "The bot check failed. Reload the page and try again.");
}

export function cleanName(raw) {
  if (typeof raw !== "string") throw new HttpError(400, "Type the name of a game.");
  const name = raw.normalize("NFKC").replace(/[\u0000-\u001f\u007f-\u009f]/g, "").replace(/\s+/g, " ").trim();
  if (name.length < 2) throw new HttpError(400, "That name is too short.");
  if (name.length > 60) throw new HttpError(400, "Keep the name under 60 characters.");
  if (/https?:|www\.|[<>]/i.test(name)) throw new HttpError(400, "Just the game's name, please. No links.");
  if (!slugify(name)) throw new HttpError(400, "Type the name of a game.");
  return name;
}

export function slugify(name) {
  return name.normalize("NFKC").toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "");
}

// ---- helpers ----------------------------------------------------------------

class HttpError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

function nowSeconds() { return Math.floor(Date.now() / 1000); }

async function voterId(request, secret) {
  const ip = voterNetwork(request.headers.get("CF-Connecting-IP") || "unknown");
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(ip)));
  return btoa(String.fromCharCode(...sig.slice(0, 16))).replace(/[+/=]/g, (c) => ({ "+": "-", "/": "_", "=": "" }[c]));
}

// One IPv6 connection usually owns a whole /64 (billions of addresses), so count the /64 as one voter.
// IPv4 addresses are used as they are.
export function voterNetwork(ip) {
  if (ip.includes(".")) return ip.slice(ip.lastIndexOf(":") + 1); // IPv4, or IPv4 written as IPv6 (::ffff:1.2.3.4)
  if (!ip.includes(":")) return ip;
  const [head, tail = ""] = ip.toLowerCase().split("::");
  const left = head ? head.split(":") : [];
  const right = tail ? tail.split(":") : [];
  const full = ip.includes("::") ? [...left, ...Array(8 - left.length - right.length).fill("0"), ...right] : left;
  return full.slice(0, 4).map((h) => h.padStart(4, "0")).join(":") + "::/64";
}

async function sameSecret(a, b) {
  // Compare digests so the check takes the same time whatever the input.
  const enc = new TextEncoder();
  const [x, y] = await Promise.all([a, b].map((s) => crypto.subtle.digest("SHA-256", enc.encode(s))));
  const ux = new Uint8Array(x), uy = new Uint8Array(y);
  let diff = 0;
  for (let i = 0; i < ux.length; i++) diff |= ux[i] ^ uy[i];
  return diff === 0;
}

function corsHeaders(request, env) {
  const origin = request.headers.get("Origin") || "";
  const allowed = (env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean);
  const headers = {
    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
  if (allowed.includes("*")) headers["Access-Control-Allow-Origin"] = "*";
  else if (allowed.includes(origin)) headers["Access-Control-Allow-Origin"] = origin;
  return headers;
}

function json(body, status, headers) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...headers, "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}
