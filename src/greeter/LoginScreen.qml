import QtQuick
import Quickshell
import Quickshell.Wayland
import "Theme.js" as Theme

PanelWindow {
    id: win
    property bool main: false
    readonly property var theme: Controller.theme
    readonly property string phase: Controller.phase

    anchors { left: true; right: true; top: true; bottom: true }
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.namespace: "mavenix-greeter"
    WlrLayershell.keyboardFocus: main ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
    color: Theme.color(theme.background.color2) ?? "black"

    Background {
        anchors.fill: parent
        theme: win.theme
        themeDir: Controller.themeDir
        opacity: Controller.themeReady ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 250 } }
    }

    Item {
        id: content
        anchors.fill: parent
        visible: win.main && Controller.themeReady && Controller.usersLoaded
        opacity: 1

        NumberAnimation on opacity {
            id: fade
            running: false
            to: 0
            duration: win.theme.animation.fade_ms
            easing.type: Easing.InOutQuad
            onFinished: Controller.dispatch({ type: "faded" })
        }

        Connections {
            target: Controller
            function onFadeOut() {
                if (win.main)
                    fade.start()
            }
            function onFadeIn() {
                fade.stop()
                content.opacity = 1
            }
        }

        UserList {
            id: list
            anchors.horizontalCenter: parent.horizontalCenter
            y: Math.round(parent.height * win.theme.layout.center_y - height / 2)
            visible: Controller.phase === "pick" && Controller.showList && Controller.users.length > 0
            focus: visible
        }

        LoginPanel {
            id: panel
            anchors.horizontalCenter: parent.horizontalCenter
            y: Math.round(parent.height * win.theme.layout.center_y - avatarCentre)
            visible: !list.visible
            focus: visible
        }

        PowerBar {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: Math.round(parent.height * 0.06)
        }
    }
}
