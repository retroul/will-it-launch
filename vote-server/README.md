# Vote server (optional)

Lets visitors request games and vote on the Requests page, with no account needed.
It runs on Cloudflare Workers + D1. The free plan is plenty for a hobby site.

Without it, the Requests page links to GitHub issues instead: people request a game with a form and vote with 👍.

## How votes stay private

- The server never stores IP addresses. Each voter is an HMAC (a keyed hash) of their IP plus your secret `VOTER_SECRET`. The same IP always gives the same code, so it can vote once per game, but the code can't be turned back into an IP.
- Nobody can see who voted. The list only returns vote counts, and whether *you* voted.
- New requests are capped at 5 per IP per day. Links and HTML in names are rejected.
- A request is removed automatically once its last vote is taken back.

Limits: people sharing one internet connection (a household, school or office) share one vote. Someone switching VPNs can vote again. That's the trade-off for not needing accounts.

## Set it up (about 10 minutes)

You need [Node.js](https://nodejs.org) and a free [Cloudflare account](https://dash.cloudflare.com/sign-up).

```sh
cd vote-server
npx wrangler login
npx wrangler d1 create will-it-launch-votes
```

1. Copy the `database_id` it prints into `wrangler.toml`.
2. In `wrangler.toml`, set `ALLOWED_ORIGINS` to your site's address, e.g. `https://your-name.github.io`.
3. Create the tables, set the two secrets (paste any long random text, e.g. from `openssl rand -hex 32`) and deploy:

```sh
npx wrangler d1 execute will-it-launch-votes --remote --file=schema.sql
npx wrangler secret put VOTER_SECRET
npx wrangler secret put ADMIN_TOKEN
npx wrangler deploy
```

4. `deploy` prints an address like `https://will-it-launch-votes.your-name.workers.dev`. Put it in `config.js` as `voteApi` and push.

## Removing spam

Find the request's `id` in the list, then:

```sh
curl https://YOUR-WORKER.workers.dev/requests
curl -X DELETE -H "Authorization: Bearer YOUR_ADMIN_TOKEN" https://YOUR-WORKER.workers.dev/requests/ID
```

## Tests

```sh
node vote-server/test.mjs
```

Runs the worker against an in-memory SQLite database (Node 22.5 or newer, no installs needed).
