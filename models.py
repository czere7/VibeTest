# from langchain_ollama import ChatOllama # TODO: do not remove - it is here for testing to not consume API limits
from typing import Sequence, Any

import openai, time
from custom_litellm import CustomChatLiteLLM
from langchain_core.prompt_values import PromptValue
from typing import Callable, TypeVar

from utils import config

T = TypeVar('T')

class ModelWrapper:
    instance = None
    model = None
    time_out_seconds = 60

    def __init__(self):
        self.generation_model_name = config.get("MODEL")
        if not self.generation_model_name:
            raise RuntimeError("MODEL is not set in .env.")

        #self.api_key = config['OPENAI_API_KEY'] or 
        #if not self.api_key:
        #    raise RuntimeError("API key is not set in .env.")

        self._set_model()

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def invoke(self, prompt_input: PromptValue | str | Sequence[Any]):
        return self._retry_model_invocation(lambda: self.model.invoke(prompt_input))

    def _set_model(self):
        #self.model = ChatOpenAI(
        #    model=self.generation_model_name,
        #    api_key=self.api_key,
        #    organization="org-ENWuCLTuWsptJcXQVIR6Exwa",
        #    timeout=self.time_out_seconds,
        #)
        self.model = CustomChatLiteLLM(
            model=self.generation_model_name,
            api_key=config['LITELLM_API_KEY'],
            api_base=config['LITELLM_BASE_URL']
        )

    def _retry_model_invocation(self, invocation_fn: Callable[[], T]) -> T:
        """
        Robust model invocation with two-tier retry mechanism.
        
        Implements a multi-tier exponential backoff pattern:
        - Inner loop: 5 quick attempts with 3-second delays (handles transient failures)
        - Outer loop: 6 extended cycles with 5-minute delays (handles rate limits/outages)
        
        Total capacity: Up to 30 attempts over ~25 minutes maximum
        
        Args:
            invocation_fn: A lambda or callable that performs the model invocation
            
        Returns:
            The result of the model invocation
            
        Raises:
            Exception: Re-raises the last exception if all retry attempts fail
        """
        max_outer_cycles = 6      # Number of outer retry cycles
        max_inner_attempts = 5    # Number of immediate retries per cycle
        short_delay = 3           # Seconds between inner retries
        long_delay = 300          # Seconds (5 minutes) between outer cycles
        
        retry_cycle = 0
        last_exception = None

        # OUTER LOOP: Cycle through extended recovery periods
        while retry_cycle < max_outer_cycles:
            
            # INNER LOOP: Quick successive retries
            for attempt in range(1, max_inner_attempts + 1):
                try:
                    # ATTEMPT: Make the actual model invocation
                    result = invocation_fn()
                    
                    # SUCCESS: Return immediately
                    return result

                except Exception as e:
                    last_exception = e
                    exception_name = type(e).__name__
                    error_message = str(e)
                    
                    # LOG: Record the failure
                    print(f"[retry_model_invocation] Request failed (attempt {attempt}/{max_inner_attempts}, "
                        f"cycle {retry_cycle + 1}/{max_outer_cycles}): {exception_name}: {error_message}")
                    
                    # DECISION POINT: Inner retry or outer cycle?
                    if attempt < max_inner_attempts:
                        # Still have inner attempts left
                        print(f"[retry_model_invocation] Retrying in {short_delay} seconds...")
                        time.sleep(short_delay)
                        continue  # Try again immediately (after short delay)
                    else:
                        # All inner attempts exhausted
                        retry_cycle += 1
                        
                        if retry_cycle < max_outer_cycles:
                            # Start new cycle after long delay
                            print(f"[retry_model_invocation] All {max_inner_attempts} retry attempts failed. "
                                f"Sleeping for {long_delay} seconds (5 minutes) before trying again "
                                f"(cycle {retry_cycle}/{max_outer_cycles})...")
                            time.sleep(long_delay)
                            break  # Exit inner loop to restart outer loop
                        else:
                            # All cycles exhausted
                            print(f"[retry_model_invocation] Maximum retry cycles ({max_outer_cycles}) reached. "
                                f"Giving up.")
                            # Re-raise the last exception
                            raise last_exception
        
        # Fallback: Should not reach here, but raise last exception if we do
        if last_exception:
            raise last_exception
        
        # Final fallback - should never reach here
        return invocation_fn()