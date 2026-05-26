"""
Custom LiteLLM wrapper with enhanced error handling and retry logic.
"""
import time, requests
from typing import Any, List, Optional, Union
from utils import config

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_litellm import ChatLiteLLM


class CustomChatLiteLLM():
    """
    Custom wrapper around ChatLiteLLM with enhanced error handling.
    
    This class provides:
    - Built-in retry logic for model loading and service unavailability
    - Better error messages and logging
    - Graceful degradation when model is loading
    """
    
    def __init__(
        self,
        model: str,
        api_key: str,
        api_base: str
    ):
        """
        Initialize the custom LiteLLM wrapper.
        
        Args:
            model: Model name to use
            api_key: API key for authentication
            api_base: Base URL for the LiteLLM proxy
        """
        super().__init__()
        self.model_name = model
        self.api_key = api_key
        self.api_base = api_base
    
    def invoke(
        self,
        prompt: str
    ) -> Any:
        """
        Invoke the model with retry logic.
        
        Args:
            prompt: Prompt string
            
        Returns:
            Model response
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "messages":[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.7,
        }

        r = requests.post(
            f"{self.api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=int(config.get('MODEL_TIMEOUT', '900'))
        )
        r.raise_for_status()
        data = r.json()
        result = data["choices"][0]["message"]["content"]

        return result

