
import datetime
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




class MessageTurbo(BaseModel):
    model: Optional[str] = Field(default="gpt-3.5-turbo", description="Model name")
    messages: Optional[List] = Field(default=None, description="Messages")
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
        data = json.dumps(res)
        error = res.get('error')
        if error:
            return '出错了，请稍后重试!!!'
        data.get('choices')[0].get('message').get('content')
