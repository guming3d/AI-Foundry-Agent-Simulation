"""
Environment setup screen for the Textual TUI application.

Guides users through initial environment configuration.
"""

import asyncio
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Input, Label
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual import work

from src.core.env_validator import EnvValidator


class SetupScreen(Screen):
    """Screen for environment setup and configuration."""

    BINDINGS = [
        ("escape", "go_home", "Back"),
        ("s", "save_config", "Save"),
    ]

    CSS = """
    SetupScreen {
        align: center middle;
    }

    #setup-container {
        width: 80%;
        max-width: 100;
        height: auto;
        border: solid $accent;
        background: $surface;
        padding: 2;
    }

    .setup-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }

    .guide-text {
        color: $text;
        margin-bottom: 1;
    }

    .input-label {
        color: $text-muted;
        margin-top: 1;
        margin-bottom: 1;
    }

    #endpoint-input {
        margin-bottom: 1;
    }

    #status-message {
        color: $success;
        text-align: center;
        margin-top: 1;
    }

    #button-bar {
        align: center middle;
        margin-top: 1;
    }

    .guide-section {
        border: solid $primary;
        padding: 1;
        margin: 1 0;
        background: $boost;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="setup-container"):
            yield Static(
                "⚠️  Environment Configuration Required",
                classes="setup-title"
            )

            # Show validation errors
            validation = EnvValidator.validate()
            if not validation.is_valid:
                yield Static(
                    f"❌ {validation.error_message}",
                    classes="guide-text"
                )

            # Setup guide in a scrollable container
            with ScrollableContainer(classes="guide-section"):
                yield Static(
                    self._format_guide(),
                    classes="guide-text",
                    markup=False
                )

            # Input section
            yield Label("Enter your Microsoft Foundry Project Endpoint:", classes="input-label")
            yield Input(
                placeholder="https://your-project.services.ai.azure.com/api/projects/your-project",
                id="endpoint-input"
            )

            yield Static("", id="status-message")

            # Buttons
            with Horizontal(id="button-bar"):
                yield Button("Save Configuration [S]", id="btn-save", variant="primary")
                yield Button("Back to Home", id="btn-back", variant="default")

    def _format_guide(self) -> str:
        """Format the setup guide text."""
        guide = EnvValidator._build_setup_guide()
        return guide

    def on_mount(self) -> None:
        """Initialize the screen."""
        # Pre-fill with existing endpoint if available
        existing_endpoint = EnvValidator.get_endpoint()
        if existing_endpoint:
            input_widget = self.query_one("#endpoint-input", Input)
            input_widget.value = existing_endpoint

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-save":
            self.action_save_config()
        elif button_id == "btn-back":
            # Navigate to home screen (handles empty screen stack case)
            self.app.switch_screen("home")

    def action_go_home(self) -> None:
        """Navigate to home screen."""
        self.app.switch_screen("home")

    @work
    async def action_save_config(self) -> None:
        """Save the configuration to .env file."""
        input_widget = self.query_one("#endpoint-input", Input)
        status_widget = self.query_one("#status-message", Static)

        endpoint = input_widget.value.strip()

        if not endpoint:
            status_widget.update("❌ Please enter a project endpoint")
            status_widget.styles.color = "red"
            return

        # Update .env file
        success, message = EnvValidator.update_env_file(endpoint)

        if success:
            status_widget.update(f"✅ {message}")
            status_widget.styles.color = "green"
            self.notify(
                "Environment configured successfully! You can now use the application.",
                severity="information",
                timeout=5
            )
            # Wait a moment then navigate to home screen
            await asyncio.sleep(1)
            # Use switch_screen to replace setup with home (handles empty screen stack)
            self.app.switch_screen("home")
        else:
            status_widget.update(f"❌ {message}")
            status_widget.styles.color = "red"
            self.notify(f"Failed: {message}", severity="error")
