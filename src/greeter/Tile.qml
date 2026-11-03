import QtQuick
import "Theme.js" as Theme

Item {
    id: tile

    required property var theme
    required property var user
    property string avatarSource: ""
    property bool highlighted: false
    property bool showBack: false
    readonly property alias nameItem: name
    signal clicked()
    signal back()

    width: theme.tile.width
    height: theme.tile.height
    Accessible.role: Accessible.Button
    Accessible.name: user.full_name

    Rectangle {
        anchors.horizontalCenter: picture.horizontalCenter
        y: picture.y - 6
        width: 140
        height: theme.tile.height - y
        radius: 8
        color: "#1e000000"
        visible: tile.highlighted
    }

    Avatar {
        id: picture
        x: (tile.width - width) / 2
        y: (92 - height) / 2
        theme: tile.theme
        source: tile.avatarSource
        other: !tile.user.name
        pressed: mouse.pressed
    }

    Row {
        x: Math.round((tile.width - width) / 2)
        y: 97
        spacing: 2
        layoutDirection: Qt.application.layoutDirection

        BackArrow {
            visible: tile.showBack
            anchors.verticalCenter: name.verticalCenter
            onActivated: tile.back()
        }

        ShadowText {
            id: name
            theme: tile.theme
            width: Math.min(140, implicitWidth)
            text: tile.user.full_name
            font.bold: tile.theme.name.bold
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: picture
        onClicked: tile.clicked()
    }
}
