import QtQuick
import "Theme.js" as Theme

Item {
    id: bar
    readonly property var theme: Controller.theme
    readonly property int pitch: 98
    readonly property var shown: [
        { action: "suspend", label: qsTr("Sleep") },
        { action: "reboot", label: qsTr("Restart") },
        { action: "poweroff", label: qsTr("Shut Down") }
    ].filter(b => Controller.power[b.action] === true)
    readonly property real firstWidth: repeater.count ? repeater.itemAt(0).width : 0
    readonly property real lastWidth: repeater.count ? repeater.itemAt(repeater.count - 1).width : 0
    // distance from the bar's left edge to the middle of the button group
    readonly property int lead: Math.round(firstWidth / 2 + (shown.length - 1) * pitch / 2)

    implicitWidth: shown.length ? Math.ceil(firstWidth / 2 + (shown.length - 1) * pitch + lastWidth / 2) : 0
    implicitHeight: repeater.count ? repeater.itemAt(0).height : 0

    Repeater {
        id: repeater
        model: bar.shown
        Item {
            id: btn
            required property var modelData
            required property int index
            x: Math.round(bar.firstWidth / 2 + index * bar.pitch - width / 2)
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
                font.pixelSize: bar.theme.fonts.label_size
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
