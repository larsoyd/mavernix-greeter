import QtQuick
import "Theme.js" as Theme

Item {
    id: chooser
    readonly property var theme: Controller.theme
    readonly property var current: Controller.sessions.find(s => s.id === Controller.sessionId)
    property bool open: false

    width: label.width
    height: label.height

    TextButton {
        id: label
        theme: chooser.theme
        text: (chooser.current ? chooser.current.name : qsTr("Session")) + " ▾"
        onActivated: chooser.open = !chooser.open
        Accessible.name: qsTr("Session: %1").arg(chooser.current ? chooser.current.name : "")
        Keys.onUpPressed: chooser.move(-1)
        Keys.onDownPressed: chooser.move(1)
    }

    function move(d) {
        const list = Controller.sessions
        const i = list.findIndex(s => s.id === Controller.sessionId)
        Controller.chooseSession(list[(i + d + list.length) % list.length].id)
    }

    Rectangle {
        visible: chooser.open
        anchors.top: label.bottom
        anchors.topMargin: 6
        anchors.horizontalCenter: label.horizontalCenter
        width: menu.width + 16
        height: menu.height + 10
        radius: 5
        color: "#f2f2f2"
        border.color: "#40000000"
        z: 10

        Column {
            id: menu
            anchors.centerIn: parent
            Repeater {
                model: Controller.sessions
                Rectangle {
                    required property var modelData
                    width: Math.max(140, t.implicitWidth + 24)
                    height: t.implicitHeight + 6
                    radius: 3
                    color: hover.containsMouse ? "#3875d7" : "transparent"
                    Text {
                        id: t
                        x: 12
                        anchors.verticalCenter: parent.verticalCenter
                        text: (modelData.id === Controller.sessionId ? "✓ " : "   ") + modelData.name
                        color: hover.containsMouse ? "white" : "black"
                        textFormat: Text.PlainText
                        font.family: chooser.theme.fonts.family
                        font.pixelSize: chooser.theme.fonts.label_size
                    }
                    MouseArea {
                        id: hover
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            Controller.chooseSession(modelData.id)
                            chooser.open = false
                        }
                    }
                }
            }
        }
    }
}
