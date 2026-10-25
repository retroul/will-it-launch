# Security

Found a security problem? Please report it privately: open the **Security** tab of this repository and choose **Report a vulnerability**. Don't open a public issue.

## What the site does with your data

- The site is static. It has no accounts, no cookies, no analytics and no tracking.
- It remembers your chosen platform and theme in your own browser (`localStorage`). That never leaves your device.
- Fonts are served from this site, not from Google. A Content Security Policy only lets the page load its own files (cover images included), and the vote server and Cloudflare bot check on the Requests page.
- The Requests page loads Cloudflare Turnstile, a bot check, from challenges.cloudflare.com. Nothing from Cloudflare loads on the other pages.
- If the optional vote server is enabled, it stores a keyed hash of your IP address per vote, never the address itself. See [vote-server/README.md](vote-server/README.md).
