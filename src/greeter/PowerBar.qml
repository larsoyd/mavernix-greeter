import QtQuick
import "Theme.js" as Theme

Row {
    id: bar
    readonly property var theme: Controller.theme
    spacing: theme.layout.bar_gap

    Repeater {
        model: [
            { action: "suspend", label: qsTr("Sleep") },
            { action: "reboot", label: qsTr("Restart") },
            { action: "poweroff", label: qsTr("Shut Down") }
        ]
        Item {
            id: btn
            required property var modelData
            visible: Controller.power[modelData.action] === true
            width: Math.max(label.implicitWidth, 34) + 4
            height: 36 + 4 + label.implicitHeight
            activeFocusOnTab: true
            Accessible.role: Accessible.Button
            Accessible.name: modelData.label
            Accessible.onPressAction: Controller.powerAction(modelData.action)
            Keys.onReturnPressed: Controller.powerAction(modelData.action)
            Keys.onSpacePressed: Controller.powerAction(modelData.action)

            PowerIcon {
                id: icon
                x: Math.round((parent.width - width) / 2)
                kind: btn.modelData.action
                pressed: area.pressed
                focused: btn.activeFocus
            }
            ShadowText {
                id: label
                x: Math.round((parent.width - width) / 2)
                anchors.top: icon.bottom
                anchors.topMargin: 4
                theme: bar.theme
                text: btn.modelData.label
                shadowY: 1
                shadowColor: Theme.color(bar.theme.colors.label_shadow) ?? "transparent"
                color: Controller.powerProblem === btn.modelData.action ? (Theme.color(bar.theme.colors.error) ?? "pink")
                     : area.pressed ? (Theme.color(bar.theme.colors.label_pressed) ?? "white")
                     : (Theme.color(bar.theme.colors.label) ?? "white")
            }
            MouseArea {
                id: area
                anchors.fill: parent
                onClicked: Controller.powerAction(btn.modelData.action)
            }
        }
    }
}
