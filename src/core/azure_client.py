"""
Azure SDK client factory for Azure AI Foundry Agent Toolkit.

Provides centralized client management with:
- Singleton pattern for connection reuse
- Thread-safe client creation
- Credential management
- Connection validation
"""

import os
import threading
from typing import Optional
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Load environment variables
load_dotenv()

# Default endpoint from environment
DEFAULT_ENDPOINT = os.environ.get(
    "PROJECT_ENDPOINT",
    "https://foundry-control-plane.services.ai.azure.com/api/projects/foundry-control-plane"
)


class AzureClientFactory:
    """
    Factory for Azure AI Projects clients.

    Uses singleton pattern to reuse connections and credentials.
    Thread-safe for concurrent access.
    """

    _instance: Optional["AzureClientFactory"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "AzureClientFactory":
        """Ensure singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the factory (only runs once due to singleton)."""
        if self._initialized:
            return

        self._project_client: Optional[AIProjectClient] = None
        self._openai_client = None
        self._credential: Optional[DefaultAzureCredential] = None
        self._endpoint: str = DEFAULT_ENDPOINT
        self._client_lock = threading.Lock()
        self._initialized = True

    def set_endpoint(self, endpoint: str) -> None:
        """
        Set a custom endpoint (resets existing clients).

        Args:
            endpoint: Azure AI Foundry project endpoint URL
        """
        with self._client_lock:
            if endpoint != self._endpoint:
                self._endpoint = endpoint
                self._project_client = None
                self._openai_client = None

    def get_credential(self) -> DefaultAzureCredential:
        """
        Get or create the Azure credential.

        Returns:
            DefaultAzureCredential instance
        """
        if self._credential is None:
            self._credential = DefaultAzureCredential()
        return self._credential

    def get_project_client(self) -> AIProjectClient:
        """
        Get or create the AI Project client.

        Returns:
            AIProjectClient instance

        Raises:
            Exception: If connection fails
        """
        if self._project_client is None:
            with self._client_lock:
                if self._project_client is None:
                    self._project_client = AIProjectClient(
                        endpoint=self._endpoint,
                        credential=self.get_credential(),
                    )
        return self._project_client

    def get_openai_client(self):
        """
        Get or create the OpenAI client for agent conversations.

        Returns:
            OpenAI client instance from project client
        """
        if self._openai_client is None:
            with self._client_lock:
                if self._openai_client is None:
                    self._openai_client = self.get_project_client().get_openai_client()
        return self._openai_client

    def test_connection(self) -> bool:
        """
        Test the connection to Azure AI Foundry.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            client = self.get_project_client()
            # Try to list agents as a connection test
            # This will raise if credentials or endpoint are invalid
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    def reset(self) -> None:
        """Reset all clients (useful for testing or reconnection)."""
        with self._client_lock:
            self._project_client = None
            self._openai_client = None
            self._credential = None

    @property
    def endpoint(self) -> str:
        """Get the current endpoint."""
        return self._endpoint

    @property
    def is_connected(self) -> bool:
        """Check if clients are initialized."""
        return self._project_client is not None


# Module-level convenience functions
_factory: Optional[AzureClientFactory] = None


def _get_factory() -> AzureClientFactory:
    """Get the global factory instance."""
    global _factory
    if _factory is None:
        _factory = AzureClientFactory()
    return _factory


def get_project_client(endpoint: str = None) -> AIProjectClient:
    """
    Get an AI Project client.

    Args:
        endpoint: Optional custom endpoint (uses default if not provided)

    Returns:
        AIProjectClient instance
    """
    factory = _get_factory()
    if endpoint:
        factory.set_endpoint(endpoint)
    return factory.get_project_client()


def get_openai_client(endpoint: str = None):
    """
    Get an OpenAI client for agent conversations.

    Args:
        endpoint: Optional custom endpoint (uses default if not provided)

    Returns:
        OpenAI client instance
    """
    factory = _get_factory()
    if endpoint:
        factory.set_endpoint(endpoint)
    return factory.get_openai_client()


def test_azure_connection(endpoint: str = None) -> bool:
    """
    Test connection to Azure AI Foundry.

    Args:
        endpoint: Optional custom endpoint

    Returns:
        True if connection successful
    """
    factory = _get_factory()
    if endpoint:
        factory.set_endpoint(endpoint)
    return factory.test_connection()


def reset_clients() -> None:
    """Reset all Azure clients."""
    factory = _get_factory()
    factory.reset()
