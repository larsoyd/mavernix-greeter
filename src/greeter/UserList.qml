import QtQuick
import "Theme.js" as Theme

FocusScope {
    id: list
    readonly property var theme: Controller.theme
    readonly property var entries: Controller.users.concat([{ name: "", full_name: qsTr("Other…"), avatar: "" }])
    property int current: Math.max(0, Controller.users.findIndex(u => u.name === Controller.last.user))

    width: row.width
    height: row.height

    signal other()

    function choose(i) {
        const u = entries[i]
        if (u.name)
            Controller.selectUser(u.name)
        else
            Controller.manual = true
    }

    Keys.onLeftPressed: current = Math.max(0, current - 1)
    Keys.onRightPressed: current = Math.min(entries.length - 1, current + 1)
    Keys.onReturnPressed: choose(current)
    Keys.onEnterPressed: choose(current)
    Keys.onSpacePressed: choose(current)

    Row {
        id: row
        spacing: list.theme.layout.grid_gap

        Repeater {
            model: list.entries
            UserTile {
                required property var modelData
                required property int index
                theme: list.theme
                user: modelData
                avatarSource: Controller.avatarFor(modelData)
                current: list.activeFocus && index === list.current
                onClicked: list.choose(index)
                onHovered: list.current = index
            }
        }
    }
}
