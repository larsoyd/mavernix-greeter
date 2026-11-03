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
    readonly property alias lineCount: label.lineCount
    property color color: Theme.color(theme.colors.text) ?? "white"
    property color shadowColor: Theme.color(theme.colors.text_shadow) ?? "transparent"
    property real shadowY: theme.name.shadow_y
    property real blur: theme.name.blur

    implicitWidth: Math.ceil(label.implicitWidth)
    implicitHeight: Math.ceil(label.implicitHeight)

    // the glyphs stay out of any layer so they are drawn sharp, only the shadow copy is blurred
    Text {
        id: shade
        x: 0
        y: Math.round(st.shadowY)
        width: label.width
        height: label.height
        text: label.text
        font: label.font
        horizontalAlignment: label.horizontalAlignment
        wrapMode: label.wrapMode
        maximumLineCount: label.maximumLineCount
        elide: label.elide
        textFormat: Text.PlainText
        color: st.shadowColor
        visible: st.blur <= 0
    }

    Item {
        id: shadeLayer
        x: -4
        y: Math.round(st.shadowY) - 4
        width: Math.ceil(label.width) + 8
        height: Math.ceil(label.height) + 8
        visible: false
        layer.enabled: st.blur > 0

        Text {
            x: 4
            y: 4
            width: label.width
            height: label.height
            text: label.text
            font: label.font
            horizontalAlignment: label.horizontalAlignment
            wrapMode: label.wrapMode
            maximumLineCount: label.maximumLineCount
            elide: label.elide
            textFormat: Text.PlainText
            color: st.shadowColor
        }
    }

    MultiEffect {
        source: shadeLayer
        x: shadeLayer.x
        y: shadeLayer.y
        width: shadeLayer.width
        height: shadeLayer.height
        visible: st.blur > 0
        blurEnabled: true
        blurMax: 8
        blur: Math.min(1, st.blur / 8)
    }

    Text {
        id: label
        width: st.width > 0 ? Math.round(st.width) : Math.ceil(implicitWidth)
        color: st.color
        font.family: st.theme.fonts.family
        font.pixelSize: st.theme.fonts.size
        textFormat: Text.PlainText
    }
}
