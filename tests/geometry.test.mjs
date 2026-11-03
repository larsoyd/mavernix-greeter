import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const load = (f) => readFileSync(new URL("../src/greeter/" + f, import.meta.url), "utf8");
const T = new Function(load("Theme.js") + "\nreturn { defaults };")();
const L = new Function(load("Layout.js") + "\nreturn { boxes };")();
const GAP = 6;

// logical sizes of the real outputs plus small and odd ones
const SCREENS = [[3440, 1440], [2560, 1440], [1920, 1080], [1280, 720], [1366, 768], [1024, 768], [800, 600], [640, 480], [1080, 1920], [1366, 767]];
const STATES = [
  { chosen: false, users: 1 }, { chosen: false, users: 3 }, { chosen: false, users: 12 },
  { chosen: true, users: 1, messageLines: 0, sessions: 1 }, { chosen: true, users: 4, messageLines: 3, sessions: 3 },
  { chosen: true, users: 1, messageLines: 1, sessions: 2, nameLines: 2 },
];
const text = { line: 17, sessionWidth: 181, barWidth: 263, barHeight: 57, clockWidth: 91 };

function overlap(a, b, gap) {
  return a.x < b.x + b.w + gap && b.x < a.x + a.w + gap && a.y < b.y + b.h + gap && b.y < a.y + a.h + gap;
}

function visible(boxes) {
  return Object.entries(boxes).filter(([, r]) => r && r.w > 0 && r.h > 0);
}

for (const [w, h] of SCREENS) {
  for (const s of STATES) {
    test(`no element meets another at ${w}x${h} ${JSON.stringify(s)}`, () => {
      const b = L.boxes(w, h, T.defaults(), { ...s, ...text });
      const items = visible(b).filter(([n]) => !n.startsWith("tile"));
      const want = ["clock", "bar"].concat(s.chosen ? ["field", "avatar", "name"] : ["row"])
        .concat(s.chosen && s.messageLines ? ["message"] : []).concat(s.chosen && s.sessions > 1 ? ["session"] : []);
      assert.deepEqual(items.map(([n]) => n).filter((n) => want.includes(n)).sort(), want.sort());
      for (let i = 0; i < items.length; i++)
        for (let j = i + 1; j < items.length; j++)
          assert.ok(!overlap(items[i][1], items[j][1], GAP),
            `${items[i][0]} ${JSON.stringify(items[i][1])} meets ${items[j][0]} ${JSON.stringify(items[j][1])}`);
    });

    test(`everything stays on screen at ${w}x${h} ${JSON.stringify(s)}`, () => {
      for (const [n, r] of visible(L.boxes(w, h, T.defaults(), { ...s, ...text }))) {
        assert.ok(r.x >= 0 && r.y >= 0 && r.x + r.w <= w && r.y + r.h <= h, `${n} ${JSON.stringify(r)} leaves ${w}x${h}`);
        for (const k of ["x", "y", "w", "h"]) assert.equal(r[k], Math.round(r[k]), `${n}.${k} not on a whole pixel`);
      }
    });

    test(`tiles do not overlap each other at ${w}x${h} ${JSON.stringify(s)}`, () => {
      const tiles = visible(L.boxes(w, h, T.defaults(), { ...s, ...text })).filter(([n]) => n.startsWith("tile"));
      assert.ok(tiles.length >= 1);
      for (let i = 1; i < tiles.length; i++) assert.ok(!overlap(tiles[i - 1][1], tiles[i][1], -1));
    });
  }
}

test("the researched positions hold where they fit", () => {
  const b = L.boxes(1920, 1080, T.defaults(), { chosen: true, users: 1, messageLines: 0, sessions: 1, ...text });
  assert.equal(b.field.y + b.field.h, 540 + 132);
  assert.equal(b.field.w, 164);
  assert.equal(b.bar.y + b.bar.h, 1080 - 35);
  assert.equal(b.avatar.y, 540 - 41 + 4);
});

test("a long message pushes the session chooser down rather than over it", () => {
  const one = L.boxes(1920, 1080, T.defaults(), { chosen: true, users: 1, messageLines: 1, sessions: 2, ...text });
  const three = L.boxes(1920, 1080, T.defaults(), { chosen: true, users: 1, messageLines: 3, sessions: 2, ...text });
  assert.ok(three.session.y > one.session.y);
});

test("a short screen moves the stack up instead of under the buttons", () => {
  const tall = L.boxes(1920, 1080, T.defaults(), { chosen: true, users: 1, messageLines: 3, sessions: 3, ...text });
  const short = L.boxes(800, 600, T.defaults(), { chosen: true, users: 1, messageLines: 3, sessions: 3, ...text });
  assert.ok(short.field.y + short.field.h < 300 + 132);
  assert.ok(tall.field.y + tall.field.h === 540 + 132);
});
