import QtQuick
import "Theme.js" as Theme
import "Layout.js" as Layout

FocusScope {
    id: stage

    readonly property var theme: Controller.theme
    readonly property real cy: height / 2
    readonly property var entries: Controller.users.concat([{ name: "", full_name: qsTr("Other…"), avatar: "" }])
    readonly property bool listing: Controller.showList && Controller.users.length > 0
    readonly property bool chosen: Controller.manual || Controller.phase !== "pick" && Controller.phase !== "unavailable"
                                   || !listing
    readonly property int chosenIndex: Controller.manual || !listing ? entries.length - 1
                                       : Math.max(0, entries.findIndex(u => u.name === Controller.auth.user))
    property int current: Math.max(0, Controller.users.findIndex(u => u.name === Controller.last.user))
    readonly property int per: Layout.perPage(width)
    readonly property var pg: Layout.page(entries.length, chosen ? chosenIndex : current, per)
    readonly property real tileW: theme.tile.width
    readonly property real rowX: Math.round((width - pg.count * tileW) / 2)
    readonly property real slide: chosen ? Math.round(width / 2 - (rowX + (chosenIndex - pg.first + 0.5) * tileW)) : 0
    property real shakeP: 0
    property bool settled: false

    Timer {
        interval: 50
        running: Controller.usersLoaded && stage.width > 0 && !stage.settled
        onTriggered: {
            stage.settled = true
            Controller.markShown()
            console.info(`[greeter] font requested=${JSON.stringify(probe.font.family)} used=${JSON.stringify(probe.fontInfo.family)}`)
        }
    }

    Text {
        id: probe
        visible: false
        text: "Ag"
        font.family: stage.theme.fonts.family
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
    Keys.onEscapePressed: if (chosen && listing) Controller.back()

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
        y: Math.round(stage.cy + stage.theme.layout.tile_top)
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
                showBack: stage.chosen && mine && stage.listing
                opacity: stage.chosen && !mine ? 0 : 1
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
        y: Math.round(stage.cy + stage.theme.layout.field_bottom - height)
        opacity: stage.chosen ? 1 : 0
        visible: opacity > 0
        Behavior on opacity { enabled: stage.settled; NumberAnimation { duration: stage.theme.animation.select_ms } }

        PasswordField {
            id: field
            asking: Controller.manual || !stage.listing && !Controller.auth.user
            focus: stage.chosen
            visible: !spinner.running
        }

        Spinner {
            id: spinner
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: -13
            width: 32
            height: 32
            running: ["verifying", "leaving", "launching"].includes(Controller.phase) || field.queued
        }
    }

    ShadowText {
        anchors.horizontalCenter: parent.horizontalCenter
        y: entry.y + entry.height + 14
        width: 360
        theme: stage.theme
        text: stage.message()
        visible: text !== "" && stage.chosen
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        color: Controller.auth.phase === "error" || Controller.auth.phase === "unavailable"
               || (Controller.auth.notes.length && Controller.auth.notes[Controller.auth.notes.length - 1].error)
               ? (Theme.color(stage.theme.colors.error) ?? "pink") : (Theme.color(stage.theme.colors.message) ?? "white")
        shadowY: 1
    }

    SessionChooser {
        anchors.horizontalCenter: parent.horizontalCenter
        y: entry.y + entry.height + 60
        visible: stage.chosen && Controller.sessions.length > 1
    }
}
