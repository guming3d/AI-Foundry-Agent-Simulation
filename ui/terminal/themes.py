"""
Custom themes for Azure AI Foundry Agent Toolkit TUI.

Provides multiple theme options following Textual's theme system:
- Cyber Ops: High-tech neon palette for a technical vibe
- Azure Dark: Azure branding colors
- Azure Light: Light theme variant
- Nord: Popular dark theme with cool colors
- High Contrast: Accessibility-focused high contrast theme

Usage:
    from ui.terminal.themes import register_app_themes, APP_THEMES

    class MyApp(App):
        def on_mount(self):
            register_app_themes(self)
            self.theme = "azure-dark"
"""

from textual.theme import Theme


# Cyber Ops Theme - High-tech, neon-inspired palette
CYBER_OPS = Theme(
    name="cyber-ops",
    primary="#23C9FF",       # Neon cyan
    secondary="#7CFF6B",     # Neon green
    accent="#FFB454",        # Amber accent
    foreground="#DCE7F8",    # Cool light text
    background="#0B0E12",    # Deep graphite
    surface="#111722",       # Panel surface
    panel="#1B2332",         # Panel background
    success="#43F2A1",       # Mint green
    warning="#FFC857",       # Bright amber
    error="#FF5C5C",         # Neon red
    dark=True,
    variables={
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#23C9FF",
        "footer-description-foreground": "#9AA8C2",
        "input-selection-background": "#23C9FF 35%",
        "input-cursor-foreground": "#23C9FF",
        "button-color-foreground": "#DCE7F8",
    },
)


# Azure Dark Theme
# Uses Azure's brand colors: #0078D4 (Azure Blue), with complementary colors
AZURE_DARK = Theme(
    name="azure-dark",
    primary="#0078D4",       # Azure Blue
    secondary="#50E6FF",     # Azure Cyan
    accent="#9B4DCA",        # Purple accent
    foreground="#E6E6E6",    # Light gray text
    background="#1E1E1E",    # VS Code dark background
    surface="#252526",       # Slightly lighter surface
    panel="#333333",         # Panel background
    success="#4EC9B0",       # Teal green
    warning="#DCDCAA",       # Yellow
    error="#F14C4C",         # Red
    dark=True,
    variables={
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#0078D4",
        "footer-description-foreground": "#BBBBBB",
        "input-selection-background": "#0078D4 40%",
        "input-cursor-foreground": "#0078D4",
        "button-color-foreground": "#FFFFFF",
    },
)


# Azure Light Theme
AZURE_LIGHT = Theme(
    name="azure-light",
    primary="#0078D4",       # Azure Blue
    secondary="#005A9E",     # Darker Azure Blue
    accent="#8661C5",        # Purple accent
    foreground="#1E1E1E",    # Dark text
    background="#FFFFFF",    # White background
    surface="#F3F3F3",       # Light gray surface
    panel="#E8E8E8",         # Panel background
    success="#107C10",       # Green
    warning="#8E562E",       # Orange/brown
    error="#D13438",         # Red
    dark=False,
    variables={
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#0078D4",
        "footer-description-foreground": "#444444",
        "input-selection-background": "#0078D4 30%",
        "input-cursor-foreground": "#0078D4",
        "button-color-foreground": "#FFFFFF",
    },
)


# Nord Theme - Cool, bluish dark theme
NORD = Theme(
    name="nord",
    primary="#88C0D0",       # Nord Frost
    secondary="#81A1C1",     # Nord Blue
    accent="#B48EAD",        # Nord Purple
    foreground="#ECEFF4",    # Snow Storm
    background="#2E3440",    # Polar Night
    surface="#3B4252",       # Lighter Polar Night
    panel="#434C5E",         # Panel
    success="#A3BE8C",       # Nord Green
    warning="#EBCB8B",       # Nord Yellow
    error="#BF616A",         # Nord Red
    dark=True,
    variables={
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#88C0D0",
        "footer-description-foreground": "#D8DEE9",
        "input-selection-background": "#81A1C1 35%",
        "input-cursor-foreground": "#88C0D0",
    },
)


# Gruvbox Dark Theme - Warm, retro aesthetic
GRUVBOX_DARK = Theme(
    name="gruvbox",
    primary="#83A598",       # Gruvbox Aqua
    secondary="#FABD2F",     # Gruvbox Yellow
    accent="#D3869B",        # Gruvbox Purple
    foreground="#EBDBB2",    # Gruvbox Light
    background="#282828",    # Gruvbox Background
    surface="#3C3836",       # Gruvbox Surface
    panel="#504945",         # Gruvbox Panel
    success="#B8BB26",       # Gruvbox Green
    warning="#FE8019",       # Gruvbox Orange
    error="#FB4934",         # Gruvbox Red
    dark=True,
    variables={
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#83A598",
        "footer-description-foreground": "#BDAE93",
        "input-selection-background": "#83A598 35%",
        "input-cursor-foreground": "#83A598",
    },
)


