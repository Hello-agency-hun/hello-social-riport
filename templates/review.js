// Szerkesztés és mentés a böngészőben. Lokális fájlba írni nem lehet, letöltést
// indítani viszont igen — a review.json onnan kerül a hónap mappájába.
(function () {
  // A gombfeliratok a riport nyelvén. A sablon szövegei az i18n modulból
  // jönnek, ezek viszont a JavaScriptben élnek — az angol próbafutáson pont
  // ezek maradtak magyarul egy egyébként teljesen angol riporton.
  var LABELS = window.__helloLabels || {};

  // Ez az egy riport. A böngésző tárhelye eredetenként (origin) közös: ha
  // minden riport ugyanarról a szerverről nyílik meg, egy közös kulcs mellett
  // az egyik ügyfél kézi adatai és megjegyzései a másik ügyfél review.json-jába
  // kerültek. A kulcs ezért riportonként más.
  var REPORT = window.__helloReport || {};
  var KEY = "hello-report-review:" + (REPORT.key || location.pathname);
  var REVISION = REPORT.revision || "";
  // A riportba már beépített kézi számok. Ezek helyén már kész kártya áll,
  // beviteli mező nélkül — a következő review.json innen viszi tovább őket.
  var APPLIED = REPORT.manual || {};
  var REFERENCE = /\{[a-z_]+(?:\.[a-z_]+)*(?:\|[a-z]+)?\}/g;

  // A tárhely lehet letiltva (privát ablak, szigorú böngésző-beállítás). Ilyenkor
  // a szerkesztés és a letöltés továbbra is működjön — csak az újratöltés
  // utáni visszaállítás marad el. Korábban egy dobott kivétel az egész
  // szerkesztőt leállította, gombok nélkül.
  function load() {
    try {
      return JSON.parse(localStorage.getItem(KEY) || "{}");
    } catch (error) {
      return {};
    }
  }

  var stored = load();
  // Egy már feldolgozott kör megjegyzései nem kerülhetnek vissza a következő
  // review.json-ba: az újrarenderelt riport új revíziót kap.
  var comments = stored.revision === REVISION ? stored.comments || [] : [];

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
      .replace(/[\s ]/g, "")
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
    //
    // A forrásuk maga a riport (APPLIED), nem csak a böngésző tárhelye: egy
    // másik böngészőből vagy a webes eszközből mentve a tárhely üres, és a
    // review.json üres `manual`-lal ment ki. A beépített érték erősebb a
    // tárhelyben ragadt régebbinél; a lapon most beírt mindkettőnél.
    var manual = Object.assign({}, stored.manual || {}, APPLIED);
    document.querySelectorAll("[data-manual]").forEach(function (field) {
      var value = readNumber(field.querySelector(".manual-input").textContent);
      if (value !== null) manual[field.dataset.manual] = value;
      else delete manual[field.dataset.manual];
    });

    var edits = {};
    var bases = {};
    document.querySelectorAll("[data-narrative]").forEach(function (block) {
      var text = asTemplate(block);
      if (text && text !== block.dataset.original) {
        edits[block.dataset.narrative] = text;
        bases[block.dataset.narrative] = block.dataset.original;
      }
    });

    return { manual: manual, edits: edits, comments: comments, bases: bases };
  }

  // A megjelenített szövegből visszaállítja az eredeti sablont: az értékek
  // szerkeszthetetlen szigetek, amik a hivatkozásukat data-ref-ben hordozzák.
  // Enélkül a mentés a behelyettesített számokat írná vissza sablonként, és a
  // következő build a saját narratíváját utasítaná el.
  function asTemplate(block) {
    // A contenteditable az Entert hol `<br>`-ként, hol új `<div>`-ként adja
    // vissza, a beágyazott elemek szövegét pedig a `textContent` sortörés
    // nélkül fűzné össze. Ezért rekurzívan járjuk be, és mindkét alakból
    // valódi sortörés lesz.
    function serialise(node) {
      if (node.nodeType === Node.TEXT_NODE) return node.textContent;
      if (node.dataset && node.dataset.ref) return node.dataset.ref;
      if (node.nodeName === "BR") return "\n";
      var inner = "";
      node.childNodes.forEach(function (child) {
        inner += serialise(child);
      });
      return /^(DIV|P|LI)$/.test(node.nodeName) ? "\n" + inner : inner;
    }

    var out = "";
    block.childNodes.forEach(function (node) {
      out += serialise(node);
    });
    // Csak a vízszintes térköz olvad össze. A sortörés adat, nem formázás:
    // korábban a \s+ minta ezt is elmosta, és a mentés után a
    // menedzser tördelése nyomtalanul eltűnt.
    return out
      .replace(/[ \t ]+/g, " ")
      .replace(/[ \t]*\n[ \t]*/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  // Egy korábbi, még el nem mentett javítás visszaállítása újratöltés után.
  // Korábban a javítás a tárhelyben maradt, de a lapon nem jelent meg újra —
  // és a következő mentés már nélküle ment ki: a munka csendben elveszett.
  // A számszigeteket az eredeti blokkból klónozzuk, tehát hivatkozás nem vész
  // el és nem keletkezik; ha a mentett szöveg ismeretlen hivatkozást vagy
  // leírt számot tartalmaz, az eredeti marad.
  function restore(block, template) {
    var islands = {};
    block.querySelectorAll("[data-ref]").forEach(function (span) {
      islands[span.dataset.ref] = span;
    });
    if (/\d/.test(template.replace(REFERENCE, ""))) return false;

    var fragment = document.createDocumentFragment();
    function addText(text) {
      text.split("\n").forEach(function (line, index) {
        if (index) fragment.appendChild(document.createElement("br"));
        if (line) fragment.appendChild(document.createTextNode(line));
      });
    }

    var last = 0;
    var match;
    REFERENCE.lastIndex = 0;
    while ((match = REFERENCE.exec(template))) {
      var island = islands[match[0]];
      if (!island) return false;
      addText(template.slice(last, match.index));
      fragment.appendChild(island.cloneNode(true));
      last = REFERENCE.lastIndex;
    }
    addText(template.slice(last));
    block.textContent = "";
    block.appendChild(fragment);
    return true;
  }

  // A mentés gombjai jelzik, ha van még ki nem mentett változás.
  var saveButtons = [];
  function markDirty(dirty) {
    saveButtons.forEach(function (button) {
      button.classList.toggle("is-dirty", dirty);
    });
  }

  function remember() {
    var state = collect();
    state.revision = REVISION;
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
    } catch (error) {
      // Tárhely nélkül is lehet dolgozni — csak újratöltés után nem marad meg.
    }
    markDirty(true);
  }

  document.querySelectorAll("[data-manual]").forEach(function (field) {
    var input = field.querySelector(".manual-input");
    var saved = (stored.manual || {})[field.dataset.manual];
    // A nulla is érték: a korábbi `if (saved)` a beírt nullát elhagyta.
    if (saved !== undefined && saved !== null) input.textContent = saved;
    input.addEventListener("input", remember);
  });

  document.querySelectorAll("[data-narrative]").forEach(function (block) {
    block.dataset.original = asTemplate(block);
    var path = block.dataset.narrative;
    var saved = (stored.edits || {})[path];
    // Csak akkor állítjuk vissza, ha a javítás ugyanarra a szövegre készült,
    // ami most a lapon áll. Ha közben a riport újra elkészült (a javítás már
    // bekerült, vagy az agent továbbírta), a régi javítás felülírná az újat.
    if (saved && (stored.bases || {})[path] === block.dataset.original) {
      restore(block, saved);
    }
    block.setAttribute("contenteditable", "true");
    block.classList.add("editable");
    block.addEventListener("input", remember);
  });

  document.querySelectorAll(".page").forEach(function (page, index) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "comment-button no-print";
    var mine = comments.filter(function (comment) {
      return comment.page === index + 1;
    });
    button.textContent = mine.length ? LABELS.comment_done : LABELS.comment;
    button.title = mine.map(function (comment) {
      return comment.text;
    }).join("\n");
    button.onclick = function () {
      var text = prompt(LABELS.comment_prompt);
      if (!text) return;
      comments.push({ page: index + 1, text: text });
      remember();
      button.textContent = LABELS.comment_done;
      button.title = (button.title ? button.title + "\n" : "") + text;
    };
    page.appendChild(button);
  });

  function payload() {
    var state = collect();
    // A `bases` csak a böngésző saját könyvelése — a review.json formátuma
    // nem változik.
    return JSON.stringify(
      { manual: state.manual, edits: state.edits, comments: state.comments },
      null,
      2
    );
  }
  // Beágyazó felületnek (pl. a webes eszköznek): a mentendő tartalom, a
  // böngésző tárhelyének olvasása nélkül.
  window.__helloReviewPayload = payload;

  // Az eszköztár a sablonból jön; a gombok egy sorba kerülnek, nem fix
  // pixel-eltolással egymásra.
  var toolbar = document.querySelector(".toolbar") || document.body;
  function addButton(label) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "pdf-button toolbar-button no-print";
    button.textContent = label;
    toolbar.appendChild(button);
    saveButtons.push(button);
    return button;
  }

  // Letöltés: mindig működik, de a fájl a Letöltések mappába esik, onnan a
  // hónap mappájába kell másolni. Tartaléknak marad.
  var save = addButton(LABELS.save);
  save.onclick = function () {
    var blob = new Blob([payload()], { type: "application/json" });
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "review.json";
    link.click();
    markDirty(false);
  };

  // Mentés a mappába: a lap egyszer elkéri a `review.json`-t, utána minden
  // további mentés oda megy. Így nincs letöltés-bemásolás oda-vissza — a
  // menedzser csak annyit mond, hogy mentett, és a riport újraépíthető.
  // A böngésző nem enged fájlt írni kérdezés nélkül, ezért kell az első bökés.
  if (window.showSaveFilePicker) {
    var handle = null;
    var direct = addButton(LABELS.save_to_folder);

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
          markDirty(false);
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
  }

  // Ha az előző munkamenetből maradt nem mentett változás, az látszódjon.
  if (Object.keys(collect().edits).length || comments.length) markDirty(true);
})();
