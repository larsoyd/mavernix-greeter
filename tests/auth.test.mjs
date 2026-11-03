import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const src = readFileSync(new URL("../src/greeter/Auth.js", import.meta.url), "utf8");
const { initial, step } = new Function(src + "\nreturn { initial, step };")();

const SESSION = { id: "mavernix", cmd: ["/usr/bin/start"], env: ["XDG_SESSION_TYPE=wayland"] };

function run(state, ...events) {
  let effects = [];
  for (const e of events) {
    const r = step(state, e);
    state = r.state;
    effects = effects.concat(r.effects);
  }
  return { state, effects };
}

const ops = (effects) => effects.map((e) => e.do);
const ready = () => run(initial(true), { type: "session", ...SESSION }, { type: "select", user: "ada" }).state;
const prompted = () => run(ready(), { type: "message", text: "Password: ", error: false, required: true, echo: false }).state;

test("selecting a user creates a session", () => {
  const r = run(initial(true), { type: "session", ...SESSION }, { type: "select", user: "ada" });
  assert.equal(r.state.phase, "starting");
  assert.deepEqual(r.effects, [{ do: "create", user: "ada" }]);
});

test("unavailable greetd refuses to start", () => {
  const r = run(initial(false), { type: "select", user: "ada" });
  assert.equal(r.state.phase, "unavailable");
  assert.deepEqual(r.effects, []);
});

test("secret prompt asks for hidden input", () => {
  const s = prompted();
  assert.equal(s.phase, "prompt");
  assert.equal(s.echo, false);
  assert.equal(s.prompt, "Password: ");
});

test("submit responds once, clears the field and keeps nothing", () => {
  const r = run(prompted(), { type: "submit", value: "hunter2" });
  assert.equal(r.state.phase, "verifying");
  assert.deepEqual(r.effects, [{ do: "respond", value: "hunter2" }, { do: "clear" }]);
  assert.ok(!JSON.stringify(r.state).includes("hunter2"));
});

test("submit outside a prompt does nothing", () => {
  for (const s of [ready(), initial(true), run(prompted(), { type: "submit", value: "x" }).state]) {
    assert.deepEqual(step(s, { type: "submit", value: "x" }).effects, []);
  }
});

test("info and error messages are shown without a prompt", () => {
  const r = run(ready(), { type: "message", text: "Please touch the device.", error: false, required: false, echo: false });
  assert.equal(r.state.phase, "info");
  assert.deepEqual(r.state.notes, [{ text: "Please touch the device.", error: false }]);
  const e = run(r.state, { type: "message", text: "Account expires soon", error: true, required: false, echo: false });
  assert.deepEqual(e.state.notes.map((n) => n.error), [false, true]);
  assert.deepEqual(e.effects, []);
});

test("sequential prompts each get their own response", () => {
  const r = run(prompted(), { type: "submit", value: "old" },
    { type: "message", text: "New password: ", error: false, required: true, echo: false },
    { type: "submit", value: "new" },
    { type: "message", text: "Code: ", error: false, required: true, echo: true },
    { type: "submit", value: "123" });
  assert.deepEqual(r.effects.filter((e) => e.do === "respond").map((e) => e.value), ["old", "new", "123"]);
  assert.equal(r.state.phase, "verifying");
});

test("visible prompt echoes", () => {
  const r = run(ready(), { type: "message", text: "Login: ", error: false, required: true, echo: true });
  assert.equal(r.state.echo, true);
});

test("notes are cleared by a new prompt round and capped", () => {
  let s = ready();
  for (let i = 0; i < 20; i++) s = run(s, { type: "message", text: "n" + i, error: false, required: false, echo: false }).state;
  assert.ok(s.notes.length <= 4);
  assert.equal(s.notes.at(-1).text, "n19");
});

test("failure shakes, clears and only retries after the shake", () => {
  const r = run(prompted(), { type: "submit", value: "bad" }, { type: "failure", text: "pam_authenticate failed" });
  assert.equal(r.state.phase, "failed");
  assert.equal(r.state.tries, 1);
  assert.ok(!ops(r.effects).includes("create") || ops(r.effects).lastIndexOf("create") === 0);
  assert.deepEqual(ops(r.effects).slice(-2), ["shake", "clear"]);
  const again = run(r.state, { type: "inactive" }, { type: "shaken" });
  assert.equal(again.state.phase, "starting");
  assert.deepEqual(again.effects, [{ do: "create", user: "ada" }]);
});

test("ready fades out before launching and remembers the choice", () => {
  const r = run(prompted(), { type: "submit", value: "ok" }, { type: "ready" });
  assert.equal(r.state.phase, "leaving");
  assert.deepEqual(ops(r.effects).slice(-2), ["remember", "fade"]);
  assert.ok(!ops(r.effects).includes("launch"));
  const l = run(r.state, { type: "faded" });
  assert.deepEqual(l.effects, [{ do: "launch", cmd: SESSION.cmd, env: SESSION.env }]);
  assert.equal(l.state.phase, "launching");
});

