import QtQuick
import "Theme.js" as Theme

Item {
    id: bg

    required property var theme
    required property string themeDir
    readonly property var look: theme.background

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0; color: Theme.color(bg.look.color) ?? "#454c58" }
            GradientStop { position: 1; color: Theme.color(bg.look.color2) ?? "#1f2329" }
        }
    }

    Image {
        anchors.fill: parent
        visible: status === Image.Ready
        source: bg.look.image ? "file://" + bg.themeDir + "/" + bg.look.image : ""
        fillMode: bg.look.fit === "contain" ? Image.PreserveAspectFit
                : bg.look.fit === "stretch" ? Image.Stretch : Image.PreserveAspectCrop
        asynchronous: true
        cache: false
        sourceSize.width: width
        onStatusChanged: if (status === Image.Error) console.info("[greeter] background problem=unreadable")
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.color(bg.look.veil) ?? "transparent"
    }
}
