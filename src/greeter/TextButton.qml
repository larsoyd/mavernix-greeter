import QtQuick
import "Theme.js" as Theme

Text {
    id: b
    required property var theme
    signal activated()

    color: Theme.color(theme.colors.button) ?? "white"
    font.family: theme.fonts.family
    font.pixelSize: theme.fonts.label_size
    font.underline: mouse.containsMouse || activeFocus
    style: Text.Raised
    styleColor: Theme.color(theme.colors.text_shadow) ?? "transparent"
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: text
    Accessible.onPressAction: activated()
    Keys.onReturnPressed: activated()
    Keys.onSpacePressed: activated()

    MouseArea {
        id: mouse
        anchors.fill: parent
        anchors.margins: -4
        hoverEnabled: true
        onClicked: b.activated()
    }
}
