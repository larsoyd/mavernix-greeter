import QtQuick

ShadowText {
    id: clock
    property date now: new Date()
    text: Qt.locale().toString(now, "ddd") + " " + Qt.locale().toString(now, Qt.locale().timeFormat(Locale.ShortFormat))
    shadowY: 1

    Timer {
        interval: 1000
        repeat: true
        running: true
        onTriggered: clock.now = new Date()
    }
}
