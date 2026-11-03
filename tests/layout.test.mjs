import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src = readFileSync(new URL("../src/greeter/Layout.js", import.meta.url), "utf8");
const L = new Function(src + "\nreturn { shakeX, perPage, page };")();
const SINE = { kind: "sine", amplitude: 14, duration_ms: 400, cycles: 3, damping: 0.8 };

test("sine shake starts right, peaks at amplitude, damps after half time", () => {
  assert.equal(L.shakeX(SINE, 0), 0);
  assert.ok(Math.abs(L.shakeX(SINE, 1 / 12) - 14) < 1e-9);
  const late = L.shakeX(SINE, 0.75);
  assert.ok(Math.abs(late - 14 * Math.exp(-0.8 * 0.75)) < 1e-9);
  assert.equal(L.shakeX(SINE, 1), 0);
  assert.equal(L.shakeX(SINE, 1.5), 0);
});

test("swing shake steps through swings", () => {
  const sw = { kind: "swings", swings: [-14, 14, 0] };
  assert.equal(L.shakeX(sw, 0), 0);
  assert.equal(L.shakeX(sw, 1 / 3), -14);
  assert.equal(L.shakeX(sw, 2 / 3), 14);
  assert.equal(L.shakeX(sw, 1), 0);
});

test("tiles per page follow the screen width", () => {
  assert.equal(L.perPage(1920), 8);
  assert.equal(L.perPage(1536), 6);
  assert.equal(L.perPage(1181), 6);
  assert.equal(L.perPage(1180), 4);
  assert.equal(L.perPage(800), 4);
});

test("page of an index", () => {
  assert.deepEqual(L.page(10, 3, 4), { first: 0, count: 4, pages: 3 });
  assert.deepEqual(L.page(10, 9, 4), { first: 8, count: 2, pages: 3 });
  assert.deepEqual(L.page(2, 1, 8), { first: 0, count: 2, pages: 1 });
});
