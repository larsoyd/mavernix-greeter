import QtQuick
import QtQuick.Shapes
import "Theme.js" as Theme

Item {
    id: bg

    required property var theme
    required property string themeDir
    readonly property var look: theme.background
    readonly property real cx: width / 2
    readonly property real cy: height * look.center_y
    readonly property real rx: Math.max(1, width * look.radius_x)
    readonly property real ys: Math.max(0.01, height * look.radius_y / rx)

    clip: true

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        transform: Scale { origin.x: bg.cx; origin.y: bg.cy; yScale: bg.ys }
        ShapePath {
            strokeWidth: -1
            startX: 0
            startY: bg.cy - bg.cy / bg.ys - 1
            PathLine { x: bg.width; y: bg.cy - bg.cy / bg.ys - 1 }
            PathLine { x: bg.width; y: bg.cy + (bg.height - bg.cy) / bg.ys + 1 }
            PathLine { x: 0; y: bg.cy + (bg.height - bg.cy) / bg.ys + 1 }
            fillGradient: RadialGradient {
                centerX: bg.cx
                centerY: bg.cy
                centerRadius: bg.rx
                focalX: bg.cx
                focalY: bg.cy
                spread: ShapeGradient.PadSpread
                GradientStop { position: 0; color: Theme.color(bg.look.color) ?? "#51535b" }
                GradientStop { position: 1; color: Theme.color(bg.look.color2) ?? "#2d2d32" }
            }
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
