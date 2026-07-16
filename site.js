/* =============================================================================
   PETER LOHMANN - WEBSITE SHARED SCRIPT
   Handles: (1) scroll reveal animations, (2) the mobile menu button.
   No dependencies, no build step. Loaded by every page.
   ========================================================================== */
(function () {
  "use strict";

  /* ---- 1. Mobile menu toggle ---- */
  var toggle = document.querySelector(".nav-toggle");
  var links = document.querySelector("nav.top .links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  /* ---- 2. Scroll reveal ---- */
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var targets = document.querySelectorAll(".reveal, .stagger");
  if (reduce || !("IntersectionObserver" in window)) {
    targets.forEach(function (el) { el.classList.add("in"); });
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        e.target.classList.add("in");
        io.unobserve(e.target);
      }
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.06 });
  targets.forEach(function (el) { io.observe(el); });
})();
