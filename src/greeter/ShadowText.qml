import QtQuick
import QtQuick.Effects
import "Theme.js" as Theme

Item {
    id: st

    required property var theme
    property alias text: label.text
    property alias font: label.font
    property alias horizontalAlignment: label.horizontalAlignment
    property alias wrapMode: label.wrapMode
    property alias maximumLineCount: label.maximumLineCount
    property alias elide: label.elide
    property color color: Theme.color(theme.colors.text) ?? "white"
    property color shadowColor: Theme.color(theme.colors.text_shadow) ?? "transparent"
    property real shadowY: theme.name.shadow_y
    property real blur: theme.name.blur

    implicitWidth: label.implicitWidth
    implicitHeight: label.implicitHeight

    Text {
        id: label
        width: st.width > 0 ? st.width : implicitWidth
        color: st.color
        font.family: st.theme.fonts.family
        font.pixelSize: st.theme.fonts.size
        renderType: Text.QtRendering
        visible: false
    }

    MultiEffect {
        source: label
        anchors.fill: label
        anchors.margins: -4
        autoPaddingEnabled: false
        paddingRect: Qt.rect(4, 4, label.width + 8, label.height + 8)
        shadowEnabled: true
        shadowColor: st.shadowColor
        shadowVerticalOffset: st.shadowY
        shadowHorizontalOffset: 0
        blurMax: 4
        shadowBlur: Math.min(1, st.blur / 4)
    }
}
