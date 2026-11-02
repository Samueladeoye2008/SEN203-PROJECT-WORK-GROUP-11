// Global UI: theme, show/hide panels, copy code, search and "my tasks" filter.
(function () {
  function $(s) { return document.querySelector(s); }

  function toggleTheme() {
    var dark = document.documentElement.classList.toggle("dark");
    try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch (e) { /* storage blocked */ }
  }
  ["#theme-toggle", "#theme-toggle-m"].forEach(function (id) {
    var b = $(id); if (b) { b.addEventListener("click", toggleTheme); }
  });

  document.addEventListener("click", function (e) {
    var t = e.target.closest && e.target.closest("[data-toggle]");
    if (t) {
      var el = $(t.dataset.toggle);
      if (el) {
        e.preventDefault();
        el.classList.toggle("hidden");
        if (!el.classList.contains("hidden")) {
          var f = el.querySelector("input:not([type=hidden]),select,textarea"); if (f) { f.focus(); }
        }
      }
      return;
    }
    var c = e.target.closest && e.target.closest("[data-copy]");
    if (c && navigator.clipboard) {
      var old = c.textContent;
      navigator.clipboard.writeText(c.dataset.copy).then(function () {
        c.textContent = "Copied"; setTimeout(function () { c.textContent = old; }, 1500);
      });
    }
  });

  var search = $("#search"), mine = $("#mine-toggle"), mineOn = false;
  function applyFilters() {
    var q = search ? search.value.trim().toLowerCase() : "";
    document.querySelectorAll("[data-search]").forEach(function (el) {
      var hide = q !== "" && el.dataset.search.indexOf(q) === -1;
      if (el.classList.contains("task") && mineOn && mine && el.dataset.assignee !== mine.dataset.me) { hide = true; }
      el.classList.toggle("hidden", hide);
    });
  }
  if (search) { search.addEventListener("input", applyFilters); }
  if (mine) {
    mine.addEventListener("click", function () {
      mineOn = !mineOn; mine.setAttribute("aria-pressed", mineOn ? "true" : "false"); applyFilters();
    });
  }
})();
