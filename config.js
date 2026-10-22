// Site settings. All of them are optional.
window.AC_CONFIG = {
  // Your GitHub repository, used for "Request a game" and "Report a problem" links.
  // Leave empty on GitHub Pages: it is worked out from the address (name.github.io/repo).
  repo: "https://github.com/retroul/will-it-launch",

  // Address of your vote server (see vote-server/README.md), e.g.
  // "https://will-it-launch-votes.your-name.workers.dev".
  // Leave empty and the Requests page uses GitHub issues instead.
  // If it is not on *.workers.dev, also add its address to connect-src in index.html.
  voteApi: "https://will-it-launch-votes.will-it-launch.workers.dev",

  // Public site key of the Cloudflare Turnstile bot check used for requests and votes.
  // Leave empty to turn the check off (then also remove TURNSTILE_SECRET from the vote server).
  turnstileSiteKey: "0x4AAAAAAFcBO-GDsEgQ74y_",
};
