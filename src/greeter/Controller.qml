pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "Auth.js" as Auth
import "Theme.js" as Theme

Singleton {
    id: root

    readonly property string helper: Quickshell.env("MAVERNIX_GREETER_HELPER") || "/usr/lib/mavernix-greeter/helper"
    readonly property string themeDir: Quickshell.env("MAVERNIX_GREETER_THEME_DIR") || "/usr/share/mavernix-greeter/themes/neutral"
    readonly property int watchdogMs: Number(Quickshell.env("MAVERNIX_GREETER_WATCHDOG_MS")) || 30000

    readonly property bool hasService: (Quickshell.env("GREETD_SOCK") ?? "") !== ""
    property var auth: Auth.initial(hasService)
    property var theme: Theme.defaults()
    property bool themeReady: false
    property var users: []
    property bool showList: true
    property var sessions: []
    property string sessionId: ""
    property var last: ({})
    property bool usersLoaded: false
    property var power: ({ poweroff: false, reboot: false, suspend: false })
    property string powerProblem: ""
    property bool manual: false
    property bool offerOther: false

    readonly property string phase: auth.phase
    readonly property var currentUser: users.find(u => u.name === auth.user) ?? ({ name: auth.user, full_name: auth.user, avatar: "" })

    signal clearField()
    signal shake()
    signal fadeOut()
    signal fadeIn()

    property var queue: []
    property bool busy: false

    function log(text) {
        console.info("[greeter] " + text)
    }

    function dispatch(event) {
        queue.push(event)
        if (busy)
            return
        busy = true
        while (queue.length) {
            const e = queue.shift()
            const before = auth.phase
            const r = Auth.step(auth, e)
            auth = r.state
            if (auth.phase !== before)
                log(`phase=${auth.phase} from=${before} event=${e.type}` + (auth.problem ? ` problem=${auth.problem}` : ""))
            r.effects.forEach(run)
        }
        busy = false
        // only an answer the service owes can be late, a person may take as long as they like
        if (["starting", "verifying"].includes(auth.phase))
            watchdog.restart()
        else
            watchdog.stop()
    }

    function run(effect) {
        switch (effect.do) {
        case "create": tell({ op: "create", user: effect.user }); break
        case "respond": tell({ op: "respond", value: effect.value }); break
        case "cancel": tell({ op: "cancel" }); break
        case "clear": clearField(); break
        case "shake": shake(); break
        case "fade": fadeOut(); break
        case "unfade": fadeIn(); break
        case "launch":
            log(`launch session=${sessionId}`)
            tell({ op: "start", cmd: effect.cmd, env: effect.env })
            break
        case "remember": helperRun(["remember", effect.user, effect.session]); break
        case "retry_later":
            retryTimer.interval = Auth.retryDelay(effect.attempt)
            log(`retry attempt=${effect.attempt} in_ms=${retryTimer.interval}`)
            retryTimer.restart()
            break
        }
    }

    function markShown() {
        log("shown")
        if (statusFile.path && phase !== "launched")
            statusFile.setText("shown\n")
    }

    function selectUser(name) {
        manual = false
        dispatch({ type: "select", user: name })
    }

    function back() {
        manual = false
        dispatch({ type: "cancel" })
    }

    function avatarFor(user) {
        const own = theme.accounts[user.name]
        return own ? themeDir + "/" + own.avatar : (user.avatar || "")
    }

    function chooseSession(id) {
        const s = sessions.find(x => x.id === id)
        if (!s)
            return
        sessionId = id
        dispatch({ type: "session", id: s.id, cmd: s.cmd, env: s.env })
    }

    function submit(text) {
        dispatch({ type: "submit", value: text })
    }

    function powerAction(action) {
        log(`power action=${action}`)
        powerProblem = ""
        powerProc.action = action
        powerProc.running = true
    }

    function helperRun(args) {
        const p = oneShot.createObject(root, { command: [helper].concat(args) })
        p.running = true
    }

    Component {
        id: oneShot
        Process {
            onExited: code => {
                if (code !== 0)
                    root.log(`helper cmd=${command[1]} rc=${code}`)
                destroy()
            }
        }
    }

    Process {
        id: powerProc
        property string action: ""
        command: [root.helper, "power", action]
        onExited: code => {
            if (code !== 0)
                root.powerProblem = action
        }
    }

    Timer {
        interval: root.theme.animation.fade_ms + 3000
        running: root.phase === "leaving"
        onTriggered: {
            root.log("watchdog phase=leaving")
            root.dispatch({ type: "faded" })
        }
    }

    Timer {
        id: retryTimer
        onTriggered: root.dispatch({ type: "retry" })
    }

    Timer {
        id: watchdog
        interval: root.watchdogMs
        onTriggered: {
            root.log(`watchdog phase=${root.phase} waited_ms=${interval}`)
            tell({ op: "cancel" })
            root.dispatch({ type: "inactive" })
        }
    }

    FileView {
        id: statusFile
        path: Quickshell.env("MAVERNIX_GREETER_STATUS") ?? ""
        blockWrites: true
        printErrors: false
    }

    FileView {
        path: root.themeDir + "/theme.json"
        printErrors: false
        onLoaded: {
            const r = Theme.load(text())
            root.theme = r.theme
            root.themeReady = true
            root.log(`theme id=${r.theme.id} problem=${r.problem || "none"}`)
        }
        onLoadFailed: error => {
            root.themeReady = true
            root.log(`theme id=neutral problem=missing error=${error}`)
        }
    }

    Process {
        command: [root.helper, "users"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const r = JSON.parse(text)
                    root.users = r.users
                    root.showList = r.show_list
                    root.offerOther = r.offer_other === true
                    root.last = r.last
                } catch (e) {
                    root.log("users problem=unreadable")
                }
                root.usersLoaded = true
                root.log(`users count=${root.users.length} list=${root.showList}`)
                if (root.users.length === 1 && root.showList)
                    root.selectUser(root.users[0].name)
            }
        }
    }

    Process {
        command: [root.helper, "sessions"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.sessions = JSON.parse(text).sessions
                } catch (e) {
                    root.log("sessions problem=unreadable")
                }
                root.log(`sessions count=${root.sessions.length}`)
                if (!root.sessions.length) {
                    if (statusFile.path)
                        statusFile.setText("no_sessions\n")
                    Qt.quit()
                    return
                }
                const remembered = root.sessions.find(s => s.id === root.last.session)
                if (root.sessions.length)
                    root.chooseSession((remembered ?? root.sessions[0]).id)
            }
        }
    }

    Process {
        command: [root.helper, "power-caps"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.power = JSON.parse(text)
                } catch (e) {
                    root.log("power problem=unreadable")
                }
            }
        }
    }

    property var pending: []
    property bool bridgeUp: false

    function tell(op) {
        if (!bridgeUp) {
            pending.push(op)
            bridge.running = true
            return
        }
        bridge.write(JSON.stringify(op) + "\n")
    }

    function heard(e) {
        switch (e.ev) {
        case "connected":
            bridgeUp = true
            pending.splice(0).forEach(tell)
            break
        case "unavailable":
            log("greetd unavailable")
            if (hasService)
                dispatch({ type: "error", text: "unavailable" })
            else
                auth = Auth.initial(false)
            break
        case "message":
            log(`message kind=${e.kind}`)
            dispatch({ type: "message", text: e.text, error: e.kind === "error",
                       required: e.kind === "visible" || e.kind === "secret", echo: e.kind === "visible" })
            break
        case "failure":
            log("auth result=failure")
            dispatch({ type: "failure", text: e.text })
            break
        case "ready":
            log("auth result=success")
            dispatch({ type: "ready" })
            break
        case "error":
            log(`greetd error stage=${e.stage} text=${JSON.stringify(e.text)}`)
            dispatch({ type: "error", text: e.text })
            break
        case "launched":
            if (statusFile.path)
                statusFile.setText("launched\n")
            dispatch({ type: "launched" })
            Qt.quit()
            break
        case "lost":
            log("greetd connection lost")
            dispatch({ type: "inactive" })
            break
        }
    }

    Process {
        id: bridge
        command: [root.helper, "bridge"]
        running: true
        stdinEnabled: true
        stdout: SplitParser {
            onRead: line => {
                try {
                    root.heard(JSON.parse(line))
                } catch (e) {
                    root.log("bridge problem=unreadable")
                }
            }
        }
        onExited: code => {
            root.bridgeUp = false
            root.pending = []
            if (code !== 0 && root.auth.phase !== "unavailable")
                root.log(`bridge exited rc=${code}`)
        }
    }

    Component.onCompleted: log(`start available=${auth.phase !== "unavailable"}`)
}
