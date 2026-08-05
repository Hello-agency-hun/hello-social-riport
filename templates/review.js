// Szerkesztés és mentés a böngészőben. Lokális fájlba írni nem lehet, letöltést
// indítani viszont igen — a review.json onnan kerül a hónap mappájába.
(function () {
  var KEY = "hello-report-review";
  var stored = JSON.parse(localStorage.getItem(KEY) || "{}");
  var comments = stored.comments || [];

  function collect() {
    var manual = {};
    document.querySelectorAll("[data-manual]").forEach(function (field) {
      var raw = field.querySelector(".manual-input").textContent;
      var value = parseInt(raw.replace(/[^0-9]/g, ""), 10);
      if (!isNaN(value)) manual[field.dataset.manual] = value;
    });

    var edits = {};
    document.querySelectorAll("[data-narrative]").forEach(function (block) {
      var text = block.textContent.trim();
      if (text && text !== block.dataset.original) {
        edits[block.dataset.narrative] = text;
      }
    });

    return { manual: manual, edits: edits, comments: comments };
  }

  function remember() {
    localStorage.setItem(KEY, JSON.stringify(collect()));
  }

  document.querySelectorAll("[data-manual]").forEach(function (field) {
    var input = field.querySelector(".manual-input");
    var saved = (stored.manual || {})[field.dataset.manual];
    if (saved) input.textContent = saved;
    input.addEventListener("input", remember);
  });

  document.querySelectorAll("[data-narrative]").forEach(function (block) {
    block.dataset.original = block.textContent.trim();
    var saved = (stored.edits || {})[block.dataset.narrative];
    if (saved) block.textContent = saved;
    block.setAttribute("contenteditable", "true");
    block.classList.add("editable");
    block.addEventListener("input", remember);
  });

  document.querySelectorAll(".page").forEach(function (page, index) {
    var button = document.createElement("button");
    button.className = "comment-button no-print";
    button.textContent = "megjegyzés";
    button.onclick = function () {
      var text = prompt("Megjegyzés ehhez az oldalhoz:");
      if (!text) return;
      comments.push({ page: index + 1, text: text });
      remember();
      button.textContent = "megjegyzés ✓";
    };
    page.appendChild(button);
  });

  var save = document.createElement("button");
  save.className = "pdf-button no-print";
  save.style.right = "190px";
  save.textContent = "Mentés";
  save.onclick = function () {
    var blob = new Blob([JSON.stringify(collect(), null, 2)], {
      type: "application/json",
    });
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "review.json";
    link.click();
  };
  document.body.appendChild(save);
})();
