(function () {
  const form = document.getElementById("feed-post-form");
  if (!form) return;

  const previewEl = document.getElementById("feed-attachments-preview");
  if (!previewEl) return;

  const inputs = [
    { el: form.querySelector("#feed-input-imagens"), kind: "image" },
    { el: form.querySelector("#feed-input-videos"), kind: "video" },
    { el: form.querySelector("#feed-input-arquivos"), kind: "file" },
  ].filter((x) => x.el);

  function isImage(file) {
    return file.type.startsWith("image/");
  }

  function iconFor(file, kind) {
    if (kind === "video" || file.type.startsWith("video/")) return "🎥";
    if (isImage(file)) return "🖼";
    return "📎";
  }

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function removeFileAt(input, index) {
    const dt = new DataTransfer();
    Array.from(input.files).forEach((f, i) => {
      if (i !== index) dt.items.add(f);
    });
    input.files = dt.files;
    render();
  }

  function render() {
    previewEl.innerHTML = "";
    let hasAny = false;

    inputs.forEach(({ el, kind }) => {
      Array.from(el.files || []).forEach((file, index) => {
        hasAny = true;
        const item = document.createElement("div");
        item.className = "feed-attachment-item";

        if (isImage(file)) {
          const img = document.createElement("img");
          img.className = "feed-attachment-thumb";
          img.alt = file.name;
          const reader = new FileReader();
          reader.onload = function () {
            img.src = reader.result;
          };
          reader.readAsDataURL(file);
          item.appendChild(img);
        } else {
          const box = document.createElement("div");
          box.className = "feed-attachment-file";
          box.textContent = iconFor(file, kind) + " " + file.name;
          item.appendChild(box);
        }

        const meta = document.createElement("span");
        meta.className = "feed-attachment-meta";
        meta.textContent = formatSize(file.size);
        item.appendChild(meta);

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "feed-attachment-remove";
        btn.setAttribute("aria-label", "Remove " + file.name);
        btn.textContent = "×";
        btn.addEventListener("click", function () {
          removeFileAt(el, index);
        });
        item.appendChild(btn);

        previewEl.appendChild(item);
      });
    });

    previewEl.hidden = !hasAny;
  }

  inputs.forEach(function ({ el }) {
    el.addEventListener("change", render);
  });
})();
