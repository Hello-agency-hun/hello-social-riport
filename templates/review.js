// Szerkesztés és mentés a böngészőben. Lokális fájlba írni nem lehet, letöltést
// indítani viszont igen — a review.json onnan kerül a hónap mappájába.
(function () {
  // A gombfeliratok a riport nyelvén. A sablon szövegei az i18n modulból
  // jönnek, ezek viszont a JavaScriptben élnek — az angol próbafutáson pont
  // ezek maradtak magyarul egy egyébként teljesen angol riporton.
  var LABELS = window.__helloLabels || {};
  var KEY = "hello-report-review";
  var stored = JSON.parse(localStorage.getItem(KEY) || "{}");
  var comments = stored.comments || [];

  // A beírt szám kiolvasása. Régebben `replace(/[^0-9]/g, "")` volt, ami
  // LETÖRÖLTE a mínuszjelet: aki „-87"-et írt be, 87-et kapott, néma
  // előjelváltással. Egy csökkenés növekedésként került volna az ügyfélhez.
  //
  // Amit elfogadunk:
  //   -87        előjeles egész
  //   1 234      ezres tagolással (sima és nem törhető szóköz is)
  //   -25,4%     magyar tizedesvessző és százalékjel
  //   -25.4      angol tizedespont
  function readNumber(raw) {
    var text = String(raw || "")
      .replace(/[\s ]/g, "")
      .replace(/[−–—]/g, "-") // valódi mínuszjel és gondolatjelek
      .replace(",", ".")
      .replace("%", "");
    if (!/^-?\d+(\.\d+)?$/.test(text)) return null;
    var value = parseFloat(text);
    return isNaN(value) ? null : value;
  }
  window.__helloReadNumber = readNumber; // teszthez

  function collect() {
    // Az egyszer már alkalmazott kézi szám a következő renderben valódi
    // összehasonlító kártyává alakul, ezért többé nincs data-manual mezője a
    // DOM-ban. A következő mentési kör mégis a korábbi értékekből induljon:
    // egy puszta szövegjavítás nem törölheti ki az előző havi adatokat.
    var manual = Object.assign({}, stored.manual || {});
    document.querySelectorAll("[data-manual]").forEach(function (field) {
      var value = readNumber(field.querySelector(".manual-input").textContent);
      if (value !== null) manual[field.dataset.manual] = value;
      else delete manual[field.dataset.manual];
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
    button.textContent = LABELS.comment;
    button.onclick = function () {
      var text = prompt(LABELS.comment_prompt);
      if (!text) return;
      comments.push({ page: index + 1, text: text });
      remember();
      button.textContent = LABELS.comment_done;
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
  save.textContent = LABELS.save;
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
    direct.textContent = LABELS.save_to_folder;

    direct.onclick = function () {
      var chain = handle
        ? Promise.resolve(handle)
        : window.showSaveFilePicker({
            suggestedName: "review.json",
            types: [
              {
                description: LABELS.save_picker || "review.json",
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
          direct.textContent = LABELS.saved_tell_claude;
          setTimeout(function () {
            direct.textContent = LABELS.save_to_folder;
          }, 4000);
        })
        .catch(function (error) {
          // A megszakított fájlválasztó nem hiba — a menedzser meggondolta magát.
          if (error && error.name === "AbortError") return;
          direct.textContent = LABELS.save_failed;
        });
    };
    document.body.appendChild(direct);
  }
})();
