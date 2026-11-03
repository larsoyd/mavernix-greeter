import QtQuick
import "Theme.js" as Theme
import "Layout.js" as Layout

FocusScope {
    id: stage

    readonly property var theme: Controller.theme
    readonly property real cy: height / 2
    readonly property var entries: Controller.users.concat(Controller.offerOther ? [{ name: "", full_name: qsTr("Other…"), avatar: "" }] : [])
    readonly property bool listing: Controller.showList && Controller.users.length > 0
    readonly property bool chosen: Controller.manual || Controller.phase !== "pick" && Controller.phase !== "unavailable"
                                   || !listing
    readonly property int chosenIndex: Controller.manual || !listing ? Math.max(0, entries.length - 1)
                                       : Math.max(0, entries.findIndex(u => u.name === Controller.auth.user))
    property int current: Math.max(0, Controller.users.findIndex(u => u.name === Controller.last.user))
    readonly property int per: Layout.perPage(width, theme.tile.width)
    readonly property var pg: Layout.page(entries.length, chosen ? chosenIndex : current, per)
    readonly property real tileW: theme.tile.width
    readonly property real rowX: Math.round((width - pg.count * tileW) / 2)
    readonly property real slide: chosen ? Math.round(width / 2 - (rowX + (chosenIndex - pg.first + 0.5) * tileW)) : 0
    property real shakeP: 0
    property bool settled: false
    readonly property var measured: ({
        line: Math.ceil(probe.implicitHeight), users: Controller.users.length,
        messageLines: messageText.visible ? messageText.lineCount : 0, sessions: Controller.sessions.length,
        nameLines: Math.min(2, nameProbe.lineCount), sessionWidth: Math.ceil(chooser.width),
        barWidth: Math.ceil(bar.implicitWidth), barHeight: Math.ceil(bar.implicitHeight), barLead: bar.lead,
        clockWidth: Math.ceil(clock.implicitWidth), other: Controller.offerOther
    })
    readonly property var box: Layout.boxes(width, height, theme, Object.assign({ chosen: chosen }, measured))
    readonly property var chosenBox: Layout.boxes(width, height, theme, Object.assign({ chosen: true }, measured))

    function rectOf(item) {
        const p = item.mapToItem(stage, 0, 0)
        return [Math.round(p.x), Math.round(p.y), Math.round(item.width), Math.round(item.height)].join(",")
    }

    function logLayout() {
        const parts = [`screen=${width}x${height}`, `clock=${rectOf(clock)}`, `bar=${rectOf(bar)}`]
        if (chosen) {
            parts.push(`name=${rectOf(chosenTile ? chosenTile.nameItem : row)}`, `field=${rectOf(entry)}`)
            if (messageText.visible) parts.push(`message=${rectOf(messageText)}`)
            if (chooser.visible) parts.push(`session=${rectOf(chooser)}`)
        } else {
            parts.push(`row=${rectOf(row)}`)
        }
        console.info(`[greeter] layout ${parts.join(" ")}`)
    }

    property var chosenTile: null

    Timer {
        id: layoutLog
        interval: stage.theme.animation.select_ms + 150
        onTriggered: stage.logLayout()
    }
    onChosenChanged: if (!layoutLog.running) layoutLog.start()

    Connections {
        target: Controller
        function onPhaseChanged() {
            if (!layoutLog.running)
                layoutLog.start()
        }
    }

    Text {
        id: nameProbe
        visible: false
        width: 140
        wrapMode: Text.WordWrap
        text: stage.entries[stage.chosenIndex] ? stage.entries[stage.chosenIndex].full_name : ""
        font.family: stage.theme.fonts.family
        font.pixelSize: stage.theme.fonts.size
    }

    Timer {
        interval: 50
        running: Controller.usersLoaded && stage.width > 0 && !stage.settled
        onTriggered: {
            stage.settled = true
            Controller.markShown()
            if (!layoutLog.running)
                layoutLog.start()
            console.info(`[greeter] font requested=${JSON.stringify(probe.font.family)} used=${JSON.stringify(probe.fontInfo.family)}`)
        }
    }

    Text {
        id: probe
        visible: false
        text: "Ag"
        font.family: stage.theme.fonts.family
        font.pixelSize: stage.theme.fonts.size
    }

    function choose(i) {
        const u = entries[i]
        if (u.name)
            Controller.selectUser(u.name)
        else
            Controller.manual = true
    }

    function message() {
        const a = Controller.auth
        if (a.phase === "unavailable") return qsTr("The login service is not running.")
        if (a.phase === "error") {
            if (a.problem === "launch") return qsTr("The session could not be started. Press Return to try again.")
            if (a.problem === "no_session") return qsTr("No desktop session is installed.")
            return qsTr("The login service stopped answering. Press Return to try again.")
        }
        if (a.phase === "failed" || !a.notes.length) return ""
        return a.notes[a.notes.length - 1].text
    }

    Keys.onLeftPressed: if (!chosen) current = Math.max(0, current - 1)
    Keys.onRightPressed: if (!chosen) current = Math.min(entries.length - 1, current + 1)
    Keys.onReturnPressed: if (!chosen) choose(current)
    Keys.onEnterPressed: if (!chosen) choose(current)
    Keys.onSpacePressed: if (!chosen) choose(current)
    Keys.onEscapePressed: if (chosen && listing && entries.length > 1) Controller.back()

    Connections {
        target: Controller
        function onShake() { shaker.restart() }
    }

    NumberAnimation {
        id: shaker
        target: stage
        property: "shakeP"
        from: 0
        to: 1
        duration: stage.theme.animation.shake.kind === "sine" ? stage.theme.animation.shake.duration_ms
                  : stage.theme.animation.shake.swing_ms * (stage.theme.animation.shake.swings.length + 1)
        onFinished: {
            stage.shakeP = 0
            Controller.dispatch({ type: "shaken" })
        }
    }

    Item {
        id: row
        x: stage.rowX + stage.slide
        y: stage.box.tile0.y
        width: stage.pg.count * stage.tileW
        height: stage.theme.tile.height
        Behavior on x {
            enabled: stage.settled
            NumberAnimation { duration: stage.theme.animation.select_ms; easing.type: Easing.BezierSpline; easing.bezierCurve: [0.42, 0, 0.58, 1, 1, 1] }
        }

        Repeater {
            model: stage.pg.count
            Tile {
                required property int index
                readonly property int at: stage.pg.first + index
                readonly property bool mine: at === stage.chosenIndex
                x: index * stage.tileW
                theme: stage.theme
                user: stage.entries[at]
                avatarSource: Controller.avatarFor(stage.entries[at])
                highlighted: !stage.chosen && stage.activeFocus && at === stage.current
                showBack: stage.chosen && mine && stage.listing && stage.entries.length > 1
                opacity: stage.chosen && !mine ? 0 : 1
                Component.onCompleted: if (mine) stage.chosenTile = this
                onMineChanged: if (mine) stage.chosenTile = this
                visible: opacity > 0
                Behavior on opacity { enabled: stage.settled; NumberAnimation { duration: stage.theme.animation.select_ms } }
                onClicked: if (!stage.chosen) stage.choose(at)
                onBack: Controller.back()
            }
        }
    }

    Item {
        id: entry
        width: field.width
        height: field.height
        x: Math.round((stage.width - width) / 2 + Layout.shakeX(stage.theme.animation.shake, stage.shakeP))
        y: stage.chosenBox.field.y
        opacity: stage.chosen ? 1 : 0
        visible: opacity > 0
        Behavior on opacity { enabled: stage.settled; NumberAnimation { duration: stage.theme.animation.select_ms } }

        PasswordField {
            id: field
            asking: Controller.manual || !stage.listing && !Controller.auth.user
            focus: stage.chosen
        }

    }

    ShadowText {
        id: messageText
        x: Math.round((stage.width - width) / 2)
        y: stage.chosenBox.message ? stage.chosenBox.message.y : entry.y + entry.height + 14
        width: 360
        theme: stage.theme
        text: stage.message()
        visible: text !== "" && stage.chosen
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        font.pixelSize: stage.theme.fonts.label_size
        color: Controller.auth.phase === "error" || Controller.auth.phase === "unavailable"
               || (Controller.auth.notes.length && Controller.auth.notes[Controller.auth.notes.length - 1].error)
               ? (Theme.color(stage.theme.colors.error) ?? "pink") : (Theme.color(stage.theme.colors.message) ?? "white")
        shadowY: 1
    }

    SessionChooser {
        id: chooser
        x: Math.round((stage.width - width) / 2)
        y: stage.chosenBox.session ? stage.chosenBox.session.y : entry.y + entry.height + 60
        visible: stage.chosen && Controller.sessions.length > 1
    }

    PowerBar {
        id: bar
        x: stage.box.bar.x
        y: stage.box.bar.y
    }

    Clock {
        id: clock
        x: stage.box.clock.x
        y: stage.box.clock.y + Math.round((stage.box.clock.h - height) / 2)
        width: implicitWidth
        height: implicitHeight
        theme: stage.theme
    }
}
