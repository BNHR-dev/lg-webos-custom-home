/* Manual developer-mode launcher. No root, boot hook, raw input or Home interception. */
(function () {
  'use strict';
  var config = window.HOME_CONFIG || { apps: [], inputs: [] };
  var bridges = [];
  var history = [];
  var groups = [[], []];
  var busy = false;
  function record(event, detail) {
    history.push({ time: new Date().toISOString(), event: event, detail: detail });
    if (history.length > 80) history.shift();
    console.log('[customhome]', event, JSON.stringify(detail));
  }
  window.homeDiagnostics = { events: history, pending: bridges };
  function status(text, error) {
    var node = document.getElementById('status');
    node.textContent = text;
    node.className = error ? 'error' : '';
  }
  function call(uri, params, done) {
    var bridge, timer, ended = false;
    function finish(result) {
      if (ended) return;
      ended = true;
      clearTimeout(timer);
      var i = bridges.indexOf(bridge);
      if (i >= 0) bridges.splice(i, 1);
      if (bridge && bridge.cancel) { try { bridge.cancel(); } catch (_) {} }
      record('api', { uri: uri, result: result });
      done(result);
    }
    try {
      if (!window.PalmServiceBridge) throw new Error('API webOS indisponible');
      bridge = new window.PalmServiceBridge();
      bridges.push(bridge);
      bridge.onservicecallback = function (message) {
        try { finish(JSON.parse(message)); }
        catch (e) { finish({ returnValue: false, errorText: 'Réponse illisible' }); }
      };
      timer = setTimeout(function () { finish({ returnValue: false, errorText: 'Aucune réponse après 8 secondes' }); }, 8000);
      bridge.call(uri, JSON.stringify(params));
    } catch (e) { finish({ returnValue: false, errorText: e.message }); }
  }
  function enabled(row) { return groups[row].filter(function (b) { return !b.disabled; }); }
  function focus(button) {
    if (!button) return;
    button.focus();
    var row = button.parentNode;
    var left = button.offsetLeft - row.offsetLeft;
    row.scrollLeft = Math.max(0, left - (row.clientWidth - button.offsetWidth) / 2);
    try { sessionStorage.setItem('home-focus', button.dataset.appId); } catch (_) {}
  }
  function restoreFocus() {
    var id;
    try { id = sessionStorage.getItem('home-focus'); } catch (_) {}
    var all = enabled(0).concat(enabled(1));
    focus(all.filter(function (b) { return b.dataset.appId === id; })[0] || all[0]);
  }
  function open(item) {
    if (busy) return;
    busy = true;
    status('Ouverture de ' + item.name + '…');
    record('launch-request', { id: item.id });
    call('luna://com.webos.applicationManager/launch', { id: item.id }, function (result) {
      busy = false;
      if (result.returnValue) status(item.name + ' : ouverture acceptée.');
      else status('Impossible d’ouvrir ' + item.name + ' : ' + (result.errorText || 'accès refusé'), true);
    });
  }
  function add(item, row, input) {
    if (!item || typeof item.id !== 'string' || !item.id || groups[row].some(function (b) { return b.dataset.appId === item.id; })) return;
    var button = document.createElement('button');
    button.className = 'tile' + (input ? ' input' : '');
    button.type = 'button';
    button.dataset.appId = item.id;
    if (item.color && /^#[0-9a-f]{6}$/i.test(item.color)) button.style.backgroundColor = item.color;
    var symbol = document.createElement('span'); symbol.className = 'symbol'; symbol.textContent = item.symbol || (input ? item.name : item.name.slice(0, 2));
    var name = document.createElement('span'); name.className = 'name'; name.textContent = input ? 'Ouvrir cette entrée' : item.name;
    button.appendChild(symbol); button.appendChild(name);
    button.setAttribute('aria-label', item.name);
    button.addEventListener('click', function () { focus(button); open(item); });
    button.addEventListener('focus', function () {
      try { sessionStorage.setItem('home-focus', item.id); } catch (_) {}
    });
    document.getElementById(input ? 'inputs' : 'apps').appendChild(button);
    groups[row].push(button);
    call('luna://com.webos.applicationManager/getAppLoadStatus', { appId: item.id }, function (result) {
      if (result.returnValue && result.exist === false) {
        button.disabled = true; name.textContent = 'Non installée';
        if (document.activeElement === button) restoreFocus();
      }
    });
  }
  document.getElementById('title').textContent = config.title || 'Mon accueil';
  document.title = config.title || 'Mon accueil';
  function clock() {
    var now = new Date();
    try {
      document.getElementById('clock').textContent = now.toLocaleTimeString(config.locale || 'fr-FR', { hour: '2-digit', minute: '2-digit' });
      document.getElementById('date').textContent = now.toLocaleDateString(config.locale || 'fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
    } catch (_) { document.getElementById('clock').textContent = now.getHours() + ':' + ('0' + now.getMinutes()).slice(-2); }
  }
  clock(); setInterval(clock, 10000);
  (config.apps || []).forEach(function (item) { add(item, 0, false); });
  document.getElementById('empty-apps').hidden = groups[0].length > 0;
  function inputs(items) {
    items.forEach(function (item) { add(item, 1, true); });
    document.getElementById('inputs-section').hidden = groups[1].length === 0;
  }
  inputs(config.inputs || []);
  if (config.discoverInputs) {
    call('luna://com.webos.service.eim/getAllInputStatus', {}, function (result) {
      if (result.returnValue && Array.isArray(result.devices)) {
        inputs(result.devices.filter(function (d) { return /^HDMI_/.test(d.id) && typeof d.appId === 'string'; }).map(function (d) {
          return { id: d.appId, name: d.label || d.id };
        }));
        status('Choisis une application ou une entrée.');
      } else {
        status('Applications prêtes. Liste HDMI indisponible.', false);
      }
      if (!groups[0].length) restoreFocus();
    });
  } else status('Choisis une application ou une entrée.');
  document.addEventListener('keydown', function (event) {
    var key = event.key;
    var code = event.keyCode;
    if (code === 461 || key === 'Escape' || key === 'BrowserBack') {
      event.preventDefault();
      record('exit', {});
      if (window.webOS && window.webOS.platformBack) window.webOS.platformBack();
      else window.close();
      return;
    }
    var row = groups[1].indexOf(document.activeElement) >= 0 ? 1 : 0;
    var list = enabled(row), index = list.indexOf(document.activeElement);
    if (index < 0) index = 0;
    if (key === 'ArrowLeft' || code === 37) { event.preventDefault(); focus(list[Math.max(0, index - 1)]); }
    else if (key === 'ArrowRight' || code === 39) { event.preventDefault(); focus(list[Math.min(list.length - 1, index + 1)]); }
    else if (key === 'ArrowDown' || code === 40 || key === 'ArrowUp' || code === 38) {
      event.preventDefault();
      var other = enabled(key === 'ArrowDown' || code === 40 ? Math.min(1, row + 1) : Math.max(0, row - 1));
      focus(other[Math.min(index, other.length - 1)]);
    } else if (key === 'Enter' || code === 13) {
      event.preventDefault();
      if (document.activeElement && document.activeElement.classList.contains('tile')) document.activeElement.click();
    }
  });
  window.addEventListener('webOSRelaunch', restoreFocus);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) { busy = false; restoreFocus(); clock(); } });
  window.addEventListener('error', function (event) { record('error', { message: event.message }); status('Erreur de l’accueil : ' + event.message, true); });
  restoreFocus();
  // Deterministic local sky, adapted from the original launcher; no remote images.
  var canvas = document.getElementById('stars');
  function sky() {
    canvas.width = window.innerWidth; canvas.height = window.innerHeight;
    var ctx = canvas.getContext('2d'), seed = 42;
    function random() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }
    for (var i = 0; i < 170; i++) {
      ctx.beginPath(); ctx.arc(random() * canvas.width, random() * canvas.height * .7, random() * 1.3 + .3, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(220,233,255,' + (random() * .5 + .15) + ')'; ctx.fill();
    }
  }
  window.addEventListener('resize', sky); sky();
  record('ready', { appCount: groups[0].length });
})();