# Tokyo Night Theme - Modern dark theme
TOKYO_NIGHT = Theme(
    name="tokyo-night",
    primary="#7AA2F7",       # Blue
    secondary="#BB9AF7",     # Purple
    accent="#F7768E",        # Pink/Red accent
    foreground="#C0CAF5",    # Light foreground
    background="#1A1B26",    # Dark background
    surface="#24283B",       # Surface
    panel="#414868",         # Panel
    success="#9ECE6A",       # Green
    warning="#E0AF68",       # Yellow
    error="#F7768E",         # Red/Pink
    dark=True,
    variables={
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#7AA2F7",
        "footer-description-foreground": "#A9B1D6",
        "input-selection-background": "#7AA2F7 30%",
        "input-cursor-foreground": "#7AA2F7",
    },
)


# High Contrast Theme - Accessibility focused
HIGH_CONTRAST = Theme(
    name="high-contrast",
    primary="#00FFFF",       # Cyan
    secondary="#FFFF00",     # Yellow
    accent="#FF00FF",        # Magenta
    foreground="#FFFFFF",    # Pure white
    background="#000000",    # Pure black
    surface="#0A0A0A",       # Near black
    panel="#1A1A1A",         # Dark gray
    success="#00FF00",       # Pure green
    warning="#FFFF00",       # Yellow
    error="#FF0000",         # Pure red
    dark=True,
    variables={
        "block-cursor-text-style": "bold reverse",
        "footer-key-foreground": "#00FFFF",
        "footer-description-foreground": "#FFFFFF",
        "input-selection-background": "#00FFFF 50%",
        "input-cursor-foreground": "#00FFFF",
    },
)


# Solarized Dark Theme - Classic color scheme
SOLARIZED_DARK = Theme(
    name="solarized-dark",
    primary="#268BD2",       # Solarized Blue
    secondary="#2AA198",     # Solarized Cyan
    accent="#D33682",        # Solarized Magenta
    foreground="#839496",    # Solarized Base0
    background="#002B36",    # Solarized Base03
    surface="#073642",       # Solarized Base02
    panel="#094959",         # Between base02 and base01
    success="#859900",       # Solarized Green
    warning="#B58900",       # Solarized Yellow
    error="#DC322F",         # Solarized Red
    dark=True,
    variables={
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#268BD2",
        "footer-description-foreground": "#93A1A1",
        "input-selection-background": "#268BD2 35%",
        "input-cursor-foreground": "#268BD2",
    },
)


# Solarized Light Theme
SOLARIZED_LIGHT = Theme(
    name="solarized-light",
    primary="#268BD2",       # Solarized Blue
    secondary="#2AA198",     # Solarized Cyan
    accent="#D33682",        # Solarized Magenta
    foreground="#657B83",    # Solarized Base00
    background="#FDF6E3",    # Solarized Base3
    surface="#EEE8D5",       # Solarized Base2
    panel="#DDD6C3",         # Slightly darker
    success="#859900",       # Solarized Green
    warning="#B58900",       # Solarized Yellow
    error="#DC322F",         # Solarized Red
    dark=False,
    variables={
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#268BD2",
        "footer-description-foreground": "#586E75",
        "input-selection-background": "#268BD2 25%",
        "input-cursor-foreground": "#268BD2",
    },
)


# Dracula Theme - Popular dark theme
DRACULA = Theme(
    name="dracula",
    primary="#BD93F9",       # Dracula Purple
    secondary="#8BE9FD",     # Dracula Cyan
    accent="#FF79C6",        # Dracula Pink
    foreground="#F8F8F2",    # Dracula Foreground
    background="#282A36",    # Dracula Background
    surface="#44475A",       # Dracula Current Line
    panel="#6272A4",         # Dracula Comment
    success="#50FA7B",       # Dracula Green
    warning="#FFB86C",       # Dracula Orange
    error="#FF5555",         # Dracula Red
    dark=True,
    variables={
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#BD93F9",
        "footer-description-foreground": "#F8F8F2",
        "input-selection-background": "#BD93F9 35%",
        "input-cursor-foreground": "#BD93F9",
    },
)


# List of all custom themes for iteration
APP_THEMES = [
    CYBER_OPS,
    AZURE_DARK,
    AZURE_LIGHT,
    NORD,
    GRUVBOX_DARK,
    TOKYO_NIGHT,
    DRACULA,
    SOLARIZED_DARK,
    SOLARIZED_LIGHT,
    HIGH_CONTRAST,
]

# Theme names for easy access
THEME_NAMES = [theme.name for theme in APP_THEMES]

# Default theme
DEFAULT_THEME = "cyber-ops"


def register_app_themes(app) -> None:
    """
    Register all custom themes with a Textual App instance.

    Args:
        app: The Textual App instance to register themes with.

    Example:
        def on_mount(self):
            register_app_themes(self)
            self.theme = "azure-dark"
    """
    for theme in APP_THEMES:
        app.register_theme(theme)


def get_theme_by_name(name: str) -> Theme | None:
    """
    Get a theme by its name.

    Args:
        name: The name of the theme to retrieve.

    Returns:
        The Theme object if found, None otherwise.
    """
    for theme in APP_THEMES:
        if theme.name == name:
            return theme
    return None


def get_next_theme(current_theme: str) -> str:
    """
    Get the next theme name in the rotation.

    Args:
        current_theme: The name of the current theme.

    Returns:
        The name of the next theme in the list.
    """
    try:
        current_index = THEME_NAMES.index(current_theme)
        next_index = (current_index + 1) % len(THEME_NAMES)
        return THEME_NAMES[next_index]
    except ValueError:
        # If current theme not found, return the default
        return DEFAULT_THEME
