import QtQuick
import "Theme.js" as Theme

Item {
    id: tile

    required property var theme
    required property var user
    property string avatarSource: ""
    property bool current: false
    signal clicked()
    signal hovered()

    width: Math.max(avatar.width, name.implicitWidth)
    height: avatar.height + theme.layout.spacing + name.height

    Accessible.role: Accessible.Button
    Accessible.name: user.full_name

    Avatar {
        id: avatar
        anchors.horizontalCenter: parent.horizontalCenter
        theme: tile.theme
        size: tile.theme.avatar.size * 0.75
        source: tile.avatarSource
        initials: (tile.user.full_name || "?").slice(0, 1).toUpperCase()
        scale: mouse.pressed ? 0.96 : 1
    }

    Rectangle {
        anchors.centerIn: avatar
        width: avatar.width + 8
        height: width
        radius: width / 2
        color: "transparent"
        border.width: 3
        border.color: Theme.color(tile.theme.colors.focus) ?? "white"
        visible: tile.current
    }

    ShadowText {
        id: name
        anchors.top: avatar.bottom
        anchors.topMargin: tile.theme.layout.spacing
        anchors.horizontalCenter: parent.horizontalCenter
        theme: tile.theme
        text: tile.user.full_name
        font.pixelSize: tile.theme.fonts.name_size
        font.bold: tile.theme.fonts.name_bold
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        onEntered: tile.hovered()
        onClicked: tile.clicked()
    }
}
