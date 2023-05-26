import os
from typing import Optional, List
from pydantic import BaseModel, Field

import httpx
import openai
import json

# 优先读取环境变量
API_KEY = os.environ.get('ChatGPT_API_KEY')
# 如果环境变量为空，则读取 config.yaml 文件
if API_KEY is None:
    config = json.load(open('.env.json'))
    API_KEY = config['openai_app_KEY']

openai.api_key = API_KEY


class chatGPT35:
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", default="gpt-3.5-turbo")
        self.prompt = "AI:你是一个基于" + self.model + "模型的聊天机器人"
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", default=0))
        self.frequency_penalty = float(os.getenv("OPENAI_FREQUENCY_PENALTY", default=0))
        self.presence_penalty = float(os.getenv("OPENAI_PRESENCE_PENALTY", default=0.6))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", default=2048))

    def get_response(self, messages):
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


class ChatMessageTurbo(BaseModel):
    role: Optional[str] = Field(default="user", description="Role")
    content: str = Field(..., description="Content")


class MessageTurbo(BaseModel):
    model: Optional[str] = Field(default="gpt-3.5-turbo", description="Model name")
    messages: Optional[List[ChatMessageTurbo]] = Field(default=None, description="Messages")
    max_tokens: Optional[int] = Field(default=2048, description="Stop sequence")
    temperature: Optional[float] = Field(default=0.5, description="Temperature")
    frequency_penalty: Optional[float] = Field(default=0.0, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(default=0.0, description="Presence penalty")


async def completions_turbo(message):
    """Get completions for the message."""
    # print('message:', message)
    url = "https://api.openai.com/v1/chat/completions"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=message.dict(),
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=60,
        )
        res = response.json()
        print('response:', res)
        error = res.get('error')
        if error:
            res['error']['message'] = '出错了，请稍后重试!!!'
        res.get('choices')[0].get('message').get('content')
