/**
 * SecureShare Messenger - Theme Management Script
 * Persists theme preference (light/dark) in localStorage and applies data-theme attribute.
 */

(function () {
  const THEME_KEY = "secureshare_theme";

  function getPreferredTheme() {
    const savedTheme = localStorage.getItem(THEME_KEY);
    if (savedTheme) {
      return savedTheme;
    }
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);

    // Update toggle icons if present in DOM
    const themeIcon = document.getElementById("themeIcon");
    if (themeIcon) {
      themeIcon.textContent = theme === "dark" ? "☀️" : "🌙";
    }
    const themeLabel = document.getElementById("themeLabel");
    if (themeLabel) {
      themeLabel.textContent = theme === "dark" ? "Light Mode" : "Dark Mode";
    }
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    const next = current === "dark" ? "light" : "dark";
    applyTheme(next);
  }

  // Initialize immediately to prevent flash of wrong theme
  const initialTheme = getPreferredTheme();
  applyTheme(initialTheme);

  // Expose toggle globally
  window.toggleTheme = toggleTheme;
  window.applyTheme = applyTheme;

  document.addEventListener("DOMContentLoaded", function () {
    const toggleBtn = document.getElementById("themeToggleBtn");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", toggleTheme);
    }
    applyTheme(getPreferredTheme());
  });
})();
