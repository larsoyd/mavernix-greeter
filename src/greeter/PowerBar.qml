import QtQuick
import "Theme.js" as Theme

Row {
    id: bar
    readonly property var theme: Controller.theme
    spacing: 44

    Repeater {
        model: [
            { action: "suspend", label: qsTr("Sleep"), glyph: "☾" },
            { action: "reboot", label: qsTr("Restart"), glyph: "↻" },
            { action: "poweroff", label: qsTr("Shut Down"), glyph: "⏻" }
        ]
        Column {
            id: btn
            required property var modelData
            visible: Controller.power[modelData.action] === true
            spacing: 6
            activeFocusOnTab: true
            Accessible.role: Accessible.Button
            Accessible.name: modelData.label
            Keys.onReturnPressed: Controller.powerAction(modelData.action)
            Keys.onSpacePressed: Controller.powerAction(modelData.action)

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 34
                height: 34
                radius: 17
                color: Theme.color(bar.theme.colors.button_back) ?? "#40000000"
                border.width: btn.activeFocus ? 2 : 1
                border.color: btn.activeFocus ? (Theme.color(bar.theme.colors.focus) ?? "white") : "#59ffffff"
                Text {
                    anchors.centerIn: parent
                    text: btn.modelData.glyph
                    color: Theme.color(bar.theme.colors.button) ?? "white"
                    font.pixelSize: 17
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: Controller.powerAction(btn.modelData.action)
                }
            }
            ShadowText {
                anchors.horizontalCenter: parent.horizontalCenter
                theme: bar.theme
                text: btn.modelData.label
                font.pixelSize: bar.theme.fonts.label_size
                color: Controller.powerProblem === btn.modelData.action
                       ? (Theme.color(bar.theme.colors.error) ?? "pink") : (Theme.color(bar.theme.colors.button) ?? "white")
            }
        }
    }
}
