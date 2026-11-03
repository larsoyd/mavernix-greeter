import QtQuick
import QtQuick.Effects
import QtQuick.Shapes
import "Theme.js" as Theme

Item {
    id: av

    required property var theme
    property string source: ""
    property bool other: false
    property bool pressed: false
    readonly property real size: theme.avatar.size
    readonly property bool hasPicture: !other && picture.status === Image.Ready
    width: size
    height: size

    Rectangle {
        id: silhouette
        anchors.fill: parent
        radius: width / 2
        visible: !av.hasPicture
        gradient: Gradient {
            GradientStop { position: 0; color: Theme.color(av.theme.avatar.other_top) ?? "#9aaac0" }
            GradientStop { position: 1; color: Theme.color(av.theme.avatar.other_bottom) ?? "#5f6f88" }
        }
        clip: true
        Rectangle {
            width: av.size * 0.36
            height: width
            radius: width / 2
            x: (av.size - width) / 2
            y: av.size * 0.2
            color: "#e8edf3"
        }
        Rectangle {
            width: av.size * 0.66
            height: av.size * 0.5
            radius: width / 2
            x: (av.size - width) / 2
            y: av.size * 0.6
            color: "#e8edf3"
        }
    }

    Image {
        id: picture
        anchors.fill: parent
        source: av.source && !av.other ? "file://" + av.source : ""
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
        visible: av.hasPicture
        maskEnabled: true
        maskSource: mask
        maskThresholdMin: 0.5
        maskSpreadAtMin: 1.0
    }

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: Theme.color(av.theme.avatar.pressed) ?? "#54000000"
        visible: av.pressed
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: -1
        radius: width / 2
        color: "transparent"
        border.width: 1
        border.color: Theme.color(av.theme.avatar.rim_outer) ?? "transparent"
    }

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: "transparent"
        border.width: 1
        border.color: Theme.color(av.theme.avatar.rim_inner) ?? "transparent"
    }
}
