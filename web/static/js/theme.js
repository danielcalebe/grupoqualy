/**
 * Gerenciador de Tema Claro / Escuro — Grupo Qualy
 * Sincroniza data-theme + data-bs-theme (Bootstrap 5.3) + gráficos Chart.js.
 */
(function () {
  const STORAGE_KEY = "qualy-theme";

  const ICON_MOON =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>';

  const ICON_SUN =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<circle cx="12" cy="12" r="5"></circle>' +
    '<line x1="12" y1="1" x2="12" y2="3"></line>' +
    '<line x1="12" y1="21" x2="12" y2="23"></line>' +
    '<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>' +
    '<line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>' +
    '<line x1="1" y1="12" x2="3" y2="12"></line>' +
    '<line x1="21" y1="12" x2="23" y2="12"></line>' +
    '<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>' +
    '<line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>';

  function getCurrentTheme() {
    return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  function applyTheme(theme, persist) {
    const normalized = theme === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", normalized);
    document.documentElement.setAttribute("data-bs-theme", normalized);
    if (persist) {
      try {
        localStorage.setItem(STORAGE_KEY, normalized);
      } catch (_) {}
    }
    syncButtons(normalized);
    window.dispatchEvent(new CustomEvent("qualy:themechange", { detail: { theme: normalized } }));
  }

  function syncButtons(theme) {
    document.querySelectorAll("[data-qualy-theme-toggle]").forEach(function (btn) {
      const isDark = theme === "dark";
      btn.setAttribute("aria-pressed", String(isDark));
      btn.setAttribute("title", isDark ? "Ativar modo claro" : "Ativar modo escuro");
      const iconSlot = btn.querySelector("[data-theme-icon]");
      const labelSlot = btn.querySelector("[data-theme-label]");
      if (iconSlot) iconSlot.innerHTML = isDark ? ICON_SUN : ICON_MOON;
      if (labelSlot) labelSlot.textContent = isDark ? "Modo Claro" : "Modo Escuro";
    });
  }

  window.QualyTheme = {
    get: getCurrentTheme,
    set: function (theme) {
      applyTheme(theme, true);
    },
    toggle: function () {
      applyTheme(getCurrentTheme() === "dark" ? "light" : "dark", true);
    },
  };

  document.addEventListener("DOMContentLoaded", function () {
    syncButtons(getCurrentTheme());
    document.querySelectorAll("[data-qualy-theme-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        window.QualyTheme.toggle();
      });
    });
  });
})();
