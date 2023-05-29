import datetime
from typing import List

import httpx
from Crypto.Cipher import AES
import hashlib
import json
import base64
import aiohttp
import asyncio

import chatGPT
from chatGPT import MessageTurbo

from pydantic import BaseModel
from fastapi import FastAPI, Request, BackgroundTasks

from model import Prompt

app = FastAPI()


class AESCipher(object):
    def __init__(self, key):
        self.bs = AES.block_size
        self.key = hashlib.sha256(AESCipher.str_to_bytes(key)).digest()

    @staticmethod
    def str_to_bytes(data):
        u_type = type(b"".decode('utf8'))
        if isinstance(data, u_type):
            return data.encode('utf8')
        return data

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]

    def decrypt(self, enc):
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:]))

    def decrypt_string(self, enc):
        enc = base64.b64decode(enc)
        return self.decrypt(enc).decode('utf8')


class TokenManager():
    def __init__(self, app_id, app_secret) -> None:
        self.token = 'an_invalid_token'
        self.url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        self.req = {
            "app_id": app_id,
            "app_secret": app_secret
        }

    async def update(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers={
                'Content-Type': 'application/json; charset=utf-8'
            }, data=json.dumps(self.req), timeout=5) as response:
                data = await response.json()
                if (data["code"] == 0):
                    self.token = data["tenant_access_token"]

    def get_token(self):
        return self.token


class LarkMsgSender():
    def __init__(self, token_manager: TokenManager) -> None:
        self.prefix = "https://open.feishu.cn/open-apis/im/v1/messages/"
        self.suffix = "/reply"
        self.token_manager = token_manager

    async def send(self, msg, msg_id):
        url = self.prefix + msg_id + self.suffix
        headers = {
            'Authorization': 'Bearer ' + self.token_manager.get_token(),  # your access token
            'Content-Type': 'application/json'
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=json.dumps({
                "msg_type": "text",
                "content": json.dumps({
                    "text": msg,
                })
            })) as response:
                data = await response.json()
        if (data["code"] == 99991668 or data["code"] == 99991663):  # token expired
            await self.token_manager.update()
            await self.send(msg, msg_id)
        elif (data["code"] == 0):
            return
        else:
            print("unreachable")
            print(data)
            pass


