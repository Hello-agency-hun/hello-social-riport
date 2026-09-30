(function () {
  "use strict";
  var fields = Array.from(document.querySelectorAll('[data-post-manual]'));
  var hu = document.documentElement.lang !== 'en';
  function read(field) {
    var raw = field.textContent.trim().replace(/[\s\u00a0\u202f]/g, '');
    if (!raw) { field.removeAttribute('aria-invalid'); return null; }
    var money = field.dataset.postKind === 'money';
    // Grouped counts: 1 234 / 1.234 / 1,234. Money also accepts decimal comma.
    if (/^\d{1,3}(?:[.,]\d{3})+$/.test(raw)) raw = raw.replace(/[.,]/g, '');
    else if (money && /^\d{1,3}(?:,\d{3})+\.\d{1,2}$/.test(raw)) raw = raw.replace(/,/g, '');
    else if (money && /^\d{1,3}(?:\.\d{3})+,\d{1,2}$/.test(raw)) raw = raw.replace(/\./g, '').replace(',', '.');
    else if (money) raw = raw.replace(',', '.');
    var valid = money ? /^\d+(?:\.\d{1,2})?$/.test(raw) : /^\d+$/.test(raw);
    var value = Number(raw);
    if (!valid || !Number.isFinite(value) || value > 1e12) {
      field.setAttribute('aria-invalid', 'true');
      throw new Error(hu ? 'A posztadat legyen nem negatív egész; költésnél legfeljebb két tizedest adj meg. A hiányzó adatot hagyd üresen.' : 'Use a non-negative whole number; spend allows two decimals. Leave unknown data blank.');
    }
    field.removeAttribute('aria-invalid');
    return value;
  }
  function collect(base) {
    var manual = Object.assign({}, base || {});
    document.querySelectorAll('[data-post-key]:not([data-post-manual])').forEach(function (field) { delete manual[field.dataset.postKey]; });
    fields.forEach(function (field) {
      var value = read(field), key = field.dataset.postManual;
      if (value === null) delete manual[key]; else manual[key] = value;
    });
    fields.forEach(function (field) {
      if (!field.dataset.postField.startsWith('organic.')) return;
      var allKey = field.dataset.postManual.replace('_organic_', '_all_');
      var all = document.querySelector('[data-post-key="' + allKey + '"]');
      var total = all && (all.hasAttribute('data-post-manual') ? manual[allKey] : (all.dataset.postValue === '' ? null : Number(all.dataset.postValue)));
      var organic = manual[field.dataset.postManual];
      if (organic != null && total != null && organic > total) {
        field.setAttribute('aria-invalid', 'true');
        throw new Error(hu ? 'Az organikus adat nem lehet több az összesnél. Ellenőrizd a posztot és a mérési időszakot.' : 'Organic cannot exceed All. Check the post and reporting period.');
      }
    });
    return manual;
  }
  fields.forEach(function (field) {
    field.addEventListener('keydown', function (event) { if (event.key === 'Enter') { event.preventDefault(); field.blur(); } });
    field.addEventListener('paste', function (event) {
      event.preventDefault();
      var value = event.clipboardData.getData('text/plain').trim();
      field.textContent = value;
      field.dispatchEvent(new Event('input', {bubbles: true}));
    });
    field.addEventListener('input', function () { try { read(field); } catch (error) { field.title = error.message; } });
  });
  window.__helloPostMetrics = {
    collect: collect,
    listen: function (callback) { fields.forEach(function (field) { field.addEventListener('input', callback); }); },
    saved: function (manual) {
      fields.forEach(function (field) {
        var value = manual[field.dataset.postManual];
        field.dataset.postValue = value == null ? '' : String(value);
        field.dataset.postSource = value == null ? 'missing' : 'manual';
        field.textContent = value == null ? '' : value.toLocaleString(hu ? 'hu-HU' : 'en-US', { minimumFractionDigits: field.dataset.postKind === 'money' ? 2 : 0, maximumFractionDigits: field.dataset.postKind === 'money' ? 2 : 0 });
      });
    }
  };
})();
