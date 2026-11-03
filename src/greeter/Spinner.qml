import QtQuick

Item {
    id: sp
    property bool running: false
    visible: running

    Repeater {
        model: 12
        Rectangle {
            required property int index
            x: sp.width / 2 - width / 2
            y: 0
            width: Math.max(1.5, sp.width / 10)
            height: sp.height * 0.28
            radius: width / 2
            color: "#555"
            opacity: ((index + 12 - tick.step) % 12) / 12 * 0.8 + 0.15
            transform: Rotation { origin.x: width / 2; origin.y: sp.height / 2; angle: index * 30 }
        }
    }

    Timer {
        id: tick
        property int step: 0
        interval: 83
        repeat: true
        running: sp.running && sp.visible
        onTriggered: step = (step + 1) % 12
    }
}
