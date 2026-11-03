import QtQuick

Item {
    id: icon
    property string kind: "poweroff"
    property bool pressed: false
    property bool focused: false
    width: 32
    height: 36

    Rectangle {
        x: 1
        y: 2
        width: 30
        height: 30
        radius: 15
        border.width: icon.focused ? 2 : 1
        border.color: icon.focused ? "#4a95e4" : "#73ffffff"
        gradient: Gradient {
            GradientStop { position: 0; color: icon.pressed ? "#5a5c63" : "#7b7d85" }
            GradientStop { position: 1; color: icon.pressed ? "#34353a" : "#4b4c52" }
        }
    }

    Canvas {
        x: 1
        y: 2
        width: 30
        height: 30
        onPaint: {
            const c = getContext("2d")
            c.reset()
            c.strokeStyle = "rgba(255,255,255,0.9)"
            c.fillStyle = "rgba(255,255,255,0.9)"
            c.lineWidth = 2
            c.lineCap = "round"
            const m = 15
            c.beginPath()
            if (icon.kind === "poweroff") {
                c.arc(m, m + 1, 7, -Math.PI * 0.32, Math.PI * 1.32, false)
                c.moveTo(m, m - 8)
                c.lineTo(m, m)
                c.stroke()
            } else if (icon.kind === "reboot") {
                c.arc(m, m, 7, -Math.PI * 0.35, Math.PI * 1.45, false)
                c.stroke()
                c.beginPath()
                c.moveTo(m + 6.5, m - 9)
                c.lineTo(m + 6.5, m - 3)
                c.lineTo(m + 0.5, m - 4)
                c.closePath()
                c.fill()
            } else {
                c.arc(m, m, 8, Math.PI * 0.35, Math.PI * 1.65, false)
                c.arc(m + 4, m - 2, 6.5, Math.PI * 1.55, Math.PI * 0.45, true)
                c.closePath()
                c.fill()
            }
        }
    }
}
