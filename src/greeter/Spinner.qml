import QtQuick

Item {
    id: sp
    property bool running: false
    property color color: "white"
    visible: running

    Repeater {
        model: 12
        Rectangle {
            required property int index
            x: sp.width / 2 - width / 2
            y: sp.height * 0.06
            width: Math.max(2, sp.width / 11)
            height: sp.height * 0.26
            radius: width / 2
            color: sp.color
            opacity: ((index + 12 - tick.step) % 12) / 12 * 0.75 + 0.15
            transform: Rotation { origin.x: width / 2; origin.y: sp.height / 2 - sp.height * 0.06; angle: index * 30 }
        }
    }

    Timer {
        id: tick
        property int step: 0
        interval: 1000 / 12
        repeat: true
        running: sp.running
        onTriggered: step = (step + 1) % 12
    }
}
