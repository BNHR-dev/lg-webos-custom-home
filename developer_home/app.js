/* Panorama: native webOS app. System integration is deliberately separate. */
(function() {
    "use strict";
    var config = window.HOME_CONFIG || {
        apps: []
    }, P = window.HomePreferences, storage;
    try {
        storage = window.localStorage;
    } catch (e) {
        storage = {
            getItem: function() {
                return null;
            },
            setItem: function() {
                throw new Error("storage unavailable");
            }
        };
    }
    var prefs = P.load(storage, config), stage = document.getElementById("stage"), apps = config.apps || [], inputs = config.inputs || [], groups = [ [], [] ], selected = prefs.selected, modal = null, settingsPage = "main", settingsOrigin = null, returnSettings = null, busy = false, launchToken = 0, bridges = [], events = [], clockTimer = null, saveTimer = null;
    var TOOL_IDS = [ "com.amazoff.patcher", "com.pirate.refresh", "org.webosbrew.hbchannel", "org.webosbrew.safeupdate" ];
    try {
        if (!prefs.selected) prefs.selected = sessionStorage.getItem("home-focus") || "";
        selected = prefs.selected;
    } catch (e) {}
    var descriptions = {
        "youtube.leanback.v4": "Vidéos, chaînes et abonnements.",
        "twitch.adamffdev.v1": "Vos directs et communautés.",
        netflix: "Films et séries.",
        "com.disney.disneyplus-prod": "Les univers Disney, Pixar et plus encore.",
        "com.crunchyroll.webapp": "Anime et séries d’animation.",
        amazon: "Films, séries et vos sélections.",
        canalplus: "Chaînes, cinéma et programmes.",
        "com.breezyfin.app": "Votre bibliothèque multimédia."
    };
    var shade = document.getElementById("shade"), panel = document.getElementById("settings"), content = document.getElementById("settings-content"), feedback = document.getElementById("feedback");
    var backgrounds = config.backgrounds && config.backgrounds.length ? config.backgrounds : [ {
        id: "panorama",
        name: "Horizon",
        src: "assets/panorama.svg"
    }, {
        id: "dunes",
        name: "Dunes",
        src: "assets/dunes.svg"
    } ];
    function record(event, detail) {
        events.push({
            time: (new Date).toISOString(),
            event: event,
            detail: detail || {}
        });
        if (events.length > 60) events.shift();
        console.log("[customhome]", event, JSON.stringify(detail || {}));
    }
    window.homeDiagnostics = {
        events: events,
        pending: bridges,
        version: "0.2.0",
        getState: function() {
            return {
                busy: busy,
                modal: modal,
                settingsPage: settingsPage,
                prefs: prefs,
                appCount: apps.length,
                inputCount: inputs.length,
                backgrounded: document.hidden,
                clockRunning: clockTimer !== null
            };
        }
    };
    function fit() {
        var scale = Math.min(innerWidth / 1920, innerHeight / 1080);
        stage.style.transform = "scale(" + scale + ")";
        stage.style.left = (innerWidth - 1920 * scale) / 2 + "px";
        stage.style.top = (innerHeight - 1080 * scale) / 2 + "px";
    }
    fit();
    addEventListener("resize", fit);
    function save() {
        clearTimeout(saveTimer);
        if (!P.save(storage, prefs)) {
            message("Impossible d’enregistrer les préférences. Elles seront perdues à la fermeture.", true);
            record("preferences_save_failed");
        }
    }
    function message(text, error) {
        var s = document.getElementById("settings-status");
        s.textContent = text;
        s.className = error ? "error" : "";
    }
    function tool(a) {
        return a.category === "tools" || !a.category && TOOL_IDS.indexOf(a.id) >= 0;
    }
    function allShortcuts() {
        return apps.filter(function(a) {
            return !tool(a);
        }).concat(inputs);
    }
    function entertainment() {
        return P.ordered(apps.filter(function(a) {
            return !tool(a);
        }), prefs).filter(function(a) {
            return prefs.hidden.indexOf(a.id) < 0;
        });
    }
    function call(uri, params, done, timeout) {
        var bridge, timer, finished = false;
        function finish(result) {
            if (finished) return;
            finished = true;
            clearTimeout(timer);
            var i = bridges.indexOf(bridge);
            if (i >= 0) bridges.splice(i, 1);
            if (bridge && bridge.cancel) {
                try {
                    bridge.cancel();
                } catch (e) {}
            }
            record("api", {
                uri: uri,
                returnValue: result.returnValue,
                errorText: result.errorText
            });
            done(result);
        }
        try {
            if (!window.PalmServiceBridge) throw new Error("Service webOS indisponible.");
            bridge = new window.PalmServiceBridge;
            bridges.push(bridge);
            bridge.onservicecallback = function(data) {
                var result;
                try {
                    result = JSON.parse(data);
                } catch (e) {
                    result = {
                        returnValue: false,
                        errorText: "Réponse illisible du système."
                    };
                }
                finish(result);
            };
            timer = setTimeout(function() {
                finish({
                    returnValue: false,
                    errorText: "La télévision n’a pas répondu à temps."
                });
            }, timeout || 8e3);
            bridge.call(uri, JSON.stringify(params));
        } catch (e) {
            finish({
                returnValue: false,
                errorText: e.message
            });
        }
    }
    function localAsset(src) {
        return typeof src === "string" && /^assets\/[a-zA-Z0-9_./-]+$/.test(src) && src.indexOf("..") < 0 ? src : null;
    }
    function applyBackground() {
        var bg = backgrounds.find(function(a) {
            return a.id === prefs.background;
        }) || backgrounds[0];
        var src = localAsset(bg.src) || "assets/panorama.svg";
        stage.style.setProperty("--background-image", 'url("' + src + '")');
        stage.style.setProperty("--dim", String(prefs.dim / 100));
    }
    function button(label, cls, handler) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = cls;
        b.setAttribute("aria-label", label);
        if (handler) b.onclick = handler;
        b.addEventListener("focus", function() {
            if (!b.classList.contains("is-focus")) focus(b);
        });
        b.addEventListener("mouseenter", function() {
            if (!b.disabled) focus(b);
        });
        return b;
    }
    function heading(text) {
        var h = document.createElement("h3");
        h.textContent = text;
        content.appendChild(h);
    }
    function paragraph(text) {
        var p = document.createElement("p");
        p.className = "panel-note";
        p.textContent = text;
        content.appendChild(p);
        return p;
    }
    function focus(b) {
        if (!b || b.disabled || !document.contains(b)) return;
        if (b.classList.contains("is-focus") && document.activeElement === b) return;
        var previous = document.querySelector(".is-focus");
        if (previous) previous.classList.remove("is-focus");
        b.classList.add("is-focus");
        if (document.activeElement !== b) b.focus({
            preventScroll: true
        });
        if (b.dataset.appId && b.classList.contains("app-button")) {
            var a = apps.find(function(x) {
                return x.id === b.dataset.appId;
            });
            if (a) {
                selected = a.id;
                prefs.selected = selected;
                clearTimeout(saveTimer);
                saveTimer = setTimeout(save, 250);
                document.getElementById("selected-title").textContent = a.name;
                document.getElementById("selected-description").textContent = a.description || descriptions[a.id] || "Ouvrir cette application.";
                document.getElementById("focus-label").textContent = a.name;
                document.getElementById("position").textContent = groups[0].indexOf(b) + 1 + " / " + groups[0].length;
                var row = document.getElementById("apps");
                row.scrollLeft = Math.max(0, b.offsetLeft - row.offsetLeft - (row.clientWidth - b.clientWidth) / 2);
            }
        }
        if (panel.contains(b)) {
            b.scrollIntoView({
                block: "nearest",
                inline: "nearest"
            });
        }
    }
    function restore() {
        var target = groups[0].find(function(b) {
            return b.dataset.appId === selected;
        }) || groups[0][0] || groups[1][0];
        focus(target);
    }
    function appTile(a) {
        var b = button(a.name, "app-button", function() {
            focus(b);
            launch(a, {
                kind: "home"
            });
        });
        b.dataset.appId = a.id;
        var src = localAsset(a.logo);
        function fallback() {
            b.classList.add("has-wordmark");
            var text = document.createElement("span");
            text.className = "wordmark";
            text.textContent = a.name;
            b.insertBefore(text, b.firstChild);
            var lab = b.querySelector(".app-name");
            if (lab) lab.classList.add("duplicate");
        }
        if (src) {
            var img = document.createElement("img");
            img.className = "logo" + (a.logoMonochrome ? " monochrome" : "");
            img.alt = "";
            img.src = src;
            img.onerror = function() {
                img.remove();
                fallback();
            };
            b.appendChild(img);
        }
        var name = document.createElement("span");
        name.className = "app-name";
        name.textContent = a.name;
        if (a.logoContainsName) name.classList.add("duplicate");
        b.appendChild(name);
        if (!src) fallback();
        return b;
    }
    function renderHome(keepFocus) {
        var list = entertainment(), container = document.getElementById("apps");
        container.textContent = "";
        groups = [ [], [] ];
        list.forEach(function(a) {
            var b = appTile(a);
            container.appendChild(b);
            groups[0].push(b);
        });
        if (!list.length) {
            var p = document.createElement("p");
            p.className = "empty-message";
            p.textContent = "Tous les raccourcis sont masqués. Retrouve-les dans Paramètres.";
            container.appendChild(p);
            document.getElementById("selected-title").textContent = "Votre accueil";
            document.getElementById("selected-description").textContent = "Affiche de nouveau tes raccourcis dans les paramètres.";
            document.getElementById("position").textContent = "0";
        }
        var row = document.getElementById("utility-row");
        row.textContent = "";
        P.ordered(inputs, prefs).filter(function(a) {
            return prefs.hidden.indexOf(a.id) < 0;
        }).forEach(function(a) {
            var b = button(a.name, "utility", function() {
                focus(b);
                launch(a, {
                    kind: "utility",
                    id: a.id
                });
            });
            b.dataset.appId = a.id;
            b.textContent = "▣  " + a.name;
            row.appendChild(b);
            groups[1].push(b);
        });
        var settings = button("Paramètres", "utility", function() {
            openSettings();
        });
        settings.dataset.action = "settings";
        settings.textContent = "⚙  Paramètres";
        row.appendChild(settings);
        groups[1].push(settings);
        if (keepFocus) restore();
    }
    function setting(label, value, handler, key) {
        var b = button(label, "setting", handler), left = document.createElement("span"), right = document.createElement("strong");
        left.textContent = label;
        right.textContent = value || "";
        b.appendChild(left);
        b.appendChild(right);
        if (key) b.dataset.setting = key;
        content.appendChild(b);
        return b;
    }
    function openSettings(page) {
        settingsOrigin = selected;
        modal = "settings";
        shade.hidden = false;
        panel.hidden = false;
        feedback.hidden = true;
        settingsPage = page || "main";
        renderSettings();
    }
    function renderSettings(focusKey) {
        content.textContent = "";
        message("");
        document.getElementById("settings-title").textContent = settingsPage === "organize" ? "Organiser les raccourcis" : "Paramètres";
        if (settingsPage === "organize") {
            paragraph("Déplace ou masque tes raccourcis. Aucune application ne sera désinstallée.");
            var appItems = P.ordered(apps.filter(function(a) {
                return !tool(a);
            }), prefs), inputItems = P.ordered(inputs, prefs), ordered = appItems.concat(inputItems);
            function isInput(a) {
                return inputs.some(function(x) {
                    return x.id === a.id;
                });
            }
            ordered.forEach(function(a, i) {
                var row = document.createElement("div");
                row.className = "manage-row";
                var name = document.createElement("span");
                name.className = "manage-name";
                name.textContent = a.name;
                row.appendChild(name);
                function move(delta) {
                    var next = i + delta;
                    if (next < 0 || next >= ordered.length || isInput(a) !== isInput(ordered[next])) return;
                    var temp = ordered[i];
                    ordered[i] = ordered[next];
                    ordered[next] = temp;
                    prefs.order = ordered.map(function(x) {
                        return x.id;
                    });
                    save();
                    renderHome(false);
                    renderSettings(a.id + ":" + (delta < 0 ? "up" : "down"));
                    message("Ordre enregistré.");
                }
                var up = button("Déplacer " + a.name + " avant", "setting", function() {
                    move(-1);
                });
                up.dataset.setting = a.id + ":up";
                up.textContent = "↑";
                up.disabled = i === 0 || isInput(a) !== isInput(ordered[i - 1]);
                row.appendChild(up);
                var down = button("Déplacer " + a.name + " après", "setting", function() {
                    move(1);
                });
                down.dataset.setting = a.id + ":down";
                down.textContent = "↓";
                down.disabled = i === ordered.length - 1 || isInput(a) !== isInput(ordered[i + 1]);
                row.appendChild(down);
                var hidden = prefs.hidden.indexOf(a.id) >= 0;
                var vis = button((hidden ? "Afficher " : "Masquer ") + a.name, "setting visibility", function() {
                    var index = prefs.hidden.indexOf(a.id);
                    if (index >= 0) prefs.hidden.splice(index, 1); else prefs.hidden.push(a.id);
                    save();
                    renderHome(false);
                    renderSettings(a.id + ":visible");
                    message(index >= 0 ? "Raccourci affiché." : "Raccourci masqué.");
                });
                vis.dataset.setting = a.id + ":visible";
                vis.textContent = hidden ? "Afficher" : "Masquer";
                row.appendChild(vis);
                content.appendChild(row);
            });
            setting("Restaurer l’ordre et les raccourcis initiaux", "Restaurer", function() {
                prefs.order = [];
                prefs.hidden = [];
                save();
                renderHome(false);
                renderSettings("reset");
                message("Ordre initial restauré.");
            }, "reset");
            setting("Revenir aux paramètres", "Retour", function() {
                settingsPage = "main";
                renderSettings();
            }, "back");
        } else {
            paragraph("Un accueil à ton goût, sans changer les réglages de la télévision.");
            heading("Affichage");
            var bg = backgrounds.find(function(a) {
                return a.id === prefs.background;
            }) || backgrounds[0];
            setting("Fond panoramique", bg.name, function() {
                var index = backgrounds.indexOf(bg);
                prefs.background = backgrounds[(index + 1) % backgrounds.length].id;
                save();
                applyBackground();
                renderSettings("background");
                message("Fond enregistré.");
            }, "background");
            var dim = setting("Assombrissement", prefs.dim + " %", function() {
                prefs.dim = prefs.dim + 5 > 70 ? 0 : prefs.dim + 5;
                save();
                applyBackground();
                renderSettings("dim");
            }, "dim");
            dim.dataset.adjust = "dim";
            paragraph("Sur Assombrissement : ← diminuer, → augmenter, OK changer.");
            setting("Organiser les raccourcis", "Ouvrir", function() {
                settingsPage = "organize";
                renderSettings();
            }, "organize");
            heading("Outils installés");
            apps.filter(tool).forEach(function(a) {
                setting(a.name, "Ouvrir", function() {
                    launch(a, {
                        kind: "settings",
                        page: "main",
                        key: "tool:" + a.id
                    });
                }, "tool:" + a.id);
            });
            heading("Accueil LG");
            setting("Ouvrir l’accueil LG", "Ouvrir", function() {
                launch({
                    id: "com.webos.app.home",
                    name: "Accueil LG"
                }, {
                    kind: "settings",
                    page: "main",
                    key: "lg-home"
                });
            }, "lg-home");
        }
        var buttons = Array.from(content.querySelectorAll("button:not(:disabled)"));
        focus(buttons.find(function(b) {
            return b.dataset.setting === focusKey;
        }) || buttons[0]);
    }
    function closeOverlay() {
        launchToken++;
        busy = false;
        feedback.hidden = true;
        if (returnSettings) {
            settingsPage = returnSettings.page || "main";
            var key = returnSettings.key;
            returnSettings = null;
            modal = "settings";
            panel.hidden = false;
            shade.hidden = false;
            renderSettings(key);
            return;
        }
        if (modal === "settings" && settingsPage === "organize") {
            settingsPage = "main";
            renderSettings("organize");
            return;
        }
        panel.hidden = true;
        shade.hidden = true;
        modal = null;
        renderHome(false);
        restore();
    }
    function feedbackAction(label, fn) {
        var b = button(label, "setting", fn);
        b.textContent = label;
        document.getElementById("feedback-actions").appendChild(b);
        return b;
    }
    function showFailure(a, origin, result) {
        busy = false;
        document.getElementById("feedback-icon").textContent = "!";
        document.getElementById("feedback-tag").textContent = "Ouverture impossible";
        document.getElementById("feedback-detail").textContent = result.missing ? "Cette application n’est plus installée. Tu peux masquer son raccourci dans les paramètres." : (result.errorText || "L’application a refusé de s’ouvrir.") + " Réessaie ou reviens à l’accueil.";
        document.getElementById("feedback-actions").textContent = "";
        if (!result.missing) feedbackAction("Réessayer", function() {
            launch(a, origin);
        });
        var back = feedbackAction("Retour", closeOverlay);
        focus(document.querySelector("#feedback-actions button") || back);
        record("launch_failed", {
            id: a.id,
            missing: !!result.missing
        });
    }
    function launch(a, origin) {
        if (busy) return;
        busy = true;
        var token = ++launchToken;
        returnSettings = origin.kind === "settings" ? origin : null;
        modal = "feedback";
        panel.hidden = true;
        shade.hidden = false;
        feedback.hidden = false;
        document.getElementById("feedback-icon").innerHTML = '<span class="spinner"></span>';
        document.getElementById("feedback-tag").textContent = "Ouverture";
        document.getElementById("feedback-title").textContent = a.name;
        document.getElementById("feedback-detail").textContent = "Patiente un instant…";
        document.getElementById("feedback-actions").textContent = "";
        focus(feedbackAction("Retour", closeOverlay));
        record("launch_request", {
            id: a.id
        });
        call("luna://com.webos.applicationManager/getAppLoadStatus", {
            appId: a.id
        }, function(status) {
            if (token !== launchToken) return;
            if (status.returnValue && status.exist === false) {
                showFailure(a, origin, {
                    missing: true
                });
                return;
            }
            call("luna://com.webos.applicationManager/launch", {
                id: a.id
            }, function(result) {
                if (token !== launchToken) return;
                if (!result.returnValue) {
                    showFailure(a, origin, result);
                    return;
                }
                busy = false;
                document.getElementById("feedback-icon").textContent = "✓";
                document.getElementById("feedback-tag").textContent = "Ouverture acceptée";
                document.getElementById("feedback-detail").textContent = "La télévision ouvre " + a.name + ".";
                document.getElementById("feedback-actions").textContent = "";
                focus(feedbackAction("Revenir à l’accueil", closeOverlay));
                record("launch_accepted", {
                    id: a.id
                });
            });
        });
    }
    function exit() {
        save();
        record("exit");
        if (window.webOS && window.webOS.platformBack) window.webOS.platformBack(); else window.close();
    }
    addEventListener("keydown", function(e) {
        var key = e.key;
        if (e.keyCode === 461) key = "Escape";
        if (![ "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Enter", "Escape", "Backspace" ].includes(key)) return;
        e.preventDefault();
        if (key === "Escape" || key === "Backspace") {
            if (modal) closeOverlay(); else exit();
            return;
        }
        if (key === "Enter") {
            if (e.repeat) return;
            if (document.activeElement && document.activeElement.tagName === "BUTTON") document.activeElement.click();
            return;
        }
        if (modal) {
            var surface = modal === "settings" ? content : feedback;
            var buttons = Array.from(surface.querySelectorAll("button:not(:disabled)"));
            var b = document.activeElement;
            if (b.dataset.adjust === "dim" && (key === "ArrowLeft" || key === "ArrowRight")) {
                prefs.dim = Math.max(0, Math.min(70, prefs.dim + (key === "ArrowLeft" ? -5 : 5)));
                save();
                applyBackground();
                renderSettings("dim");
                return;
            }
            if (modal === "settings" && settingsPage === "organize" && b.closest(".manage-row")) {
                var row = b.closest(".manage-row"), rows = Array.from(content.querySelectorAll(".manage-row")), cells = Array.from(row.querySelectorAll("button")), col = cells.indexOf(b), r = rows.indexOf(row), dest;
                if (key === "ArrowLeft" || key === "ArrowRight") {
                    dest = cells[col + (key === "ArrowRight" ? 1 : -1)];
                    if (dest && !dest.disabled) focus(dest);
                    return;
                }
                var next = rows[r + (key === "ArrowDown" ? 1 : -1)];
                if (next) {
                    var options = Array.from(next.querySelectorAll("button"));
                    dest = options[col];
                    if (!dest || dest.disabled) dest = options.find(function(x) {
                        return !x.disabled;
                    });
                    focus(dest);
                } else if (key === "ArrowDown") focus(content.querySelector("[data-setting=reset]"));
                return;
            }
            var i = buttons.indexOf(b), step = key === "ArrowDown" || key === "ArrowRight" ? 1 : -1;
            focus(buttons[Math.max(0, Math.min(buttons.length - 1, i + step))]);
            return;
        }
        var row = groups[1].indexOf(document.activeElement) >= 0 ? 1 : 0, list = groups[row], i = list.indexOf(document.activeElement);
        if (key === "ArrowDown") {
            focus(groups[1][0]);
            return;
        }
        if (key === "ArrowUp") {
            restore();
            return;
        }
        focus(list[Math.max(0, Math.min(list.length - 1, i + (key === "ArrowRight" ? 1 : -1)))]);
    });
    function clock() {
        if (document.hidden) return;
        var now = new Date;
        document.getElementById("date").textContent = now.toLocaleDateString(config.locale || "fr-FR", {
            weekday: "long",
            day: "numeric",
            month: "long"
        });
        document.getElementById("clock").textContent = now.toLocaleTimeString(config.locale || "fr-FR", {
            hour: "2-digit",
            minute: "2-digit"
        });
    }
    function resume() {
        document.body.classList.remove("backgrounded");
        clearInterval(clockTimer);
        clock();
        clockTimer = setInterval(clock, 15e3);
        if (modal === "feedback") {
            launchToken++;
            busy = false;
            feedback.hidden = true;
            shade.hidden = true;
            panel.hidden = true;
            modal = null;
            returnSettings = null;
        }
        if (!modal) restore();
    }
    document.addEventListener("visibilitychange", function() {
        if (document.hidden) {
            document.body.classList.add("backgrounded");
            clearInterval(clockTimer);
            clockTimer = null;
            save();
            launchToken++;
            busy = false;
        } else resume();
    });
    addEventListener("webOSRelaunch", resume);
    addEventListener("pagehide", save);
    addEventListener("error", function(e) {
        record("error", {
            message: e.message
        });
    });
    document.getElementById("selected-title").textContent = config.title || "Mon accueil";
    applyBackground();
    renderHome(false);
    restore();
    resume();
    if (config.discoverInputs) {
        call("luna://com.webos.service.eim/getAllInputStatus", {}, function(result) {
            if (result.returnValue && Array.isArray(result.devices)) {
                inputs = result.devices.filter(function(a) {
                    return /^HDMI_/.test(a.id) && typeof a.appId === "string";
                }).map(function(a) {
                    return {
                        id: a.appId,
                        name: a.label || a.id
                    };
                });
                renderHome(false);
                if (!modal) restore();
            } else record("inputs_unavailable");
        });
    }
    record("ready", {
        version: "0.2.0",
        apps: apps.length
    });
})();
