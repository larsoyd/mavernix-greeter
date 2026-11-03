import QtQuick
import Quickshell

ShellRoot {
    id: shell

    readonly property string mainName: Quickshell.env("MAVENIX_GREETER_MAIN_OUTPUT") || ""

    function isMain(screen) {
        const all = Quickshell.screens
        const named = all.find(s => s.name === mainName)
        if (named)
            return screen === named
        const leftmost = all.slice().sort((a, b) => a.x - b.x || a.y - b.y)[0]
        return screen === leftmost
    }

    Variants {
        model: Quickshell.screens
        LoginScreen {
            required property var modelData
            screen: modelData
            main: shell.isMain(modelData)
        }
    }
}
