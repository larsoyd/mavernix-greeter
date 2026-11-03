// greeter theme snapshot: neutral defaults, a checked merge and colour conversion

var SCHEMA = "mavernix-greeter.theme";
var VERSION = 1;
var ASSET = /^[A-Za-z0-9_][A-Za-z0-9_.-]*(\/[A-Za-z0-9_][A-Za-z0-9_.-]*)*$/;
var RANGES = {
    "background.center_y": [0, 1], "background.radius_x": [0.1, 3], "background.radius_y": [0.1, 3],
    "fonts.size": [6, 72], "fonts.label_size": [6, 72], "fonts.field_size": [6, 72], "fonts.clock_size": [6, 72], "name.blur": [0, 16], "name.shadow_y": [-8, 8],
    "avatar.size": [16, 512], "tile.width": [60, 600], "tile.height": [60, 600],
    "field.width": [60, 800], "field.height": [12, 80], "field.radius": [0, 40],
    "layout.tile_top": [-400, 400], "layout.field_bottom": [-400, 600], "layout.bar_bottom": [0, 400],
    "layout.bar_gap": [0, 200], "animation.select_ms": [0, 3000], "animation.fade_ms": [0, 3000],
    "animation.shake.amplitude": [0, 200], "animation.shake.duration_ms": [0, 3000],
    "animation.shake.cycles": [0, 20], "animation.shake.damping": [0, 20], "animation.shake.swing_ms": [10, 500]
};

function defaults() {
    return {
        schema: SCHEMA, version: VERSION, id: "neutral", name: "Neutral",
        background: { color: "#51535bff", color2: "#2d2d32ff", center_y: 0.382, radius_x: 0.6, radius_y: 0.688,
                      image: "", fit: "cover", veil: "#00000000" },
        fonts: { family: "sans-serif", size: 15, label_size: 14, field_size: 14, clock_size: 15 },
        name: { shadow_y: 1, blur: 2, bold: false },
        colors: { text: "#ffffffff", text_shadow: "#000000a3", clock: "#ffffff8c", label: "#ffffff8c", label_pressed: "#f0f0f0ff",
                  label_shadow: "#00000066", field: "#ffffffff", field_top: "#eaeaeaff", field_border: "#00000033",
                  field_text: "#000000ff", placeholder: "#808080ff", focus: "#4a95e4ff", focus2: "#3c8cdcff",
                  error: "#e0443eff", button_back: "#00000059", message: "#ffffff8c" },
        avatar: { size: 84, rim_outer: "#00000017", rim_inner: "#ffffff40", pressed: "#00000054",
                  other_top: "#9aaac0ff", other_bottom: "#5f6f88ff" },
        tile: { width: 178, height: 146 },
        field: { width: 164, height: 30, radius: 6 },
        layout: { tile_top: -41, field_bottom: 132, bar_bottom: 35, bar_gap: 20 },
        animation: { select_ms: 500, fade_ms: 250,
                     shake: { kind: "sine", amplitude: 14, duration_ms: 400, cycles: 3, damping: 0.8,
                              swings: [-14, 14, -14, 8, -8, 6], swing_ms: 67 } },
        accounts: {}
    };
}

function kind(v) {
    return Array.isArray(v) ? "array" : v === null ? "null" : typeof v;
}

function merge(base, over) {
    var out = {};
    for (var k in base) {
        var b = base[k], o = over ? over[k] : undefined;
        if (kind(b) === "object")
            out[k] = merge(b, o || {});
        else if (o !== undefined && kind(o) === kind(b))
            out[k] = o;
        else
            out[k] = b;
    }
    return out;
}

function color(c) {
    if (typeof c !== "string" || !/^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.test(c))
        return null;
    return c.length === 9 ? "#" + c.slice(7) + c.slice(1, 7) : c;
}

function asset(p) {
    return typeof p === "string" && ASSET.test(p);
}

function clamp(theme) {
    for (var key in RANGES) {
        var parts = key.split("."), obj = theme;
        for (var i = 0; i < parts.length - 1; i++)
            obj = obj[parts[i]];
        var last = parts[parts.length - 1], r = RANGES[key];
        obj[last] = Math.min(r[1], Math.max(r[0], obj[last]));
    }
    var sh = theme.animation.shake;
    sh.swings = sh.swings.filter(function (n) { return typeof n === "number" && isFinite(n); })
        .slice(0, 16).map(function (n) { return Math.max(-200, Math.min(200, n)); });
}

function checkColors(theme, base) {
    for (var group of ["colors", "background", "avatar"]) {
        for (var k in theme[group]) {
            var d = base[group][k];
            if (typeof d === "string" && d[0] === "#" && color(theme[group][k]) === null)
                theme[group][k] = d;
        }
    }
}

function accounts(raw) {
    var out = {};
    if (kind(raw) !== "object")
        return out;
    for (var name in raw) {
        var a = raw[name];
        if (/^[A-Za-z0-9_][A-Za-z0-9_.@-]{0,63}$/.test(name) && kind(a) === "object" && asset(a.avatar))
            out[name] = { avatar: a.avatar };
    }
    return out;
}

function load(text) {
    var base = defaults(), raw;
    try {
        raw = JSON.parse(text);
    } catch (e) {
        return { theme: base, problem: "unreadable" };
    }
    if (kind(raw) !== "object")
        return { theme: base, problem: "not_an_object" };
    if (raw.schema !== SCHEMA)
        return { theme: base, problem: "schema" };
    if (typeof raw.version !== "number" || raw.version < 1 || raw.version > VERSION)
        return { theme: base, problem: "version" };
    var theme = merge(base, raw);
    theme.accounts = accounts(raw.accounts);
    if (theme.background.image && !asset(theme.background.image))
        theme.background.image = "";
    checkColors(theme, base);
    clamp(theme);
    return { theme: theme, problem: "" };
}
