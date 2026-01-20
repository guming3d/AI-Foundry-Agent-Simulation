"""
Environment validation for Microsoft Foundry Agent Toolkit.

Validates required environment variables and provides setup guidance.
"""

import os
from pathlib import Path
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class EnvValidationResult:
    """Result of environment validation."""
    is_valid: bool
    missing_vars: list
    error_message: str = ""
    setup_guide: str = ""


class EnvValidator:
    """Validates environment configuration."""

    REQUIRED_VARS = ["PROJECT_ENDPOINT"]
    ENV_FILE = Path(".env")
    ENV_EXAMPLE_FILE = Path(".env.example")

    @classmethod
    def validate(cls) -> EnvValidationResult:
        """
        Validate that all required environment variables are set.

        Returns:
            EnvValidationResult with validation status and guidance
        """
        missing_vars = []

        for var in cls.REQUIRED_VARS:
            value = os.getenv(var)
            if not value or value.strip() == "":
                missing_vars.append(var)

        if missing_vars:
            error_msg = cls._build_error_message(missing_vars)
            setup_guide = cls._build_setup_guide()
            return EnvValidationResult(
                is_valid=False,
                missing_vars=missing_vars,
                error_message=error_msg,
                setup_guide=setup_guide
            )

        return EnvValidationResult(is_valid=True, missing_vars=[])

    @classmethod
    def _build_error_message(cls, missing_vars: list) -> str:
        """Build error message for missing variables."""
        vars_list = ", ".join(missing_vars)
        return f"Missing required environment variable(s): {vars_list}"

    @classmethod
    def _build_setup_guide(cls) -> str:
        """Build setup guide text."""
        env_exists = cls.ENV_FILE.exists()
        example_exists = cls.ENV_EXAMPLE_FILE.exists()

        guide = "Setup Guide:\n\n"

        if not env_exists:
            guide += "1. Create a .env file in the project root\n"
            if example_exists:
                guide += "   You can copy from .env.example:\n"
                guide += "   $ cp .env.example .env\n\n"
            else:
                guide += "   $ touch .env\n\n"
        else:
            guide += "1. Your .env file exists but needs configuration\n\n"

        guide += "2. Add your Microsoft Foundry project endpoint:\n"
        guide += "   PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project\n\n"

        guide += "3. How to find your project endpoint:\n"
        guide += "   a) Go to https://ai.azure.com\n"
        guide += "   b) Open your AI Foundry project\n"
        guide += "   c) Go to Settings → Project details\n"
        guide += "   d) Copy the 'Project endpoint' URL\n\n"

        guide += "4. Required format:\n"
        guide += "   PROJECT_ENDPOINT=https://[your-project].services.ai.azure.com/api/projects/[project-id]\n\n"

        guide += "5. Save the .env file and restart the application\n"

        return guide

    @classmethod
    def update_env_file(cls, project_endpoint: str) -> Tuple[bool, str]:
        """
        Update or create .env file with PROJECT_ENDPOINT.

        Args:
            project_endpoint: The Microsoft Foundry project endpoint URL

        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate endpoint format
            if not project_endpoint.startswith("https://"):
                return False, "Project endpoint must start with https://"

            if "services.ai.azure.com" not in project_endpoint:
                return False, "Invalid endpoint format. Should contain 'services.ai.azure.com'"

            # Read existing .env or create new
            existing_lines = []
            if cls.ENV_FILE.exists():
                with open(cls.ENV_FILE, 'r') as f:
                    existing_lines = f.readlines()

            # Update or append PROJECT_ENDPOINT
            updated = False
            new_lines = []

            for line in existing_lines:
                if line.strip().startswith("PROJECT_ENDPOINT="):
                    new_lines.append(f"PROJECT_ENDPOINT={project_endpoint}\n")
                    updated = True
                else:
                    new_lines.append(line)

            if not updated:
                new_lines.append(f"PROJECT_ENDPOINT={project_endpoint}\n")

            # Write back to file
            with open(cls.ENV_FILE, 'w') as f:
                f.writelines(new_lines)

            # Reload environment from .env file
            cls.reload_environment()

            # Update environment variable for current session (redundant but ensures it's set)
            os.environ["PROJECT_ENDPOINT"] = project_endpoint

            # Update Azure client factory with new endpoint
            cls._update_azure_client(project_endpoint)

            return True, f"Successfully updated {cls.ENV_FILE}"

        except Exception as e:
            return False, f"Failed to update .env file: {str(e)}"

    @classmethod
    def _update_azure_client(cls, endpoint: str) -> None:
        """
        Update Azure client factory with new endpoint.

        Args:
            endpoint: The new project endpoint
        """
        try:
            # Import here to avoid circular dependency
            from .azure_client import _get_factory

            factory = _get_factory()
            factory.set_endpoint(endpoint)
            factory.reset()  # Reset clients to force reconnection with new endpoint
        except Exception as e:
            # Not critical if this fails, user can restart
            print(f"Warning: Could not update Azure client: {e}")

    @classmethod
    def get_endpoint(cls) -> Optional[str]:
        """Get the current PROJECT_ENDPOINT value."""
        return os.getenv("PROJECT_ENDPOINT")

    @classmethod
    def is_configured(cls) -> bool:
        """Check if environment is properly configured."""
        return cls.validate().is_valid

    @classmethod
    def reload_environment(cls) -> None:
        """
        Reload environment variables from .env file.

        This is useful after updating the .env file to ensure
        all environment variables are current.
        """
        try:
            from dotenv import load_dotenv
            # Reload with override=True to update existing variables
            load_dotenv(override=True)
        except Exception as e:
            print(f"Warning: Could not reload environment: {e}")


def validate_environment() -> EnvValidationResult:
    """
    Convenience function to validate environment.

    Returns:
        EnvValidationResult
    """
    return EnvValidator.validate()


def is_env_configured() -> bool:
    """
    Check if environment is configured.

    Returns:
        True if all required variables are set
    """
    return EnvValidator.is_configured()


def get_setup_guide() -> str:
    """
    Get the setup guide text.

    Returns:
        Setup guide string
    """
    result = EnvValidator.validate()
    return result.setup_guide
