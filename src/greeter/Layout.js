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

function perPage(width) {
    return width > 1536 ? 8 : width > 1180 ? 6 : 4;
}

function page(count, index, per) {
    var first = Math.floor(index / per) * per;
    return { first: first, count: Math.min(per, count - first), pages: Math.ceil(count / per) };
}
