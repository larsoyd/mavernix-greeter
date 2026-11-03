import QtQuick

Item {
    id: arrow
    signal activated()
    width: 16
    height: 16
    Accessible.role: Accessible.Button
    Accessible.name: qsTr("Back")

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: area.pressed ? "#a0000000" : "#66000000"
        border.color: "#59ffffff"
    }
    Canvas {
        anchors.fill: parent
        onPaint: {
            const c = getContext("2d")
            c.reset()
            c.strokeStyle = "white"
            c.lineWidth = 1.6
            c.beginPath()
            c.moveTo(width * 0.6, height * 0.28)
            c.lineTo(width * 0.36, height * 0.5)
            c.lineTo(width * 0.6, height * 0.72)
            c.stroke()
        }
    }
    MouseArea {
        id: area
        anchors.fill: parent
        anchors.margins: -4
        onClicked: arrow.activated()
    }
}
