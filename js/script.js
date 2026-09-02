document.addEventListener("DOMContentLoaded", function () {
  var langToggle = document.querySelector(".lang-switch");
  if (langToggle) {
    var applyLang = function (lang) {
      document.documentElement.setAttribute("data-lang", lang);
      document.documentElement.setAttribute("lang", lang === "zh" ? "zh-Hant" : "en");
      try { localStorage.setItem("siteLang", lang); } catch (e) {}
    };
    applyLang(document.documentElement.getAttribute("data-lang") || "en");
    langToggle.addEventListener("click", function () {
      var current = document.documentElement.getAttribute("data-lang") || "en";
      applyLang(current === "en" ? "zh" : "en");
    });
  }

  var toggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector(".site-nav");
  if (!toggle || !nav) return;

  toggle.addEventListener("click", function () {
    var isOpen = nav.classList.toggle("open");
    toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
  });

  nav.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", function () {
      nav.classList.remove("open");
      toggle.setAttribute("aria-expanded", "false");
    });
  });

  var here = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".site-nav a, .page-tabs a").forEach(function (link) {
    var href = link.getAttribute("href");
    if (href === here || (here === "" && href === "index.html")) {
      link.classList.add("active");
    }
  });

  var activeTab = document.querySelector(".page-tabs a.active");
  if (activeTab) {
    activeTab.scrollIntoView({ inline: "center", block: "nearest" });
  }
});
