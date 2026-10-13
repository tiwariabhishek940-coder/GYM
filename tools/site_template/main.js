(function () {
  window.__gymOk = true;
  var y = document.getElementById("year");
  if (y) y.textContent = new Date().getFullYear();

  var header = document.querySelector(".site-header");
  function onScroll() { header && header.classList.toggle("scrolled", window.scrollY > 8); }
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  var btn = document.querySelector(".menu-btn");
  var links = document.getElementById("nav-links");
  if (btn && links) {
    btn.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
    links.addEventListener("click", function (e) {
      if (e.target.tagName === "A") { links.classList.remove("open"); btn.setAttribute("aria-expanded", "false"); }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && links.classList.contains("open")) {
        links.classList.remove("open"); btn.setAttribute("aria-expanded", "false"); btn.focus();
      }
    });
    document.addEventListener("click", function (e) {
      if (links.classList.contains("open") && !links.contains(e.target) && !btn.contains(e.target)) {
        links.classList.remove("open"); btn.setAttribute("aria-expanded", "false");
      }
    });
  }

  var items = document.querySelectorAll(".reveal");
  if (!("IntersectionObserver" in window)) { items.forEach(function (el) { el.classList.add("in"); }); return; }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) { if (en.isIntersecting) {
        var t = en.target; t.classList.add("in"); io.unobserve(t);
        setTimeout(function () { t.style.transitionDelay = ""; }, 1100);
      } });
  }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
  items.forEach(function (el, i) { el.style.transitionDelay = (i % 4) * 70 + "ms"; io.observe(el); });
})();
