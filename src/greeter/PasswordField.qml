import QtQuick
import "Theme.js" as Theme

FocusScope {
    id: box

    readonly property var theme: Controller.theme
    property bool asking: false
    readonly property string phase: Controller.auth.phase
    readonly property bool secret: !asking && !Controller.auth.echo
    readonly property bool failedBadge: Controller.auth.tries > 0 && input.text === "" && !asking
    property bool queued: false

    width: theme.field.width
    height: theme.field.height
    Accessible.role: Accessible.EditableText
    Accessible.name: placeholder.text
    Accessible.passwordEdit: secret

    function placeholderText() {
        if (asking) return qsTr("Name")
        const a = Controller.auth
        if (a.phase === "prompt" && a.prompt && !/^password:?\s*$/i.test(a.prompt)) return a.prompt.replace(/:\s*$/, "")
        return qsTr("Password")
    }

    function accept() {
        if (asking) {
            if (input.text.trim())
                Controller.selectUser(input.text.trim())
            input.text = ""
            return
        }
        if (phase === "prompt")
            Controller.submit(input.text)
        else if (phase === "error")
            Controller.dispatch({ type: "retry" })
        else if (phase === "info" || phase === "starting")
            queued = true
    }

    onPhaseChanged: {
        if (phase === "prompt" && queued) {
            queued = false
            Controller.submit(input.text)
        } else if (phase !== "info" && phase !== "starting") {
            queued = false
        }
    }

    Connections {
        target: Controller
        function onClearField() { input.text = "" }
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: -2
        radius: box.theme.field.radius + 2
        visible: input.activeFocus
        gradient: Gradient {
            GradientStop { position: 0; color: Theme.color(box.theme.colors.focus) ?? "#4a95e4" }
            GradientStop { position: 1; color: Theme.color(box.theme.colors.focus2) ?? "#3c8cdc" }
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: box.theme.field.radius
        border.width: 1
        border.color: Theme.color(box.theme.colors.field_border) ?? "#33000000"
        gradient: Gradient {
            GradientStop { position: 0; color: Theme.color(box.theme.colors.field_top) ?? "#eaeaea" }
            GradientStop { position: Math.min(1, 15 / box.height); color: Theme.color(box.theme.colors.field) ?? "white" }
            GradientStop { position: 1; color: Theme.color(box.theme.colors.field) ?? "white" }
        }
    }

    Text {
        id: placeholder
        anchors.fill: input
        verticalAlignment: Text.AlignVCenter
        text: box.placeholderText()
        visible: input.text === "" && !input.preeditText
        renderType: Text.NativeRendering
        color: Theme.color(box.theme.colors.placeholder) ?? "gray"
        font: input.font
        elide: Text.ElideRight
    }

    TextInput {
        id: input
        anchors.fill: parent
        anchors.leftMargin: 5
        anchors.rightMargin: (go.visible || badge.visible || busy.running) ? 30 : 10
        anchors.topMargin: 3
        anchors.bottomMargin: 3
        verticalAlignment: TextInput.AlignVCenter
        focus: true
        echoMode: box.secret ? TextInput.Password : TextInput.Normal
        passwordMaskDelay: 0
        passwordCharacter: "•"
        readOnly: !box.asking && !["prompt", "info", "starting", "failed", "error"].includes(box.phase)
        color: Theme.color(box.theme.colors.field_text) ?? "black"
        font.family: box.theme.fonts.family
        font.pixelSize: box.theme.fonts.field_size
        renderType: Text.NativeRendering
        selectByMouse: false
        clip: true
        inputMethodHints: box.secret ? (Qt.ImhHiddenText | Qt.ImhSensitiveData | Qt.ImhNoPredictiveText) : Qt.ImhNone
        onAccepted: box.accept()
    }

    Item {
        id: go
        width: 16
        height: 17
        anchors.right: parent.right
        anchors.rightMargin: Math.round((box.height - height) / 2)
        anchors.verticalCenter: parent.verticalCenter
        visible: (input.text !== "" || box.asking) && !busy.running
        Accessible.role: Accessible.Button
        Accessible.name: qsTr("Log In")

        Rectangle {
            anchors.centerIn: parent
            width: 16
            height: 16
            radius: 8
            color: goArea.pressed ? "#8c8c8c" : "#a8a8a8"
        }
        Canvas {
            anchors.fill: parent
            onPaint: {
                const c = getContext("2d")
                c.reset()
                c.fillStyle = "white"
                c.beginPath()
                c.moveTo(4, 7)
                c.lineTo(8, 7)
                c.lineTo(8, 4)
                c.lineTo(12.5, 8.5)
                c.lineTo(8, 13)
                c.lineTo(8, 10)
                c.lineTo(4, 10)
                c.closePath()
                c.fill()
            }
        }
        MouseArea {
            id: goArea
            anchors.fill: parent
            anchors.margins: -3
            onClicked: box.accept()
        }
    }

    Rectangle {
        id: badge
        width: 14
        height: 14
        radius: 7
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        visible: box.failedBadge && !go.visible && !busy.running
        color: Theme.color(box.theme.colors.error) ?? "#e0443e"
        Text {
            anchors.centerIn: parent
            text: "!"
            color: "white"
            font.bold: true
            font.pixelSize: 11
        }
    }

    Spinner {
        id: busy
        width: 16
        height: 16
        anchors.right: parent.right
        anchors.rightMargin: Math.round((box.height - height) / 2)
        anchors.verticalCenter: parent.verticalCenter
        color: "#7a7a7a"
        running: ["verifying", "leaving", "launching"].includes(box.phase) || box.queued
    }
}
