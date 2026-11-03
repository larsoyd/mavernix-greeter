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
    WlrLayershell.namespace: "mavenix-greeter"
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

        Stage {
            anchors.fill: parent
            focus: true
        }

        PowerBar {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: win.theme.layout.bar_bottom
        }

        Clock {
            anchors.right: parent.right
            anchors.rightMargin: 10
            y: 4
            theme: win.theme
        }
    }
}
