import QtQuick
import "Theme.js" as Theme

FocusScope {
    id: box

    required property var theme
    property bool asking: false
    readonly property string phase: Controller.auth.phase
    readonly property bool secret: !asking && !Controller.auth.echo
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
        if (a.phase === "verifying" || a.phase === "leaving" || a.phase === "launching") return ""
        return qsTr("Enter Password")
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

    Repeater {
        model: 3
        Rectangle {
            required property int index
            anchors.fill: parent
            anchors.margins: -(index + 1)
            radius: box.theme.field.radius + index + 1
            color: "transparent"
            border.width: 1
            border.color: Theme.color(box.theme.colors.focus) ?? "steelblue"
            opacity: input.activeFocus ? (0.9 - index * 0.3) : 0
            Behavior on opacity { NumberAnimation { duration: 120 } }
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: box.theme.field.radius
        color: Theme.color(box.theme.colors.field) ?? "white"
        border.width: 1
        border.color: Theme.color(box.theme.colors.field_border) ?? "gray"
    }

    Text {
        id: placeholder
        anchors.fill: input
        verticalAlignment: Text.AlignVCenter
        text: box.placeholderText()
        visible: input.text === ""
        color: Theme.color(box.theme.colors.placeholder) ?? "gray"
        font: input.font
        elide: Text.ElideRight
        renderType: Text.NativeRendering
    }

    TextInput {
        id: input
        anchors.fill: parent
        anchors.leftMargin: Math.round(box.theme.field.radius * 0.7) + 4
        anchors.rightMargin: arrow.width + 6
        verticalAlignment: TextInput.AlignVCenter
        focus: true
        echoMode: box.secret ? TextInput.Password : TextInput.Normal
        passwordMaskDelay: 0
        passwordCharacter: "●"
        readOnly: !box.asking && !["prompt", "info", "starting", "failed"].includes(box.phase)
        color: Theme.color(box.theme.colors.field_text) ?? "black"
        font.family: box.theme.fonts.family
        font.pixelSize: box.theme.fonts.field_size
        selectByMouse: false
        inputMethodHints: box.secret ? (Qt.ImhHiddenText | Qt.ImhSensitiveData | Qt.ImhNoPredictiveText) : Qt.ImhNone
        renderType: Text.NativeRendering
        onAccepted: box.accept()
    }

    Rectangle {
        id: arrow
        anchors.right: parent.right
        anchors.rightMargin: 3
        anchors.verticalCenter: parent.verticalCenter
        width: parent.height - 6
        height: width
        radius: width / 2
        color: Theme.color(box.theme.colors.button_back) ?? "#40000000"
        visible: input.text !== "" || box.asking
        Text {
            anchors.centerIn: parent
            text: "➜"
            color: "white"
            font.pixelSize: parent.height * 0.6
        }
        MouseArea {
            anchors.fill: parent
            onClicked: box.accept()
        }
    }

    Spinner {
        anchors.right: parent.right
        anchors.rightMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        height: parent.height - 8
        width: height
        running: ["verifying", "leaving", "launching"].includes(box.phase) || box.queued
    }
}
