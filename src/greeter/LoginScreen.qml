import QtQuick
import Quickshell
import Quickshell.Wayland
import "Theme.js" as Theme

PanelWindow {
    id: win

    property bool main: false
    readonly property var theme: Controller.theme

    anchors { left: true; right: true; top: true; bottom: true }
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.namespace: "mavernix-greeter"
    WlrLayershell.keyboardFocus: main ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
    color: Theme.color(theme.background.color2) ?? "black"

    Background {
        anchors.fill: parent
        theme: win.theme
        themeDir: Controller.themeDir
    }

    Item {
        id: content
        anchors.fill: parent
        visible: win.main && Controller.themeReady && Controller.usersLoaded

        Stage {
            anchors.fill: parent
            focus: true
        }

    }

    // every screen ends on black, the same colour the console shows before the desktop draws
    Rectangle {
        id: curtain
        anchors.fill: parent
        color: "black"
        opacity: 0

        NumberAnimation on opacity {
            id: fade
            running: false
            to: 1
            duration: win.theme.animation.fade_ms
            easing.type: Easing.InOutQuad
            onFinished: if (win.main) Controller.dispatch({ type: "faded" })
        }
    }

    Connections {
        target: Controller
        function onFadeOut() { fade.start() }
        function onFadeIn() {
            fade.stop()
            curtain.opacity = 0
        }
    }
}