# 获取会话历史消息
class HistoryMessages():
    def __init__(self, token_manager: TokenManager,page_size) -> None:
        self.prefix = "https://open.feishu.cn/open-apis/im/v1/messages"
        self.page_size = page_size
        self.container_id_type = "chat"
        self.token_manager = token_manager

    async def getHistoryMsg(self, start_time,end_time, chat_id):
        url = self.prefix
        headers = {
            'Authorization': 'Bearer ' + self.token_manager.get_token(),  # your access token
            'Content-Type': 'application/json'
        }
        params = {
            'container_id_type': self.container_id_type,
            'page_size': self.page_size,
            'start_time': start_time,
            'container_id': chat_id,
            'end_time':  end_time
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                data = await response.json()
        if (data["code"] == 99991668 or data["code"] == 99991663):  # token expired
            await self.token_manager.update()
            await self.getHistoryMsg(timestamp, chat_id)
        elif (data["code"] == 0):
            items = data['data']['items']
            result = []
            # 过滤出需要的响应消息
            for item in items:
                sender_type = item['sender']['sender_type']
                content = item['body']['content']
                result.append({'sender_type': sender_type, 'content': content})
            # 将消息体转换为模型需要的格式
            new_data = []
            for item in result:
                new_item = {}
                if item['sender_type'] == 'app':
                    new_item['role'] = 'assistant'
                else:
                    new_item['role'] = item['sender_type']
                new_item['content'] = json.loads(item['content'])['text']
                new_data.append(new_item)
            return new_data
        else:
            print("获取上下文失败")
            print(data)
            return


# 获取指定消息
class getTheMessage:
    def __init__(self, token_manager: TokenManager) -> None:
        self.prefix = "https://open.feishu.cn/open-apis/im/v1/messages/:"
        self.token_manager = token_manager

    async def getMsg(self, msg_id):
        url = self.prefix + msg_id
        headers = {
            'Authorization': 'Bearer ' + self.token_manager.get_token(),  # your access token
            'Content-Type': 'application/json'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.json()
        if data["code"] == 99991668 or data["code"] == 99991663:  # token expired
            await self.token_manager.update()
            await self.getMsg(msg_id)
        elif (data["code"] == 0):
            content = data['data']['items'][0]['body']['content']
            return json.loads(content)['text']
        else:
            print("获取消息失败")
            print(data)
            return


# 将下面的参数改为从json文件中读取
config = json.load(open('.env.json'))
app_id = config['app_id']
app_secret = config['app_secret']
verification_token = config['verification_token']
encryption_key = config['encryption_key']

cipher = AESCipher(encryption_key)
users_info = {}
token_manager = TokenManager(app_id=app_id, app_secret=app_secret)
sender = LarkMsgSender(token_manager)


async def completions_turbo(input: dict):
    """Get completions for the message."""
    content = None
    reply = ""
    if input['header']['token'] != verification_token:
        return

        # 检查输入中是否包含文本消息
    if 'event' in input and 'message' in input['event'] and 'content' in input['event']['message']:
        try:
            content = json.loads(input['event']['message']['content'])
            if 'text' not in content:
                reply = "抱歉，我只能接收文本消息哦"
        except ValueError:
            reply = "消息格式错误"
    if reply != "":
        await sender.send(reply, input["event"]["message"]["message_id"])
        return

    # 判断是回复信息还是新消息
    if 'event' in input and 'message' in input['event'] and 'parent_id' in input['event']['message']:
        # 回复消息，将原消息作为上下文
        # 获取上下文消息
        parent_id = input['event']['message']['parent_id']
        get_msg = getTheMessage(token_manager)
        parent_msg = await get_msg.getMsg(parent_id)
        messages = [{'role': 'user', 'content': parent_msg}]
        new_message = content['text']
        messages.append({'role': 'user', 'content': new_message})
        message = MessageTurbo(messages=messages)
        print("gpt:", reply)
        reply = await chatGPT.completions_turbo(message)


    else:  # 新消息，将历史消息作为上下文
        # 获取5分钟前的时间戳
        timestamp = int(input["event"]["message"]["create_time"])  # 给定时间戳
        dt = datetime.datetime.fromtimestamp(timestamp / 1000)  # 将时间戳转换为 datetime 对象
        ago = dt - datetime.timedelta(minutes=10)  # 计算5分钟前的时间
        start_time = int(ago.timestamp())  # 将时间转换为时间戳
        now = dt - datetime.timedelta(seconds=1)  # 计算1秒前的时间
        end_time = int(now.timestamp())  # 将时间转换为时间戳

        # 获取会话id
        chatId = input['event']['message']['chat_id']
        # 获取一个小时之内的上下文消息，默认10条
        history_msg = HistoryMessages(token_manager, 10)
        his_messages = await history_msg.getHistoryMsg(start_time, end_time, chatId)
        # 给机器人知道当前时间
        now = datetime.datetime.now()
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
        messages = [{'role': 'system', 'content': '你是一个基于gpt-3.5-turbo模型的聊天机器人'}]
        newMessage = content['text']
        print('newMessage', newMessage)
        if his_messages is not None:
            messages.extend(his_messages)
        messages.append({'role': 'user', 'content': newMessage})
        print('messages', messages)
        message = MessageTurbo(messages=messages)
        reply = await chatGPT.completions_turbo(message)
        print("gpt:", reply)
    await sender.send(reply, input["event"]["message"]["message_id"])


class LarkMsgType(BaseModel):
    encrypt: str


processed_message_ids = set()


@app.post("/feishu")
async def process(message: LarkMsgType, request: Request, background_tasks: BackgroundTasks):
    plaintext = json.loads(cipher.decrypt_string(message.encrypt))  # 对encrypt解密
    print("plaintext:", plaintext)
    # plaintext：
    #   "challenge": "ajls384kdjx98XX", // 应用需要在响应中原样返回的值
    #   "token": "xxxxxx", // 即VerificationToken
    #   "type": "url_verification" // 表示这是一个验证请求

    # 接收到客户端消息，如果有challenge就响应challenge
    if 'challenge' in plaintext:  # url verification
        return {'challenge': plaintext['challenge']}

    message_id = plaintext['event']['message']['message_id']
    if message_id not in processed_message_ids:
        # 将message_id加入到已处理列表，避免下次重复处理
        processed_message_ids.add(message_id)
        background_tasks.add_task(completions_turbo, plaintext)  # reply in background

    return {'message': 'ok'}  # 接受到消息后，立即返回ok，避免客户端重试
