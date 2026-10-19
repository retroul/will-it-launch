// Run with: node vote-server/test.mjs   (Node 22.5+, no dependencies)
// Exercises the worker against an in-memory SQLite database shaped like Cloudflare D1.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import worker from "./worker.js";

const sqlite = new DatabaseSync(":memory:");
sqlite.exec(readFileSync(new URL("./schema.sql", import.meta.url), "utf8"));

// Minimal D1 shim: prepare(sql).bind(...).first/all/run
const DB = {
  prepare(sql) {
    const make = (params) => ({
      bind: (...p) => make(p),
      first: async () => sqlite.prepare(sql).get(...params) ?? null,
      all: async () => ({ results: sqlite.prepare(sql).all(...params) }),
      run: async () => sqlite.prepare(sql).run(...params),
    });
    return make([]);
  },
};
const env = { DB, VOTER_SECRET: "test-secret", ADMIN_TOKEN: "admin", ALLOWED_ORIGINS: "https://site.example" };

async function call(method, path, { ip = "1.1.1.1", body, origin = "https://site.example", auth } = {}) {
  const headers = { "CF-Connecting-IP": ip };
  if (origin) headers.Origin = origin;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) headers.Authorization = `Bearer ${auth}`;
  const res = await worker.fetch(new Request(`https://votes.example${path}`, {
    method, headers, body: body === undefined ? undefined : JSON.stringify(body),
  }), env);
  return { status: res.status, body: await res.json().catch(() => null), headers: res.headers };
}

// Create a request: counts as the creator's vote.
let r = await call("POST", "/requests", { body: { name: "  Deep   Rock Galactic " } });
assert.equal(r.status, 200);
assert.deepEqual([r.body.name, r.body.votes, r.body.voted, r.body.existed], ["Deep Rock Galactic", 1, true, false]);
const id = r.body.id;
assert.equal(r.headers.get("Access-Control-Allow-Origin"), "https://site.example");

// Same game, different spelling, same IP: no double vote.
r = await call("POST", "/requests", { body: { name: "deep rock galactic!" } });
assert.deepEqual([r.body.id, r.body.votes, r.body.existed], [id, 1, true]);
r = await call("POST", `/requests/${id}/vote`);
assert.equal(r.body.votes, 1, "one vote per IP");

// Another IP votes.
r = await call("POST", `/requests/${id}/vote`, { ip: "2.2.2.2" });
assert.deepEqual([r.body.votes, r.body.voted], [2, true]);

// The list shows per-viewer vote state and never exposes voters.
r = await call("GET", "/requests", { ip: "3.3.3.3", origin: null });
assert.deepEqual(r.body.requests, [{ id, name: "Deep Rock Galactic", votes: 2, voted: false }]);

// Unvote, and auto-remove a request once nobody wants it.
r = await call("DELETE", `/requests/${id}/vote`, { ip: "2.2.2.2" });
assert.deepEqual([r.body.votes, r.body.voted], [1, false]);
r = await call("DELETE", `/requests/${id}/vote`);
assert.equal(r.body.removed, true);
assert.equal((await call("GET", "/requests")).body.requests.length, 0);

// Validation.
for (const name of ["", "x", "a".repeat(61), "visit https://spam.example", "<b>hi</b>", 42, "!!!"]) {
  r = await call("POST", "/requests", { body: { name } });
  assert.equal(r.status, 400, `rejects ${JSON.stringify(name)}`);
}
assert.equal((await call("POST", "/requests", { body: "not json" })).status, 400);
assert.equal((await call("POST", "/requests/999/vote")).status, 404);
assert.equal((await call("POST", "/requests/abc/vote")).status, 404);

// Daily limit on new requests per IP.
for (let i = 0; i < 5; i++) assert.equal((await call("POST", "/requests", { ip: "9.9.9.9", body: { name: `Game ${i}` } })).status, 200);
assert.equal((await call("POST", "/requests", { ip: "9.9.9.9", body: { name: "Game 6" } })).status, 429);

// Other websites can't vote from a visitor's browser.
assert.equal((await call("POST", "/requests", { origin: "https://evil.example", body: { name: "Spam" } })).status, 403);

// Admin removal needs the token.
const target = (await call("GET", "/requests")).body.requests[0].id;
assert.equal((await call("DELETE", `/requests/${target}`, { origin: null })).status, 401);
assert.equal((await call("DELETE", `/requests/${target}`, { origin: null, auth: "wrong" })).status, 401);
assert.equal((await call("DELETE", `/requests/${target}`, { origin: null, auth: "admin" })).status, 200);
assert.equal((await call("GET", "/requests")).body.requests.length, 4);

// No raw IPs in the database.
const stored = JSON.stringify([...sqlite.prepare("SELECT * FROM votes").all(), ...sqlite.prepare("SELECT * FROM requests").all()]);
assert.ok(!/\d+\.\d+\.\d+\.\d+/.test(stored), "IPs are hashed");

// Bot check (Turnstile) and rate limit, with Cloudflare's verify call and limiter faked.
const realFetch = globalThis.fetch;
globalThis.fetch = async (url, init) => {
  assert.equal(String(url), "https://challenges.cloudflare.com/turnstile/v0/siteverify");
  assert.equal(init.body.get("secret"), "ts-secret");
  return new Response(JSON.stringify({ success: init.body.get("response") === "good-token" }));
};
let used = 0;
const guarded = { ...env, TURNSTILE_SECRET: "ts-secret", WRITE_LIMITER: { limit: async () => ({ success: ++used <= 3 }) } };
const guardedCall = (method, path, body) => worker.fetch(new Request(`https://votes.example${path}`, {
  method, headers: { "CF-Connecting-IP": "7.7.7.7", Origin: "https://site.example", "Content-Type": "application/json" },
  body: body === undefined ? undefined : JSON.stringify(body),
}), guarded).then(async (res) => ({ status: res.status, body: await res.json() }));

assert.equal((await guardedCall("POST", "/requests", { name: "Bot Game" })).status, 403, "no token");
assert.equal((await guardedCall("POST", "/requests", { name: "Bot Game", token: "fake" })).status, 403, "bad token");
r = await guardedCall("POST", "/requests", { name: "Human Game", token: "good-token" });
assert.equal(r.status, 200, "good token");
assert.equal((await guardedCall("POST", `/requests/${r.body.id}/vote`, {})).status, 429, "4th write in a minute is limited");
assert.equal((await guardedCall("GET", "/requests")).status, 200, "reading is never limited");
globalThis.fetch = realFetch;

console.log("vote-server: all checks passed");
