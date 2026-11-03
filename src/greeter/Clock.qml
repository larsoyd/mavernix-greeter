import QtQuick
import "Theme.js" as Theme

ShadowText {
    id: clock
    property date now: new Date()
    text: Qt.locale().toString(now, Qt.locale().timeFormat(Locale.ShortFormat))
    font.pixelSize: theme.fonts.clock_size
    color: Theme.color(theme.colors.clock) ?? "white"
    shadowColor: Theme.color(theme.colors.label_shadow) ?? "transparent"
    shadowY: 1

    Timer {
        interval: 1000
        repeat: true
        running: true
        onTriggered: clock.now = new Date()
    }
}
