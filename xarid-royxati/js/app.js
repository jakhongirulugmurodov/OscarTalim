(function () {
  "use strict";

  var STORAGE_KEY = "xarid-royxati-items";
  var items = loadItems();
  var currentPeriod = "today";

  var form = document.getElementById("item-form");
  var dateInput = document.getElementById("date");
  var nameInput = document.getElementById("name");
  var nameSuggestions = document.getElementById("name-suggestions");
  var periodTabs = document.getElementById("period-tabs");
  var itemsBody = document.getElementById("items-body");
  var itemsEmpty = document.getElementById("items-empty");
  var topProductsBody = document.getElementById("top-products-body");
  var topProductsEmpty = document.getElementById("top-products-empty");
  var categoryChart = document.getElementById("category-chart");
  var exportBtn = document.getElementById("export-btn");
  var importInput = document.getElementById("import-input");
  var clearBtn = document.getElementById("clear-btn");

  dateInput.value = todayStr();

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var name = nameInput.value.trim();
    var category = document.getElementById("category").value.trim();
    var quantity = parseFloat(document.getElementById("quantity").value);
    var unit = document.getElementById("unit").value.trim();
    var price = parseFloat(document.getElementById("price").value);
    var date = dateInput.value;

    if (!name || !category || !unit || !date) return;
    if (isNaN(quantity) || quantity <= 0) return;
    if (isNaN(price) || price < 0) return;

    items.push({
      id: makeId(),
      name: name,
      category: category,
      quantity: quantity,
      unit: unit,
      price: price,
      date: date
    });
    saveItems();
    form.reset();
    dateInput.value = todayStr();
    document.getElementById("quantity").value = 1;
    render();
    nameInput.focus();
  });

  periodTabs.addEventListener("click", function (e) {
    var btn = e.target.closest("button[data-period]");
    if (!btn) return;
    currentPeriod = btn.getAttribute("data-period");
    Array.prototype.forEach.call(periodTabs.querySelectorAll(".tab"), function (t) {
      t.classList.toggle("active", t === btn);
    });
    render();
  });

  itemsBody.addEventListener("click", function (e) {
    var btn = e.target.closest("button[data-delete-id]");
    if (!btn) return;
    var id = btn.getAttribute("data-delete-id");
    items = items.filter(function (it) { return it.id !== id; });
    saveItems();
    render();
  });

  exportBtn.addEventListener("click", function () {
    var blob = new Blob([JSON.stringify(items, null, 2)], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "xarid-royxati-" + todayStr() + ".json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  importInput.addEventListener("change", function () {
    var file = importInput.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () {
      try {
        var data = JSON.parse(reader.result);
        if (!Array.isArray(data)) throw new Error("invalid");
        var existingIds = {};
        items.forEach(function (it) { existingIds[it.id] = true; });
        data.forEach(function (it) {
          if (!it || typeof it.name !== "string") return;
          if (!it.id || existingIds[it.id]) it.id = makeId();
          existingIds[it.id] = true;
          items.push(it);
        });
        saveItems();
        render();
      } catch (err) {
        alert("Fayl noto'g'ri formatda.");
      }
      importInput.value = "";
    };
    reader.readAsText(file);
  });

  clearBtn.addEventListener("click", function () {
    if (!items.length) return;
    if (!confirm("Barcha xaridlar tarixi o'chiriladi. Davom etasizmi?")) return;
    items = [];
    saveItems();
    render();
  });

  function loadItems() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      var parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      return [];
    }
  }

  function saveItems() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch (err) {
      alert("Ma'lumotlarni saqlab bo'lmadi (xotira to'lgan bo'lishi mumkin).");
    }
  }

  function makeId() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return "id-" + Date.now() + "-" + Math.random().toString(16).slice(2);
  }

  function todayStr() {
    var d = new Date();
    return formatDate(d);
  }

  function formatDate(d) {
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, "0");
    var day = String(d.getDate()).padStart(2, "0");
    return y + "-" + m + "-" + day;
  }

  function getPeriodRange(period) {
    var now = new Date();
    now.setHours(0, 0, 0, 0);
    if (period === "today") {
      return [now, now];
    }
    if (period === "week") {
      var dayOfWeek = now.getDay() === 0 ? 7 : now.getDay(); // Monday=1..Sunday=7
      var monday = new Date(now);
      monday.setDate(now.getDate() - (dayOfWeek - 1));
      var sunday = new Date(monday);
      sunday.setDate(monday.getDate() + 6);
      return [monday, sunday];
    }
    if (period === "month") {
      var first = new Date(now.getFullYear(), now.getMonth(), 1);
      var last = new Date(now.getFullYear(), now.getMonth() + 1, 0);
      return [first, last];
    }
    return null; // all
  }

  function filterByPeriod(period) {
    var range = getPeriodRange(period);
    if (!range) return items.slice();
    var startStr = formatDate(range[0]);
    var endStr = formatDate(range[1]);
    return items.filter(function (it) {
      return it.date >= startStr && it.date <= endStr;
    });
  }

  function money(n) {
    return Math.round(n).toLocaleString("uz-UZ") + " so'm";
  }

  function render() {
    renderNameSuggestions();
    var filtered = filterByPeriod(currentPeriod).sort(function (a, b) {
      return b.date.localeCompare(a.date);
    });
    renderSummary(filtered);
    renderCategoryChart(filtered);
    renderTopProducts(filtered);
    renderItemsTable(filtered);
  }

  function renderNameSuggestions() {
    var names = Array.from(new Set(items.map(function (it) { return it.name; })));
    nameSuggestions.innerHTML = names.map(function (n) {
      return '<option value="' + escapeHtml(n) + '">';
    }).join("");
  }

  function renderSummary(filtered) {
    var total = filtered.reduce(function (sum, it) { return sum + it.price * it.quantity; }, 0);
    var distinctProducts = new Set(filtered.map(function (it) { return it.name.toLowerCase(); })).size;
    var distinctDays = new Set(filtered.map(function (it) { return it.date; })).size;
    var dailyAvg = distinctDays ? total / distinctDays : 0;

    document.getElementById("summary-total").textContent = money(total);
    document.getElementById("summary-count").textContent = filtered.length;
    document.getElementById("summary-products").textContent = distinctProducts;
    document.getElementById("summary-daily-avg").textContent = money(dailyAvg);
  }

  function renderCategoryChart(filtered) {
    var totals = {};
    filtered.forEach(function (it) {
      var key = it.category || "Boshqa";
      totals[key] = (totals[key] || 0) + it.price * it.quantity;
    });
    var entries = Object.keys(totals).map(function (k) { return [k, totals[k]]; });
    entries.sort(function (a, b) { return b[1] - a[1]; });

    if (!entries.length) {
      categoryChart.innerHTML = '<p class="empty-hint">Hali ma\'lumot yo\'q</p>';
      return;
    }

    var max = entries[0][1];
    categoryChart.innerHTML = entries.map(function (e) {
      var pct = max ? Math.round((e[1] / max) * 100) : 0;
      return (
        '<div class="chart-row">' +
        '<span class="chart-label">' + escapeHtml(e[0]) + '</span>' +
        '<div class="chart-bar-track"><div class="chart-bar-fill" style="width:' + pct + '%"></div></div>' +
        '<span class="chart-value">' + money(e[1]) + '</span>' +
        '</div>'
      );
    }).join("");
  }

  function renderTopProducts(filtered) {
    var byName = {};
    filtered.forEach(function (it) {
      var key = it.name.toLowerCase();
      if (!byName[key]) {
        byName[key] = { name: it.name, count: 0, quantity: 0, unit: it.unit, spent: 0 };
      }
      byName[key].count += 1;
      byName[key].quantity += it.quantity;
      byName[key].spent += it.price * it.quantity;
    });
    var list = Object.values(byName).sort(function (a, b) {
      return b.count - a.count || b.spent - a.spent;
    }).slice(0, 10);

    topProductsEmpty.style.display = list.length ? "none" : "block";
    topProductsBody.innerHTML = list.map(function (p) {
      return (
        "<tr>" +
        "<td>" + escapeHtml(p.name) + "</td>" +
        "<td>" + p.count + "</td>" +
        "<td>" + trimNum(p.quantity) + " " + escapeHtml(p.unit) + "</td>" +
        "<td>" + money(p.spent) + "</td>" +
        "</tr>"
      );
    }).join("");
  }

  function renderItemsTable(filtered) {
    itemsEmpty.style.display = filtered.length ? "none" : "block";
    itemsBody.innerHTML = filtered.map(function (it) {
      return (
        "<tr>" +
        "<td>" + it.date + "</td>" +
        "<td>" + escapeHtml(it.name) + "</td>" +
        "<td>" + escapeHtml(it.category) + "</td>" +
        "<td>" + trimNum(it.quantity) + " " + escapeHtml(it.unit) + "</td>" +
        "<td>" + money(it.price) + "</td>" +
        "<td>" + money(it.price * it.quantity) + "</td>" +
        '<td><button class="delete-btn" data-delete-id="' + it.id + '" title="O\'chirish">✕</button></td>' +
        "</tr>"
      );
    }).join("");
  }

  function trimNum(n) {
    return (Math.round(n * 100) / 100).toString();
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  render();
})();
