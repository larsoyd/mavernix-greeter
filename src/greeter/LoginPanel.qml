import QtQuick
import "Theme.js" as Theme

FocusScope {
    id: panel
    readonly property var theme: Controller.theme
    readonly property var user: Controller.currentUser
    readonly property bool asking: Controller.manual || !Controller.auth.user
    readonly property real avatarCentre: avatar.y + avatar.height / 2
    property real shakeX: 0

    width: Math.max(field.width, name.implicitWidth, avatar.width) + 80
    height: column.height

    function message() {
        const a = Controller.auth
        if (a.phase === "unavailable") return qsTr("The login service is not running.")
        if (a.phase === "error") {
            if (a.problem === "launch") return qsTr("The session could not be started.")
            if (a.problem === "no_session") return qsTr("No desktop session is installed.")
            return qsTr("The login service stopped answering.")
        }
        if (a.phase === "failed") return ""
        const notes = a.notes
        return notes.length ? notes[notes.length - 1].text : ""
    }

    Connections {
        target: Controller
        function onShake() { shaker.restart() }
    }

    SequentialAnimation {
        id: shaker
        property var swings: panel.theme.animation.shake.swings
        property int ms: panel.theme.animation.shake.swing_ms
        NumberAnimation { target: panel; property: "shakeX"; to: shaker.swings[0] ?? 0; duration: shaker.ms; easing.type: Easing.InOutSine }
        NumberAnimation { target: panel; property: "shakeX"; to: shaker.swings[1] ?? 0; duration: shaker.ms; easing.type: Easing.InOutSine }
        NumberAnimation { target: panel; property: "shakeX"; to: shaker.swings[2] ?? 0; duration: shaker.ms; easing.type: Easing.InOutSine }
        NumberAnimation { target: panel; property: "shakeX"; to: shaker.swings[3] ?? 0; duration: shaker.ms; easing.type: Easing.InOutSine }
        NumberAnimation { target: panel; property: "shakeX"; to: shaker.swings[4] ?? 0; duration: shaker.ms; easing.type: Easing.InOutSine }
        NumberAnimation { target: panel; property: "shakeX"; to: shaker.swings[5] ?? 0; duration: shaker.ms; easing.type: Easing.InOutSine }
        NumberAnimation { target: panel; property: "shakeX"; to: 0; duration: shaker.ms; easing.type: Easing.InOutSine }
        ScriptAction { script: Controller.dispatch({ type: "shaken" }) }
    }

    Column {
        id: column
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: panel.theme.layout.spacing

        Avatar {
            id: avatar
            anchors.horizontalCenter: parent.horizontalCenter
            theme: panel.theme
            source: panel.asking ? "" : Controller.avatarFor(panel.user)
            initials: panel.asking ? "?" : (panel.user.full_name || "?").slice(0, 1).toUpperCase()
        }

        ShadowText {
            id: name
            anchors.horizontalCenter: parent.horizontalCenter
            theme: panel.theme
            text: panel.asking ? qsTr("Other…") : panel.user.full_name
            font.pixelSize: panel.theme.fonts.name_size
            font.bold: panel.theme.fonts.name_bold
        }

        Item {
            width: field.width
            height: field.height
            anchors.horizontalCenter: parent.horizontalCenter
            transform: Translate { x: panel.shakeX }

            PasswordField {
                id: field
                theme: panel.theme
                asking: panel.asking
                focus: true
            }
        }

        ShadowText {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.max(field.width * 1.6, 1)
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            theme: panel.theme
            text: panel.message()
            visible: text !== ""
            font.pixelSize: panel.theme.fonts.label_size
            color: Controller.auth.phase === "error" || Controller.auth.phase === "unavailable"
                   || (Controller.auth.notes.length && Controller.auth.notes[Controller.auth.notes.length - 1].error)
                   ? (Theme.color(panel.theme.colors.error) ?? "pink") : (Theme.color(panel.theme.colors.text) ?? "white")
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 18

            TextButton {
                theme: panel.theme
                text: qsTr("Back")
                visible: Controller.showList && Controller.users.length > 1 || Controller.manual
                onActivated: Controller.back()
            }
            TextButton {
                theme: panel.theme
                text: qsTr("Try Again")
                visible: Controller.auth.phase === "error"
                onActivated: Controller.dispatch({ type: "retry" })
            }
            SessionChooser {
                visible: Controller.sessions.length > 1
            }
        }
    }

    Keys.onEscapePressed: if (Controller.showList && Controller.users.length > 1 || Controller.manual) Controller.back()
}
