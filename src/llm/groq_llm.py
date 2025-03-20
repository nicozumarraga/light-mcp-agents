import logging
import httpx
from typing import List, Dict, Any, Optional

from src.llm.base_llm import BaseLLM


class GroqLLM(BaseLLM):
    """
    Implementation of Groq API for the MCP Agent protocol.

    This class provides Groq-specific implementations of the LLM interface,
    including model selection and API communication.
    """

    _GROQ_API_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

    # Models available from Groq
    _GROQ_MODELS = [
        "llama-3.2-90b-vision-preview",
        "llama-3.2-8b-chat-preview",
        "llama-3.2-70b-chat",
        "mixtral-8x7b-32768",
        "gemma-7b-it"
    ]

    def __init__(self, api_key: str, model: Optional[str] = None) -> None:
        """
        Initialize the Groq LLM client.

        Args:
            api_key: Groq API key for authentication.
            model: Optional model identifier. If not provided, default_model is used.
        """
        super().__init__(api_key)
        self._model = model if model in self._GROQ_MODELS else self.default_model

    @property
    def default_model(self) -> str:
        """
        Get the default model for Groq.

        Returns:
            The default model identifier as a string.
        """
        return "llama-3.2-90b-vision-preview"

    @property
    def available_models(self) -> List[str]:
        """
        Get a list of available Groq models.

        Returns:
            List of model identifiers as strings.
        """
        return self._GROQ_MODELS.copy()

    @property
    def model(self) -> str:
        """
        Get the currently selected model.

        Returns:
            The current model identifier as a string.
        """
        return self._model

    @model.setter
    def model(self, model_name: str) -> None:
        """
        Set the model to use for requests.

        Args:
            model_name: The model identifier to use.

        Raises:
            ValueError: If the model is not supported by Groq.
        """
        if model_name not in self._GROQ_MODELS:
            raise ValueError(f"Model {model_name} is not supported by Groq. Available models: {', '.join(self._GROQ_MODELS)}")
        self._model = model_name

    def get_response(self, messages: List[Dict[str, str]],
                    temperature: float = 0.7,
                    max_tokens: int = 4096,
                    top_p: float = 1.0) -> str:
        """
        Get a response from the Groq LLM.

        Args:
            messages: A list of message dictionaries.
            temperature: Controls randomness. Higher values (e.g., 0.8) make output more random,
                         lower values (e.g., 0.2) make it more deterministic.
            max_tokens: Maximum number of tokens to generate.
            top_p: Controls diversity. 1.0 means no filtering.

        Returns:
            The LLM's response as a string.

        Raises:
            httpx.RequestError: If the request to the LLM fails.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "messages": messages,
            "model": self._model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": False,
            "stop": None,
        }

        try:
            with httpx.Client() as client:
                response = client.post(self._GROQ_API_ENDPOINT, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]

        except httpx.RequestError as e:
            error_message = f"Error getting Groq LLM response: {str(e)}"
            logging.error(error_message)

            if isinstance(e, httpx.HTTPStatusError):
                status_code = e.response.status_code
                logging.error(f"Status code: {status_code}")
                logging.error(f"Response details: {e.response.text}")

            return (
                f"I encountered an error: {error_message}. "
                "Please try again or rephrase your request."
            )
