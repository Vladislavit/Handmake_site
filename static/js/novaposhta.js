/* Клубок — вибір відділення/поштомата Нової Пошти на чекауті.
   Дані беруться з нашої БД (ендпоінти /np/cities/ та /np/warehouses/),
   карта — Leaflet + OpenStreetMap. */
(function () {
  'use strict';

  var delivery = document.getElementById('delivery');
  if (!delivery) return;

  var npFields = document.getElementById('np-fields');
  var branchBlock = document.getElementById('np-branch-block');
  var addrField = document.getElementById('addr-field');

  var cityInput = document.getElementById('np-city-input');
  var fCity = document.getElementById('f-city');
  var fCityRef = document.getElementById('f-city-ref');
  var suggestBox = document.getElementById('np-city-suggest');

  var listEl = document.getElementById('np-list');
  var mapEl = document.getElementById('np-map');
  var fBranch = document.getElementById('f-branch');
  var fWhRef = document.getElementById('f-wh-ref');
  var selectedEl = document.getElementById('np-selected');

  var state = { cityRef: fCityRef.value || '', type: 'branch', warehouses: [], selected: fWhRef.value || '' };
  var map = null, markersLayer = null, markersByRef = {};

  function getJSON(url) {
    return fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } }).then(function (r) { return r.json(); });
  }
  function debounce(fn, ms) {
    var t; return function () { var a = arguments, c = this; clearTimeout(t); t = setTimeout(function () { fn.apply(c, a); }, ms); };
  }

  /* ---------- видимість блоків залежно від способу доставки ---------- */
  function applyDelivery(value) {
    if (value === 'pickup') {
      npFields.classList.add('hidden');
      return;
    }
    npFields.classList.remove('hidden');
    if (value === 'np-courier') {
      addrField.classList.remove('hidden');
      branchBlock.classList.add('hidden');
    } else { // np-branch
      addrField.classList.add('hidden');
      branchBlock.classList.remove('hidden');
      ensureMap();
      if (state.cityRef && !state.warehouses.length) loadWarehouses();
    }
  }

  delivery.querySelectorAll('.ro').forEach(function (r) {
    r.addEventListener('click', function () {
      delivery.querySelectorAll('.ro').forEach(function (o) { o.classList.remove('on'); });
      r.classList.add('on');
      var radio = r.querySelector('input[type=radio]');
      if (radio) radio.checked = true;
      applyDelivery(r.dataset.d);
    });
  });

  /* ---------- карта ---------- */
  function ensureMap() {
    if (map || typeof L === 'undefined') { if (map) map.invalidateSize(); return; }
    map = L.map(mapEl, { scrollWheelZoom: false }).setView([49.0, 32.0], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap'
    }).addTo(map);
    // Кластеризація маркерів (плагін Leaflet.markercluster), з фолбеком
    markersLayer = (typeof L.markerClusterGroup === 'function')
      ? L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 50 })
      : L.layerGroup();
    markersLayer.addTo(map);
    setTimeout(function () { map.invalidateSize(); }, 200);
  }

  /* ---------- автодоповнення міста ---------- */
  function renderSuggest(cities) {
    if (!cities.length) { suggestBox.classList.add('hidden'); return; }
    suggestBox.innerHTML = '';
    cities.forEach(function (c) {
      var div = document.createElement('div');
      div.className = 'np-suggest-item';
      div.textContent = c.area ? (c.name + ' — ' + c.area) : c.name;
      div.addEventListener('click', function () { pickCity(c); });
      suggestBox.appendChild(div);
    });
    suggestBox.classList.remove('hidden');
  }

  function pickCity(c) {
    cityInput.value = c.name;
    fCity.value = c.name;
    fCityRef.value = c.ref;
    state.cityRef = c.ref;
    suggestBox.classList.add('hidden');
    clearSelection();
    loadWarehouses();
  }

  cityInput.addEventListener('input', debounce(function () {
    var q = cityInput.value.trim();
    fCity.value = q;          // якщо користувач не обрав зі списку — лишаємо текст
    state.cityRef = '';       // ref скидаємо, доки не обрано місто зі списку
    fCityRef.value = '';
    if (q.length < 2) { suggestBox.classList.add('hidden'); return; }
    getJSON('/np/cities/?q=' + encodeURIComponent(q)).then(function (d) { renderSuggest(d.cities || []); });
  }, 250));

  document.addEventListener('click', function (e) {
    if (!suggestBox.contains(e.target) && e.target !== cityInput) suggestBox.classList.add('hidden');
  });

  /* ---------- перемикач Відділення / Поштомати ---------- */
  document.querySelectorAll('.np-type-toggle .chip').forEach(function (chip) {
    chip.addEventListener('click', function () {
      document.querySelectorAll('.np-type-toggle .chip').forEach(function (c) { c.classList.remove('on'); });
      chip.classList.add('on');
      state.type = chip.dataset.nptype;
      clearSelection();
      loadWarehouses();
    });
  });

  /* ---------- список + маркери ---------- */
  function loadWarehouses() {
    if (!state.cityRef) {
      listEl.innerHTML = '<p class="np-hint">Оберіть місто зі списку, щоб побачити відділення.</p>';
      return;
    }
    listEl.innerHTML = '<p class="np-hint">Завантаження…</p>';
    ensureMap();
    getJSON('/np/warehouses/?city=' + encodeURIComponent(state.cityRef) + '&type=' + state.type)
      .then(function (d) {
        state.warehouses = d.warehouses || [];
        renderWarehouses();
      });
  }

  function renderWarehouses() {
    var items = state.warehouses;
    markersByRef = {};
    if (markersLayer) markersLayer.clearLayers();

    if (!items.length) {
      listEl.innerHTML = '<p class="np-hint">У цьому місті немає ' +
        (state.type === 'poshtomat' ? 'поштоматів' : 'відділень') + '.</p>';
      return;
    }

    listEl.innerHTML = '';
    var bounds = [];
    items.forEach(function (w) {
      var item = document.createElement('button');
      item.type = 'button';
      item.className = 'np-item' + (w.ref === state.selected ? ' on' : '');
      item.dataset.ref = w.ref;
      item.innerHTML = '<span class="np-num">' + (w.number || '•') + '</span>' +
        '<span class="np-addr">' + (w.short_address || w.description) + '</span>';
      item.addEventListener('click', function () { selectWarehouse(w, true); });
      listEl.appendChild(item);

      if (map && w.lat && w.lng) {
        var marker = L.marker([w.lat, w.lng]);
        marker.bindPopup('<b>№' + (w.number || '') + '</b><br>' + (w.short_address || w.description));
        marker.on('click', function () { selectWarehouse(w, false); });
        marker.addTo(markersLayer);
        markersByRef[w.ref] = marker;
        bounds.push([w.lat, w.lng]);
      }
    });

    if (map && bounds.length) {
      map.invalidateSize();
      map.fitBounds(bounds, { padding: [30, 30], maxZoom: 14 });
    }
  }

  function selectWarehouse(w, fromList) {
    state.selected = w.ref;
    fBranch.value = w.description;
    fWhRef.value = w.ref;
    selectedEl.textContent = 'Обрано: ' + w.description;
    selectedEl.classList.remove('hidden');

    listEl.querySelectorAll('.np-item').forEach(function (el) {
      el.classList.toggle('on', el.dataset.ref === w.ref);
    });
    var marker = markersByRef[w.ref];
    if (marker) {
      // якщо маркер сховано в кластері — спершу розкрити кластер, тоді показати попап
      if (typeof markersLayer.zoomToShowLayer === 'function') {
        markersLayer.zoomToShowLayer(marker, function () { marker.openPopup(); });
      } else {
        map.setView(marker.getLatLng(), 15);
        marker.openPopup();
      }
    }
    if (!fromList) {
      var active = listEl.querySelector('.np-item.on');
      if (active) active.scrollIntoView({ block: 'nearest' });
    }
  }

  function clearSelection() {
    state.selected = '';
    fBranch.value = '';
    fWhRef.value = '';
    if (selectedEl) { selectedEl.textContent = ''; selectedEl.classList.add('hidden'); }
  }

  /* ---------- початковий стан ---------- */
  var checked = delivery.querySelector('.ro.on');
  applyDelivery(checked ? checked.dataset.d : 'np-branch');
})();
