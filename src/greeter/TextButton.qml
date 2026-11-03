import QtQuick
import "Theme.js" as Theme

ShadowText {
    id: b
    signal activated()

    color: mouse.pressed ? (Theme.color(theme.colors.label_pressed) ?? "white") : (Theme.color(theme.colors.label) ?? "white")
    shadowColor: Theme.color(theme.colors.label_shadow) ?? "transparent"
    shadowY: 1
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: text
    Accessible.onPressAction: activated()
    Keys.onReturnPressed: activated()
    Keys.onSpacePressed: activated()

    Rectangle {
        anchors.fill: parent
        anchors.margins: -3
        radius: 3
        color: "transparent"
        border.color: Theme.color(b.theme.colors.focus) ?? "white"
        border.width: 2
        visible: b.activeFocus
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        anchors.margins: -4
        onClicked: b.activated()
    }
}
