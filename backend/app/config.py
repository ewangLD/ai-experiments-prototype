import os

from dotenv import load_dotenv
import ldclient
from ldclient.config import Config
from ldobserve import ObservabilityConfig, ObservabilityPlugin
from ldai import LDAIClient
from openai import OpenAI

load_dotenv()

# --- LaunchDarkly SDK with Observability ---

ldclient.set_config(
    Config(
        os.environ["LAUNCHDARKLY_SDK_KEY"],
        plugins=[
            ObservabilityPlugin(
                ObservabilityConfig(
                    service_name="ld-support-chatbot",
                    service_version="0.1.0",
                )
            )
        ],
    )
)

ld_client = ldclient.get()
ai_client = LDAIClient(ld_client)

# --- OpenAI client (auto-instrumented by ObservabilityPlugin's OpenLLMetry) ---

openai_client = OpenAI()
