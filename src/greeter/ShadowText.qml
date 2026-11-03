import QtQuick
import "Theme.js" as Theme

Text {
    required property var theme
    color: Theme.color(theme.colors.text) ?? "white"
    font.family: theme.fonts.family
    style: Text.Raised
    styleColor: Theme.color(theme.colors.text_shadow) ?? "transparent"
    renderType: Text.NativeRendering
}
