(function () {
  var layout = document.querySelector(".layout");
  var sidebar = document.getElementById("appSidebar");
  var overlay = document.getElementById("sidebarOverlay");
  var toggle = document.getElementById("mobileMenuBtn");

  if (!layout || !sidebar || !toggle) return;

  function setOpen(open) {
    layout.classList.toggle("sidebar-open", open);
    document.body.classList.toggle("nav-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    toggle.setAttribute("aria-label", open ? "Fechar menu" : "Abrir menu");
  }

  function closeNav() {
    setOpen(false);
  }

  toggle.addEventListener("click", function (e) {
    e.preventDefault();
    setOpen(!layout.classList.contains("sidebar-open"));
  });

  if (overlay) {
    overlay.addEventListener("click", closeNav);
  }

  sidebar.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", closeNav);
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeNav();
  });

  window.addEventListener("resize", function () {
    if (window.innerWidth > 900) closeNav();
  });
})();
