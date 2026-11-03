// greeter theme snapshot: neutral defaults, a checked merge and colour conversion

var SCHEMA = "mavenix-greeter.theme";
var VERSION = 1;
var ASSET = /^[A-Za-z0-9_][A-Za-z0-9_.-]*(\/[A-Za-z0-9_][A-Za-z0-9_.-]*)*$/;
var RANGES = {
    "avatar.size": [16, 512], "field.width": [60, 800], "field.height": [12, 80], "field.radius": [0, 40],
    "fonts.name_size": [6, 72], "fonts.field_size": [6, 72], "fonts.label_size": [6, 72],
    "layout.center_y": [0.1, 0.9], "layout.spacing": [0, 200], "layout.grid_gap": [0, 400],
    "animation.fade_ms": [0, 2000], "animation.shake.swing_ms": [10, 500]
};

function defaults() {
    return {
        schema: SCHEMA, version: VERSION, id: "neutral", name: "Neutral",
        background: { color: "#454c58ff", color2: "#1f2329ff", image: "", fit: "cover", veil: "#00000000" },
        fonts: { family: "sans-serif", name_size: 15, name_bold: true, field_size: 13, label_size: 12 },
        colors: { text: "#ffffffff", text_shadow: "#00000099", field: "#ffffffff", field_border: "#00000040",
                  field_text: "#000000ff", placeholder: "#8c8c8cff", focus: "#7aa7d8ff", error: "#ffc4c4ff",
                  button: "#ffffffe0", button_back: "#00000040" },
        avatar: { size: 128, ring: "#ffffff59", shadow: "#00000080" },
        field: { width: 220, height: 28, radius: 14 },
        layout: { center_y: 0.5, spacing: 18, grid_gap: 34 },
        animation: { fade_ms: 450, shake: { swings: [-14, 14, -14, 8, -8, 6], swing_ms: 67 } },
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
