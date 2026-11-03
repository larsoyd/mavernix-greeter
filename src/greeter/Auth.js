// greetd talk as a pure reducer, step gives the next state and the effects to run

var MAX_NOTES = 4;
var TALKING = ["starting", "prompt", "info", "verifying"];

function initial(available) {
    return { phase: available ? "pick" : "unavailable", user: "", session: null, prompt: "",
             echo: false, notes: [], tries: 0, problem: "" };
}

function with_(state, changes) {
    return Object.assign({}, state, changes);
}

function start(state, user) {
    return { state: with_(state, { phase: "starting", user: user, prompt: "", notes: [], problem: "" }),
             effects: [{ do: "create", user: user }] };
}

function talking(state) {
    return TALKING.indexOf(state.phase) >= 0;
}

function step(state, e) {
    var none = { state: state, effects: [] };
    switch (e.type) {
    case "session":
        if (state.phase === "leaving" || state.phase === "launching")
            return none;
        return { state: with_(state, { session: { id: e.id, cmd: e.cmd, env: e.env } }), effects: [] };
    case "select":
        if (state.phase === "unavailable" || state.phase === "leaving" || state.phase === "launching")
            return none;
        if (talking(state) || state.phase === "failed") {
            var next = start(state, e.user);
            next.effects = [{ do: "cancel" }, { do: "clear" }].concat(next.effects);
            return next;
        }
        return start(state, e.user);
    case "message":
        if (!talking(state))
            return none;
        if (e.required)
            return { state: with_(state, { phase: "prompt", prompt: e.text, echo: !!e.echo }), effects: [] };
        var notes = state.notes.concat([{ text: e.text, error: !!e.error }]).slice(-MAX_NOTES);
        return { state: with_(state, { phase: "info", notes: notes }), effects: [] };
    case "submit":
        if (state.phase !== "prompt")
            return none;
        return { state: with_(state, { phase: "verifying", notes: [] }),
                 effects: [{ do: "respond", value: e.value }, { do: "clear" }] };
    case "failure":
        if (!talking(state))
            return none;
        return { state: with_(state, { phase: "failed", tries: state.tries + 1, prompt: "" }),
                 effects: [{ do: "shake" }, { do: "clear" }] };
    case "shaken":
        return state.phase === "failed" ? start(state, state.user) : none;
    case "ready":
        if (!talking(state))
            return none;
        if (!state.session)
            return { state: with_(state, { phase: "error", problem: "no_session" }), effects: [{ do: "cancel" }] };
        return { state: with_(state, { phase: "leaving" }),
                 effects: [{ do: "remember", user: state.user, session: state.session.id }, { do: "fade" }] };
    case "faded":
        if (state.phase !== "leaving")
            return none;
        return { state: with_(state, { phase: "launching" }),
                 effects: [{ do: "launch", cmd: state.session.cmd, env: state.session.env }] };
    case "launched":
        return state.phase === "launching" ? { state: with_(state, { phase: "launched" }), effects: [] } : none;
    case "error":
        if (state.phase === "launching")
            return { state: with_(state, { phase: "error", problem: "launch" }), effects: [{ do: "unfade" }] };
        if (!talking(state))
            return none;
        return { state: with_(state, { phase: "error", problem: "service" }), effects: [] };
    case "inactive":
        if (!talking(state))
            return none;
        return { state: with_(state, { phase: "error", problem: "lost" }), effects: [] };
    case "retry":
        return state.phase === "error" && state.user ? start(state, state.user) : none;
    case "cancel":
        if (!talking(state) && state.phase !== "failed" && state.phase !== "error")
            return none;
        return { state: with_(state, { phase: "pick", prompt: "", notes: [], problem: "" }),
                 effects: [{ do: "cancel" }, { do: "clear" }] };
    }
    return none;
}
