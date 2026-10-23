/**
 * SecureShare Messenger - Utility Helpers
 * Formats timestamps, provides safe HTML escaping, and wraps fetch calls.
 */

const Utils = {
  /**
   * Escape HTML to prevent XSS when rendering user content.
   */
  escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  },

  /**
   * Format ISO date strings into user-friendly time representations.
   */
  formatTime(isoString) {
    if (!isoString) return "";
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return "";
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  },

  formatDateTime(isoString) {
    if (!isoString) return "";
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return "";
    return date.toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  },

  /**
   * Copy text to user clipboard with UI feedback.
   */
  async copyToClipboard(text, successMessage = "Copied to clipboard!") {
    try {
      await navigator.clipboard.writeText(text);
      Utils.showToast(successMessage, "success");
      return true;
    } catch (err) {
      console.error("Clipboard copy failed:", err);
      Utils.showToast("Failed to copy to clipboard", "error");
      return false;
    }
  },

  /**
   * Display floating toast notification.
   */
  showToast(message, type = "info") {
    let container = document.getElementById("toastContainer");
    if (!container) {
      container = document.createElement("div");
      container.id = "toastContainer";
      container.style.position = "fixed";
      container.style.bottom = "20px";
      container.style.right = "20px";
      container.style.zIndex = "9999";
      container.style.display = "flex";
      container.style.flexDirection = "column";
      container.style.gap = "8px";
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `alert-box alert-${type === "error" ? "error" : "success"}`;
    toast.style.margin = "0";
    toast.style.boxShadow = "var(--shadow-lg)";
    toast.style.minWidth = "240px";
    toast.style.animation = "fadeIn 0.2s ease-out";
    toast.textContent = message;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  },

  /**
   * Standard JSON API fetch wrapper.
   */
  async apiFetch(url, options = {}) {
    const defaultHeaders = {
      "Content-Type": "application/json",
      "Accept": "application/json",
    };
    options.headers = { ...defaultHeaders, ...options.headers };

    try {
      const response = await fetch(url, options);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || `HTTP error ${response.status}`);
      }
      return data;
    } catch (error) {
      console.error(`API Fetch Error [${url}]:`, error);
      throw error;
    }
  },

  /**
   * Universal Cross-Browser Password Visibility Toggle.
   * Works consistently in Chrome, Edge, Firefox, Safari.
   */
  initPasswordToggles() {
    const passwordInputs = document.querySelectorAll('input[type="password"], input[data-password-input="true"]');
    passwordInputs.forEach(input => {
      input.setAttribute("data-password-input", "true");

      let wrapper = input.closest(".password-input-wrapper");
      if (!wrapper) {
        wrapper = document.createElement("div");
        wrapper.className = "password-input-wrapper";
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);
      }

      let btn = wrapper.querySelector(".password-toggle-btn");
      if (!btn) {
        btn = document.createElement("button");
        btn.type = "button";
        btn.className = "password-toggle-btn";
        btn.setAttribute("tabindex", "-1");
        btn.setAttribute("aria-label", "Show password");
        btn.setAttribute("title", "Show password");
        btn.innerHTML = `
          <svg class="eye-icon eye-show" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
          <svg class="eye-icon eye-hide" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: none;">
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
            <line x1="1" y1="1" x2="23" y2="23"></line>
          </svg>
        `;
        wrapper.appendChild(btn);
      }

      if (btn.dataset.initialized) return;
      btn.dataset.initialized = "true";

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();

        const isCurrentlyPassword = input.type === "password";
        input.type = isCurrentlyPassword ? "text" : "password";

        const eyeShow = btn.querySelector(".eye-show");
        const eyeHide = btn.querySelector(".eye-hide");
        if (eyeShow && eyeHide) {
          eyeShow.style.display = isCurrentlyPassword ? "none" : "block";
          eyeHide.style.display = isCurrentlyPassword ? "block" : "none";
        }

        const label = isCurrentlyPassword ? "Hide password" : "Show password";
        btn.setAttribute("aria-label", label);
        btn.setAttribute("title", label);

        input.focus();
        try {
          const valLen = input.value.length;
          input.setSelectionRange(valLen, valLen);
        } catch (_) {}
      });
    });
  }
};

// Auto-initialize password toggles on load
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => Utils.initPasswordToggles());
} else {
  Utils.initPasswordToggles();
}

window.Utils = Utils;
