import os

MSG_LIST_LIMIT = int(os.getenv("MSG_LIST_LIMIT", default=20))

class Prompt:
    def __init__(self):
        self.msg_list = []

    def add_msg(self, new_msg):
        if len(self.msg_list) >= MSG_LIST_LIMIT:  # 上下文超过MSG_LIST_LIMIT就删除第一条消息
            self.remove_msg()
        self.msg_list.append(new_msg)

    def remove_msg(self):
        self.msg_list.pop(0)

    def generate_prompt(self):
        return '\n'.join(self.msg_list)