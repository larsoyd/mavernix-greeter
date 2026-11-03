import QtQuick
import QtQuick.Effects
import "Theme.js" as Theme

Item {
    id: av

    required property var theme
    property string source: ""
    property string initials: ""
    property real size: theme.avatar.size
    width: size
    height: size

    RectangularShadow {
        anchors.fill: face
        radius: width / 2
        blur: Math.round(av.size / 14)
        offset.y: Math.round(av.size / 40)
        color: Theme.color(av.theme.avatar.shadow) ?? "#80000000"
    }

    Rectangle {
        id: face
        anchors.fill: parent
        radius: width / 2
        color: "#8a96a8"
        visible: picture.status !== Image.Ready
        Text {
            anchors.centerIn: parent
            text: av.initials
            color: "white"
            font.pixelSize: av.size * 0.4
            font.weight: Font.DemiBold
        }
    }

    Image {
        id: picture
        anchors.fill: parent
        source: av.source ? "file://" + av.source : ""
        fillMode: Image.PreserveAspectCrop
        sourceSize: Qt.size(av.size * 2, av.size * 2)
        asynchronous: true
        visible: false
        onStatusChanged: if (status === Image.Error) console.info("[greeter] avatar problem=unreadable")
    }

    Rectangle {
        id: mask
        anchors.fill: parent
        radius: width / 2
        visible: false
        layer.enabled: true
    }

    MultiEffect {
        anchors.fill: parent
        source: picture
        visible: picture.status === Image.Ready
        maskEnabled: true
        maskSource: mask
        maskThresholdMin: 0.5
        maskSpreadAtMin: 1.0
    }

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: "transparent"
        border.width: Math.max(1, Math.round(av.size / 64))
        border.color: Theme.color(av.theme.avatar.ring) ?? "transparent"
    }
}
