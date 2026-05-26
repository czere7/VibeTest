# from langchain_ollama import ChatOllama # TODO: do not remove - it is here for testing to not consume API limits
#from langchain_openai import ChatOpenAI
#from langchain_litellm import ChatLiteLLM
from custom_litellm import CustomChatLiteLLM

from utils import config

generation_model_name = config.get("MODEL")
if not generation_model_name:
    raise RuntimeError("MODEL is not set in .env.")

# TODO: do not remove - it is here for testing to not consume API limits
# common_generation_model = ChatOllama(
#     model=generation_model_name,
#     reasoning=True,
# )

#common_generation_model = ChatOpenAI(
#    model=generation_model_name,
#    api_key=config['OPENAI_API_KEY'],
#    organization="org-ENWuCLTuWsptJcXQVIR6Exwa",
#)

common_generation_model = CustomChatLiteLLM(
    model=generation_model_name,
    api_key=config['LITELLM_API_KEY'],
    api_base=config['LITELLM_BASE_URL']
)