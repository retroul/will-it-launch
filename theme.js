// Runs in <head> before the page paints, so a saved theme doesn't flash the other one first.
// Without a saved choice the page follows the system setting.
try {
  const saved = localStorage.getItem("will-it-launch:theme");
  if (saved === "light" || saved === "dark") document.documentElement.dataset.theme = saved;
} catch { /* storage blocked */ }
