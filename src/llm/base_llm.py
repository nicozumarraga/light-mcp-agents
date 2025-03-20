import abc
from typing import List, Dict, Any, Optional


class BaseLLM(abc.ABC):
    """
    Base class for the augmented LLM.

    This abstract class defines the interface that all LLM implementations
    should follow to ensure compatibility with the MCP Agent protocol.
    """

    def __init__(self, api_key: str) -> None:
        """
        Initialize the LLM with an API key.

        Args:
            api_key: Authentication key for the LLM service.
        """
        self.api_key: str = api_key

    @abc.abstractmethod
    def get_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Get a response from the LLM.

        Args:
            messages: A list of message dictionaries with role and content.
                     Format: [{"role": "system", "content": "..."}, ...]

        Returns:
            The LLM's response as a string.

        Raises:
            Exception: If the request to the LLM fails.
        """
        pass

    @property
    @abc.abstractmethod
    def default_model(self) -> str:
        """
        Get the default model identifier for this LLM provider.

        Returns:
            String identifier for the default model.
        """
        pass

    @property
    @abc.abstractmethod
    def available_models(self) -> List[str]:
        """
        Get a list of available models from this LLM provider.

        Returns:
            List of model identifiers as strings.
        """
        pass
