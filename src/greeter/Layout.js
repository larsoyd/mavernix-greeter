// pure geometry and motion helpers for the login screen

function shakeX(shake, p) {
    if (p <= 0 || p >= 1)
        return 0;
    if (shake.kind === "sine") {
        var damp = p < 0.5 ? 1 : Math.exp(-shake.damping * p);
        return shake.amplitude * Math.sin(2 * Math.PI * shake.cycles * p) * damp;
    }
    var sw = [0].concat(shake.swings || []);
    var n = sw.length - 1;
    if (n < 1)
        return 0;
    var k = Math.floor(p * n), f = p * n - k;
    return sw[k] + (sw[Math.min(n, k + 1)] - sw[k]) * f;
}

function perPage(width, tileWidth) {
    var rule = width > 1536 ? 8 : width > 1180 ? 6 : 4;
    return Math.max(1, Math.min(rule, Math.floor((width - 32) / (tileWidth || 178))));
}

function page(count, index, per) {
    var first = Math.floor(index / per) * per;
    return { first: first, count: Math.min(per, count - first), pages: Math.ceil(count / per) };
}

var GAP = 6;

function rect(x, y, w, h) {
    return { x: Math.round(x), y: Math.round(y), w: Math.round(w), h: Math.round(h) };
}

// every element's rectangle for a screen of w by h, the screens own data come from s
function boxes(w, h, theme, s) {
    var t = theme.tile, cy = Math.round(h / 2), line = s.line || 16;
    var out = {};
    out.clock = rect(w - 18 - s.clockWidth, 0, s.clockWidth, 22);
    var barX = s.barLead !== undefined ? w / 2 - s.barLead : (w - s.barWidth) / 2;
    out.bar = rect(barX, h - theme.layout.bar_bottom - s.barHeight, s.barWidth, s.barHeight);
    var entries = (s.users || 0) + (s.other ? 1 : 0);
    var count = s.chosen ? 1 : Math.max(1, Math.min(perPage(w, t.width), entries));
    var top = cy + theme.layout.tile_top;
    var picture = Math.round((92 - theme.avatar.size) / 2);
    var parts = s.chosen ? [] : [["row", 0, 0, count * t.width, t.height]];
    if (s.chosen) {
        var fieldTop = theme.layout.field_bottom - theme.layout.tile_top - theme.field.height;
        parts.push(["avatar", (t.width - theme.avatar.size) / 2, picture, theme.avatar.size, theme.avatar.size]);
        parts.push(["name", (t.width - 140) / 2, 97, 140, (s.nameLines || 1) * line]);
        parts.push(["field", (t.width - theme.field.width) / 2, fieldTop, theme.field.width, theme.field.height]);
        var below = fieldTop + theme.field.height;
        if (s.messageLines) {
            parts.push(["message", (t.width - 360) / 2, below + 14, 360, s.messageLines * line]);
            below += 14 + s.messageLines * line;
        }
        if (s.sessions > 1) {
            parts.push(["session", (t.width - s.sessionWidth) / 2, Math.max(below + 14, fieldTop + theme.field.height + 46),
                        s.sessionWidth, line + 4]);
        }
    }
    var bottom = Math.max.apply(null, parts.map(function (p) { return p[2] + p[4]; }));
    var lowest = out.bar.y - 2 * GAP;
    var shift = Math.min(0, lowest - (top + bottom));
    var left = Math.round((w - count * t.width) / 2);
    var stackLeft = Math.round((w - t.width) / 2);
    parts.forEach(function (p) {
        var x0 = p[0] === "row" ? left : stackLeft;
        out[p[0]] = rect(x0 + p[1], top + shift + p[2], p[3], p[4]);
    });
    for (var i = 0; i < count; i++)
        out["tile" + i] = rect(left + i * t.width, top + shift, t.width, t.height);
    return out;
}
