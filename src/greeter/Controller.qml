pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Greetd
import "Auth.js" as Auth
import "Theme.js" as Theme

Singleton {
    id: root

    readonly property string helper: Quickshell.env("MAVENIX_GREETER_HELPER") || "/usr/lib/mavenix-greeter/helper"
    readonly property string themeDir: Quickshell.env("MAVENIX_GREETER_THEME_DIR") || "/usr/share/mavenix-greeter/themes/neutral"
    readonly property int watchdogMs: Number(Quickshell.env("MAVENIX_GREETER_WATCHDOG_MS")) || 30000

    property var auth: Auth.initial(Greetd.available)
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
        watchdog.restart()
    }

    function run(effect) {
        switch (effect.do) {
        case "create": Greetd.createSession(effect.user); break
        case "respond": Greetd.respond(effect.value); break
        case "cancel": Greetd.cancelSession(); break
        case "clear": clearField(); break
        case "shake": shake(); break
        case "fade": fadeOut(); break
        case "unfade": fadeIn(); break
        case "launch":
            log(`launch session=${sessionId}`)
            Greetd.launch(effect.cmd, effect.env, true)
            break
        case "remember": helperRun(["remember", effect.user, effect.session]); break
        }
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
        id: watchdog
        interval: root.watchdogMs
        running: ["starting", "verifying"].includes(root.phase)
        onTriggered: {
            root.log(`watchdog phase=${root.phase} waited_ms=${interval}`)
            Greetd.cancelSession()
            root.dispatch({ type: "inactive" })
        }
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

    Connections {
        target: Greetd
        function onAuthMessage(message, error, responseRequired, echoResponse) {
            root.log(`message required=${responseRequired} echo=${echoResponse} error=${error}`)
            root.dispatch({ type: "message", text: message, error: error, required: responseRequired, echo: echoResponse })
        }
        function onAuthFailure(message) {
            root.log("auth result=failure")
            root.dispatch({ type: "failure", text: message })
        }
        function onReadyToLaunch() {
            root.log("auth result=success")
            root.dispatch({ type: "ready" })
        }
        function onLaunched() {
            root.dispatch({ type: "launched" })
        }
        function onError(error) {
            root.log(`greetd error=${JSON.stringify(error)}`)
            root.dispatch({ type: "error", text: error })
        }
        function onStateChanged() {
            if (Greetd.state === GreetdState.Inactive)
                root.dispatch({ type: "inactive" })
        }
    }

    Component.onCompleted: log(`start available=${Greetd.available}`)
}
