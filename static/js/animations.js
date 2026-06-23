/* ==========================================================================
 *  PRESTIGE OUTDOORS SUPPLY — animations.js
 *  Sticky nav · scroll reveal (.in) · stagger cascade · count-up numbers ·
 *  parallax drift · page-fade (+ bfcache pageshow fix). Vanilla, no libs.
 * ========================================================================== */
(function () {
  "use strict";

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var $all = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };

  /* ----------------------------------------------------------- sticky nav */
  function stickyNav() {
    var header = document.getElementById("site-header");
    if (!header) return;
    var onScroll = function () {
      header.classList.toggle("scrolled", window.pageYOffset > 8);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* -------------------------------------------------------- scroll reveal */
  function reveal() {
    var els = $all(".reveal, .reveal-l, .reveal-r, .reveal-scale");
    var staggers = $all(".stagger");
    if (reduce || !("IntersectionObserver" in window)) {
      els.forEach(function (e) { e.classList.add("in"); });
      staggers.forEach(function (s) { s.classList.add("in"); });
      return;
    }
    var io = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        en.target.classList.add("in");
        obs.unobserve(en.target);
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    els.forEach(function (e) { io.observe(e); });

    // Stagger: cascade children with incremental transition-delay.
    var sio = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var kids = Array.prototype.slice.call(en.target.children);
        kids.forEach(function (k, i) { k.style.transitionDelay = (i * 80) + "ms"; });
        en.target.classList.add("in");
        obs.unobserve(en.target);
      });
    }, { threshold: 0.1, rootMargin: "0px 0px -40px 0px" });
    staggers.forEach(function (s) { sio.observe(s); });
  }

  /* ---------------------------------------------------------- count-up */
  function countUp() {
    var nums = $all(".count-num[data-count]");
    if (!nums.length) return;
    if (reduce || !("IntersectionObserver" in window)) {
      nums.forEach(function (n) { n.textContent = (+n.getAttribute("data-count")).toLocaleString("en-US") + (n.getAttribute("data-plus") ? "+" : ""); });
      return;
    }
    var io = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        animate(en.target);
        obs.unobserve(en.target);
      });
    }, { threshold: 0.4 });
    nums.forEach(function (n) { io.observe(n); });

    function animate(el) {
      var target = +el.getAttribute("data-count") || 0;
      var suffix = el.getAttribute("data-plus") ? "+" : "";
      var dur = 1400, start = null;
      function step(ts) {
        if (start === null) start = ts;
        var p = Math.min((ts - start) / dur, 1);
        var eased = 1 - Math.pow(1 - p, 3);      // easeOutCubic
        el.textContent = Math.round(eased * target).toLocaleString("en-US") + suffix;
        if (p < 1) requestAnimationFrame(step);
        else el.textContent = target.toLocaleString("en-US") + suffix;
      }
      requestAnimationFrame(step);
    }
  }

  /* ----------------------------------------------------------- parallax */
  function parallax() {
    var els = $all("[data-parallax]");
    if (reduce || !els.length) return;
    var ticking = false;
    function update() {
      var vh = window.innerHeight;
      els.forEach(function (el) {
        var host = el.parentElement;
        var r = host.getBoundingClientRect();
        if (r.bottom < -100 || r.top > vh + 100) return;        // skip offscreen
        var factor = parseFloat(el.getAttribute("data-parallax")) || 0.12;
        // progress: -1 (below viewport) → +1 (above viewport)
        var progress = (r.top + r.height / 2 - vh / 2) / (vh / 2 + r.height / 2);
        var shift = (-progress * 26 * (factor / 0.15)).toFixed(1);
        el.style.transform = "translateY(" + shift + "px) scale(1.12)";
      });
      ticking = false;
    }
    function onScroll() { if (!ticking) { ticking = true; requestAnimationFrame(update); } }
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    update();
  }

  /* --------------------------------------------------- page-fade nav */
  function pageTransitions() {
    if (reduce) return;
    document.addEventListener("click", function (e) {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      var a = e.target.closest && e.target.closest("a");
      if (!a) return;
      var href = a.getAttribute("href");
      if (!href || href.charAt(0) === "#") return;
      if (a.target && a.target !== "_self") return;
      if (a.hasAttribute("download") || a.hasAttribute("data-no-fade")) return;
      if (/^(mailto:|tel:|javascript:|https?:\/\/wa\.me)/i.test(href)) return;
      var url;
      try { url = new URL(a.href, window.location.href); } catch (err) { return; }
      if (url.origin !== window.location.origin) return;
      if (url.pathname === window.location.pathname && url.search === window.location.search) return;
      e.preventDefault();
      document.body.classList.add("page-leaving");
      setTimeout(function () { window.location.href = a.href; }, 170);
    });
  }

  window.addEventListener("pageshow", function () { document.body.classList.remove("page-leaving"); });
  window.addEventListener("DOMContentLoaded", function () { document.body.classList.remove("page-leaving"); });

  function init() { stickyNav(); reveal(); countUp(); parallax(); pageTransitions(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
