(function () {
  if (!("serviceWorker" in navigator)) return;

  window.addEventListener("load", function () {
    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .catch(function (err) {
        console.warn("PWA: service worker registration failed", err);
      });
  });

  var deferredPrompt = null;
  var installBtn = document.getElementById("pwaInstallBtn");

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
    if (installBtn) {
      installBtn.hidden = false;
    }
  });

  if (installBtn) {
    installBtn.addEventListener("click", function () {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function () {
        deferredPrompt = null;
        installBtn.hidden = true;
      });
    });
  }

  window.addEventListener("appinstalled", function () {
    deferredPrompt = null;
    if (installBtn) installBtn.hidden = true;
  });
})();
