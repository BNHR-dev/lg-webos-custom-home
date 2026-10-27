/* Versioned, app-local preferences. Does not write TV settings or uninstall apps. */
(function(root) {
    "use strict";
    var KEY = "bnhr.customhome.preferences.v1";
    function defaults() {
        return {
            schema: 1,
            order: [],
            hidden: [],
            background: "panorama",
            dim: 15,
            selected: ""
        };
    }
    function normalize(value, config) {
        var p = defaults();
        value = value || {};
        p.order = Array.isArray(value.order) ? value.order.filter(function(id, i, a) {
            return typeof id === "string" && a.indexOf(id) === i;
        }) : [];
        p.hidden = Array.isArray(value.hidden) ? value.hidden.filter(function(id, i, a) {
            return typeof id === "string" && a.indexOf(id) === i;
        }) : [];
        p.background = typeof value.background === "string" ? value.background : p.background;
        p.dim = typeof value.dim === "number" ? Math.max(0, Math.min(70, Math.round(value.dim / 5) * 5)) : p.dim;
        p.selected = typeof value.selected === "string" ? value.selected : "";
        return p;
    }
    root.HomePreferences = {
        key: KEY,
        load: function(storage, config) {
            var value;
            try {
                value = JSON.parse(storage.getItem(KEY));
            } catch (e) {}
            return normalize(value, config);
        },
        save: function(storage, value) {
            try {
                storage.setItem(KEY, JSON.stringify(value));
                return true;
            } catch (e) {
                return false;
            }
        },
        normalize: normalize,
        ordered: function(items, prefs) {
            var ranked = items.slice();
            ranked.sort(function(a, b) {
                var x = prefs.order.indexOf(a.id), y = prefs.order.indexOf(b.id);
                return (x < 0 ? 1e5 + items.indexOf(a) : x) - (y < 0 ? 1e5 + items.indexOf(b) : y);
            });
            return ranked;
        }
    };
})(typeof window === "undefined" ? globalThis : window);
