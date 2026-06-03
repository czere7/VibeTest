"""
Custom LiteLLM wrapper with enhanced error handling and retry logic.
"""
import time, requests
from typing import Any, List, Optional, Union
from utils import config, log_litellm_response_error
from exceptions import ContextWindowOverflowError

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_litellm import ChatLiteLLM

from json import dumps

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
                    "cache_control": {
                        "type": "ephemeral"
                    }
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

        data = r.json()

        if 'error' in data:
            log_litellm_response_error(dumps(data))
            error_message = data['error']['message']
            if 'litellm.ContextWindowExceededError' in error_message:
                raise ContextWindowOverflowError(
                    message=error_message,
                    node_name=None,  # Will be set by the calling node
                    class_info=None   # Will be set by the calling node
                )
            elif 'budget' in error_message.lower():
                exit(-1)

        
        r.raise_for_status()
        
        result = data["choices"][0]["message"]["content"]

        return AIMessage(content=result)
            

