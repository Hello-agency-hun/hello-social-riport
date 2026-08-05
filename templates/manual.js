// A kézi mezők mentése. A böngésző lokális fájlba nem tud írni, letöltést
// viszont tud indítani — a manual.json onnan kerül a hónap mappájába.
(function () {
  var KEY = "hello-report-manual";
  var fields = document.querySelectorAll("[data-manual]");
  if (!fields.length) return;

  var stored = JSON.parse(localStorage.getItem(KEY) || "{}");

  function read() {
    var out = {};
    fields.forEach(function (field) {
      var raw = field.querySelector(".manual-input").textContent;
      var value = parseInt(raw.replace(/[^0-9]/g, ""), 10);
      if (!isNaN(value)) out[field.dataset.manual] = value;
    });
    return out;
  }

  fields.forEach(function (field) {
    var input = field.querySelector(".manual-input");
    if (stored[field.dataset.manual]) {
      input.textContent = stored[field.dataset.manual];
    }
    input.addEventListener("input", function () {
      localStorage.setItem(KEY, JSON.stringify(read()));
    });
  });

  var button = document.createElement("button");
  button.className = "pdf-button no-print";
  button.style.right = "190px";
  button.textContent = "Kézi adatok mentése";
  button.onclick = function () {
    var blob = new Blob([JSON.stringify(read(), null, 2)], {
      type: "application/json",
    });
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "manual.json";
    link.click();
  };
  document.body.appendChild(button);
})();
