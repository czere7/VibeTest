# from langchain_ollama import ChatOllama # TODO: do not remove - it is here for testing to not consume API limits
from typing import Sequence, Any

import openai
from langchain_core.prompt_values import PromptValue
from langchain_openai import ChatOpenAI

from utils import config

class ModelWrapper:
    instance = None
    model = None
    time_out_seconds = 60

    def __init__(self):
        self.generation_model_name = config.get("MODEL")
        if not self.generation_model_name:
            raise RuntimeError("MODEL is not set in .env.")

        self.api_key = config['OPENAI_API_KEY']
        if not self.api_key:
            raise RuntimeError("API key is not set in .env.")

        self._set_model()

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def invoke(self, prompt_input: PromptValue | str | Sequence[Any]):
        while self.time_out_seconds < int(config.get("MAX_LLM_TIMEOUT", 60)):
            try:
                return self.model.invoke(prompt_input)
            except openai.APIConnectionError:
                self._handle_timeout()
        raise TimeoutError("Timeout exceeded maximum allowed value")

    def _set_model(self):
        self.model = ChatOpenAI(
            model=self.generation_model_name,
            api_key=self.api_key,
            organization="org-ENWuCLTuWsptJcXQVIR6Exwa",
            timeout=self.time_out_seconds,
        )

    def _handle_timeout(self):
        print(f"[TIMEOUT]: timeout value of {self.time_out_seconds} seconds has been exceeded.")
        self.time_out_seconds += 60
        self._set_model()
