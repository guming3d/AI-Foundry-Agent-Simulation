"""
Theme selection screen for the Textual TUI application.

Provides a modal dialog for selecting application themes with live preview.
When user highlights a different theme, the dialog colors update dynamically
so they can see what the theme looks like before applying.
"""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static, Button, OptionList
from textual.widgets.option_list import Option
from textual.containers import Container, Horizontal

from ui.terminal.themes import APP_THEMES, THEME_NAMES, get_theme_by_name


class ThemeSelectScreen(ModalScreen[str | None]):
    """Modal screen for selecting a theme with live preview.
    
    The app's theme changes dynamically as the user navigates through options,
    allowing them to see each theme's colors in real-time. If cancelled, the
    original theme is restored.
    """

    DEFAULT_CSS = """
    ThemeSelectScreen {
        align: center middle;
    }

    #theme-dialog {
        width: 60;
        height: auto;
        max-height: 80%;
        border: solid $primary;
        background: $background;
        padding: 1 2;
    }

    #theme-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        padding-bottom: 1;
    }

    #theme-description {
        text-align: center;
        color: $text-muted;
        padding-bottom: 1;
    }

    #theme-list {
        height: auto;
        max-height: 15;
        margin-bottom: 1;
        border: solid $secondary;
    }

    #theme-info {
        height: auto;
        margin-bottom: 1;
        padding: 1;
        border: solid $accent;
        background: $background;
    }

    #theme-info-name {
        text-align: center;
        text-style: bold;
        color: $primary;
    }

    #theme-info-mode {
        text-align: center;
        color: $secondary;
    }

    #color-swatches {
        height: auto;
        align: center middle;
        padding-top: 1;
    }

    .swatch {
        width: 8;
        height: 1;
        text-align: center;
        text-style: bold;
        margin: 0 1;
    }

    #theme-buttons {
        height: auto;
        align: center middle;
    }

    #theme-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "select", "Select"),
    ]

    def __init__(self, current_theme: str = ""):
        super().__init__()
        self.current_theme = current_theme  # Original theme to restore if cancelled
        self.selected_theme = current_theme  # Currently highlighted theme

    def compose(self) -> ComposeResult:
        with Container(id="theme-dialog"):
            yield Static("Select Theme", id="theme-title")
            yield Static("Navigate to preview colors live", id="theme-description")

            # Build option list with theme info
            options = []
            for theme in APP_THEMES:
                # Add indicator for current theme
                if theme.name == self.current_theme:
                    label = f"{theme.name} (current)"
                else:
                    label = theme.name

                # Add light/dark indicator
                mode = "light" if not theme.dark else "dark"
                options.append(Option(f"{label} [{mode}]", id=theme.name))

            yield OptionList(*options, id="theme-list")

            # Theme info panel with color swatches
            with Container(id="theme-info"):
                yield Static("", id="theme-info-name")
                yield Static("", id="theme-info-mode")
                with Horizontal(id="color-swatches"):
                    yield Static("Pri", id="swatch-primary", classes="swatch")
                    yield Static("Sec", id="swatch-secondary", classes="swatch")
                    yield Static("Acc", id="swatch-accent", classes="swatch")
                    yield Static("OK", id="swatch-success", classes="swatch")
                    yield Static("Wrn", id="swatch-warning", classes="swatch")
                    yield Static("Err", id="swatch-error", classes="swatch")

            with Horizontal(id="theme-buttons"):
                yield Button("Apply", id="btn-apply", variant="primary")
                yield Button("Cancel", id="btn-cancel", variant="default")

    def on_mount(self) -> None:
        """Set initial selection to current theme."""
        option_list = self.query_one("#theme-list", OptionList)

        # Find and highlight current theme
        for i, theme_name in enumerate(THEME_NAMES):
            if theme_name == self.current_theme:
                option_list.highlighted = i
                break

        self._update_preview()

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """Update preview when option is highlighted - applies theme live."""
        if event.option and event.option.id:
            self.selected_theme = event.option.id
            self._update_preview()

    def _update_preview(self) -> None:
        """Update the theme preview - applies theme to app for live preview."""
        theme = get_theme_by_name(self.selected_theme)

        if theme:
            # Apply theme to app for live preview
            self.app.theme = theme.name

            # Update info labels
            name_label = self.query_one("#theme-info-name", Static)
            mode_label = self.query_one("#theme-info-mode", Static)
            
            mode = "Light Mode" if not theme.dark else "Dark Mode"
            name_label.update(f"{theme.name}")
            mode_label.update(mode)

            # Update color swatches with inline styles
            self._update_swatch("#swatch-primary", theme.primary)
            self._update_swatch("#swatch-secondary", theme.secondary)
            self._update_swatch("#swatch-accent", theme.accent)
            self._update_swatch("#swatch-success", theme.success)
            self._update_swatch("#swatch-warning", theme.warning)
            self._update_swatch("#swatch-error", theme.error)

    def _update_swatch(self, selector: str, color: str) -> None:
        """Update a color swatch with the given color."""
        swatch = self.query_one(selector, Static)
        # Set background to the color, and use contrasting text
        swatch.styles.background = color
        # Use dark text for light colors, light text for dark colors
        # Simple heuristic: if the color is "bright" use dark text
        swatch.styles.color = "#000000" if self._is_light_color(color) else "#FFFFFF"

    def _is_light_color(self, hex_color: str) -> bool:
        """Check if a hex color is light (for choosing contrasting text)."""
        try:
            # Remove # prefix if present
            hex_color = hex_color.lstrip('#')
            # Parse RGB values
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            # Calculate luminance (simplified)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b)
            return luminance > 128
        except (ValueError, IndexError):
            return False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-apply":
            # Theme is already applied, just dismiss
            self.dismiss(self.selected_theme)
        elif event.button.id == "btn-cancel":
            # Restore original theme before dismissing
            self.app.theme = self.current_theme
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Cancel and close the dialog - restores original theme."""
        self.app.theme = self.current_theme
        self.dismiss(None)

    def action_select(self) -> None:
        """Apply the selected theme."""
        self.dismiss(self.selected_theme)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Apply theme when double-clicked or Enter pressed."""
        if event.option and event.option.id:
            self.dismiss(event.option.id)