test("passwordless success without any prompt still launches", () => {
  const r = run(ready(), { type: "ready" }, { type: "faded" });
  assert.equal(r.state.phase, "launching");
});

test("faded twice launches once", () => {
  const r = run(prompted(), { type: "submit", value: "ok" }, { type: "ready" }, { type: "faded" }, { type: "faded" });
  assert.equal(r.effects.filter((e) => e.do === "launch").length, 1);
});

test("launch failure is recoverable", () => {
  const r = run(prompted(), { type: "submit", value: "ok" }, { type: "ready" }, { type: "faded" },
    { type: "error", text: "exec failed" });
  assert.equal(r.state.phase, "error");
  assert.equal(r.state.problem, "launch");
  assert.deepEqual(ops(r.effects).slice(-1), ["unfade"]);
  const again = run(r.state, { type: "retry" });
  assert.deepEqual(again.effects, [{ do: "create", user: "ada" }]);
});

test("losing greetd mid conversation is an error, not a silent stop", () => {
  const r = run(prompted(), { type: "inactive" });
  assert.equal(r.state.phase, "error");
  assert.equal(r.state.problem, "lost");
});

test("inactive after cancel or failure is expected", () => {
  assert.equal(run(prompted(), { type: "cancel" }, { type: "inactive" }).state.phase, "pick");
  assert.equal(run(prompted(), { type: "failure", text: "x" }, { type: "inactive" }).state.phase, "failed");
});

test("cancel goes back to the user list", () => {
  const r = run(prompted(), { type: "cancel" });
  assert.equal(r.state.phase, "pick");
  assert.deepEqual(ops(r.effects), ["cancel", "clear"]);
});

test("switching user cancels the old conversation first", () => {
  const r = run(prompted(), { type: "select", user: "bob" });
  assert.deepEqual(r.effects, [{ do: "cancel" }, { do: "clear" }, { do: "create", user: "bob" }]);
  assert.equal(r.state.user, "bob");
});

test("late events from a cancelled conversation are ignored", () => {
  const r = run(prompted(), { type: "cancel" }, { type: "ready" }, { type: "faded" });
  assert.ok(!ops(r.effects).includes("launch"));
  assert.equal(r.state.phase, "pick");
});

test("no launch without a session", () => {
  const r = run(initial(true), { type: "select", user: "ada" }, { type: "ready" }, { type: "faded" });
  assert.equal(r.state.phase, "error");
  assert.equal(r.state.problem, "no_session");
  assert.ok(!ops(r.effects).includes("launch"));
});

test("session can change until leaving", () => {
  const other = { type: "session", id: "wayfire", cmd: ["wayfire"], env: [] };
  const r = run(prompted(), other, { type: "submit", value: "ok" }, { type: "ready" }, { type: "faded" });
  assert.deepEqual(r.effects.find((e) => e.do === "launch").cmd, ["wayfire"]);
  assert.equal(r.effects.find((e) => e.do === "remember").session, "wayfire");
});

test("service error while authenticating can be retried", () => {
  const r = run(prompted(), { type: "error", text: "boom" });
  assert.equal(r.state.problem, "service");
  assert.deepEqual(run(r.state, { type: "retry" }).effects, [{ do: "create", user: "ada" }]);
});

test("unknown events change nothing", () => {
  const s = prompted();
  const r = step(s, { type: "bogus" });
  assert.deepEqual(r.state, s);
  assert.deepEqual(r.effects, []);
});

test("session change while leaving is ignored", () => {
  const r = run(prompted(), { type: "submit", value: "ok" }, { type: "ready" },
    { type: "session", id: "x", cmd: ["x"], env: [] }, { type: "faded" });
  assert.deepEqual(r.effects.find((e) => e.do === "launch").cmd, SESSION.cmd);
});

test("picking a user after a failure cancels the old conversation", () => {
  const r = run(prompted(), { type: "failure", text: "x" }, { type: "select", user: "bob" });
  assert.deepEqual(r.effects.slice(-3), [{ do: "cancel" }, { do: "clear" }, { do: "create", user: "bob" }]);
});

test("stray shake, retry, launched and cancel events do nothing", () => {
  for (const type of ["shaken", "retry", "launched"]) {
    const s = prompted();
    assert.deepEqual(step(s, { type }).effects, [], type);
    assert.equal(step(s, { type }).state.phase, "prompt", type);
  }
  assert.deepEqual(step(initial(true), { type: "cancel" }).effects, []);
});

test("a submit clears old notes", () => {
  const r = run(ready(), { type: "message", text: "hint", error: false, required: false, echo: false },
    { type: "message", text: "Password: ", error: false, required: true, echo: false },
    { type: "submit", value: "x" });
  assert.deepEqual(r.state.notes, []);
});
