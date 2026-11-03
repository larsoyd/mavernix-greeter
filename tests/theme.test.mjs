import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src = readFileSync(new URL("../src/greeter/Theme.js", import.meta.url), "utf8");
const T = new Function(src + "\nreturn { defaults, merge, color, load, SCHEMA, VERSION };")();

test("colours are rrggbbaa and become qt aarrggbb", () => {
  assert.equal(T.color("#11223344"), "#44112233");
  assert.equal(T.color("#112233"), "#112233");
  assert.equal(T.color("red"), null);
  assert.equal(T.color("#12345"), null);
  assert.equal(T.color(7), null);
});

test("merge keeps defaults for missing and mistyped keys", () => {
  const d = { a: 1, b: { c: "x", d: [1, 2] }, e: true };
  assert.deepEqual(T.merge(d, { a: 2, b: { c: 3, d: [5] }, e: "no", z: 9 }), { a: 2, b: { c: "x", d: [5] }, e: true });
});

test("merge refuses arrays where objects belong and vice versa", () => {
  const d = { b: { c: 1 }, l: [1] };
  assert.deepEqual(T.merge(d, { b: [1], l: { x: 1 } }), d);
});

test("merge does not change the defaults object", () => {
  const d = T.defaults();
  T.merge(d, { avatar: { size: 3 } });
  assert.notEqual(d.avatar.size, 3);
});

test("load accepts the current schema only", () => {
  const ok = { schema: T.SCHEMA, version: T.VERSION, id: "x", avatar: { size: 100 } };
  assert.equal(T.load(JSON.stringify(ok)).theme.avatar.size, 100);
  for (const bad of [{ ...ok, schema: "other" }, { ...ok, version: T.VERSION + 1 }, { ...ok, version: "1" }]) {
    const r = T.load(JSON.stringify(bad));
    assert.equal(r.theme.id, "neutral");
    assert.match(r.problem, /schema|version/);
  }
});

test("older versions are read with defaults filling the gaps", () => {
  const r = T.load(JSON.stringify({ schema: T.SCHEMA, version: 1, id: "old" }));
  assert.equal(r.theme.id, "old");
  assert.equal(r.problem, "");
});

test("broken json falls back to the neutral theme with a reason", () => {
  for (const text of ["{", "", "[]", "null"]) {
    const r = T.load(text);
    assert.equal(r.theme.id, "neutral");
    assert.notEqual(r.problem, "");
  }
});

test("colour strings in a loaded theme are checked", () => {
  const r = T.load(JSON.stringify({ schema: T.SCHEMA, version: T.VERSION, colors: { text: "javascript:1" } }));
  assert.equal(r.theme.colors.text, T.defaults().colors.text);
});

test("asset paths must stay inside the theme folder", () => {
  const r = T.load(JSON.stringify({ schema: T.SCHEMA, version: T.VERSION,
    background: { image: "../../etc/shadow" }, accounts: { a: { avatar: "/etc/x" }, b: { avatar: "people/b.png" } } }));
  assert.equal(r.theme.background.image, "");
  assert.equal(r.theme.accounts.a, undefined);
  assert.equal(r.theme.accounts.b.avatar, "people/b.png");
});

test("numbers are clamped to sane ranges", () => {
  const r = T.load(JSON.stringify({ schema: T.SCHEMA, version: T.VERSION, avatar: { size: 100000 },
    animation: { fade_ms: -5, shake: { swings: [1e9, 3], swing_ms: 0 } } }));
  assert.ok(r.theme.avatar.size <= 512);
  assert.ok(r.theme.animation.fade_ms >= 0);
  assert.deepEqual(r.theme.animation.shake.swings, [200, 3]);
  assert.ok(r.theme.animation.shake.swing_ms >= 10);
});
