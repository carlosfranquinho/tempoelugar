// Mobile menu toggle
(function () {
  const toggle = document.querySelector(".menu-toggle");
  const nav = document.querySelector(".primary-nav");

  if (!toggle || !nav) return;

  toggle.addEventListener("click", function () {
    const isOpen = nav.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", isOpen);
  });

  // Close menu on outside click
  document.addEventListener("click", function (e) {
    if (!nav.contains(e.target) && !toggle.contains(e.target)) {
      nav.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
    }
  });

  // Close menu on Escape
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      nav.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
    }
  });
})();
