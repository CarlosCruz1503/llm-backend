from agents.providers.prompts.text import SYSTEM_PROMPTS

def promptsFactory(output_type):
    return SYSTEM_PROMPTS.get(output_type)