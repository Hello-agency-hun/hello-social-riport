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
      var text = asTemplate(block);
      if (text && text !== block.dataset.original) {
        edits[block.dataset.narrative] = text;
      }
    });

    return { manual: manual, edits: edits, comments: comments };
  }

  // A megjelenített szövegből visszaállítja az eredeti sablont: az értékek
  // szerkeszthetetlen szigetek, amik a hivatkozásukat data-ref-ben hordozzák.
  // Enélkül a mentés a behelyettesített számokat írná vissza sablonként, és a
  // következő build a saját narratíváját utasítaná el.
  function asTemplate(block) {
    var out = "";
    block.childNodes.forEach(function (node) {
      if (node.nodeType === Node.TEXT_NODE) out += node.textContent;
      else if (node.dataset && node.dataset.ref) out += node.dataset.ref;
      else out += node.textContent;
    });
    return out.trim().replace(/\s+/g, " ");
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
    block.dataset.original = asTemplate(block);
    var saved = (stored.edits || {})[block.dataset.narrative];
    if (saved && saved.indexOf("{") === -1) {
      // Régi, sablon nélküli mentés — inkább hagyjuk az eredetit, mint hogy
      // a hivatkozásokat elveszítsük.
      saved = null;
    }
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

  function payload() {
    return JSON.stringify(collect(), null, 2);
  }

  // Letöltés: mindig működik, de a fájl a Letöltések mappába esik, onnan a
  // hónap mappájába kell másolni. Tartaléknak marad.
  var save = document.createElement("button");
  save.className = "pdf-button no-print";
  save.style.right = "190px";
  save.textContent = "Mentés";
  save.onclick = function () {
    var blob = new Blob([payload()], { type: "application/json" });
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "review.json";
    link.click();
  };
  document.body.appendChild(save);

  // Mentés a mappába: a lap egyszer elkéri a `review.json`-t, utána minden
  // további mentés oda megy. Így nincs letöltés-bemásolás oda-vissza — a
  // menedzser csak annyit mond, hogy mentett, és a riport újraépíthető.
  // A böngésző nem enged fájlt írni kérdezés nélkül, ezért kell az első bökés.
  if (window.showSaveFilePicker) {
    var handle = null;
    var direct = document.createElement("button");
    direct.className = "pdf-button no-print";
    direct.style.right = "330px";
    direct.textContent = "Mentés a mappába";

    direct.onclick = function () {
      var chain = handle
        ? Promise.resolve(handle)
        : window.showSaveFilePicker({
            suggestedName: "review.json",
            types: [
              {
                description: "A hónap mappájába, a report_data.json mellé",
                accept: { "application/json": [".json"] },
              },
            ],
          });

      chain
        .then(function (chosen) {
          handle = chosen;
          return chosen.createWritable();
        })
        .then(function (stream) {
          return stream.write(payload()).then(function () {
            return stream.close();
          });
        })
        .then(function () {
          direct.textContent = "Mentve ✓ — szólj Claude-nak";
          setTimeout(function () {
            direct.textContent = "Mentés a mappába";
          }, 4000);
        })
        .catch(function (error) {
          // A megszakított fájlválasztó nem hiba — a menedzser meggondolta magát.
          if (error && error.name === "AbortError") return;
          direct.textContent = "Nem sikerült — használd a Mentés gombot";
        });
    };
    document.body.appendChild(direct);
  }
})();
