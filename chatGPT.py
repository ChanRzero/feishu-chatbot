import os
import openai
import json

config = json.load(open('.env.json'))
app_id = config['openai_app_KEY']
openai.api_key = app_id
class chatGPT35:
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", default="gpt-3.5-turbo")
        self.prompt = "AI:你是一个基于" + self.model + "模型的聊天机器人"
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", default=0))
        self.frequency_penalty = float(os.getenv("OPENAI_FREQUENCY_PENALTY", default=0))
        self.presence_penalty = float(os.getenv("OPENAI_PRESENCE_PENALTY", default=0.6))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", default=2048))

    async def get_response(self, messages):
        response = openai.ChatCompletion.create(
            messages=[{'role': 'assistant',
                       'content': self.prompt}, [messages]],
            model=self.model,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
            max_tokens=self.max_tokens
        )
        return response['choices'][0].message.content
