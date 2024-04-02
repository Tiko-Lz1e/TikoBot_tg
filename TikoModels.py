import dashscope
from openai import OpenAI
from http import HTTPStatus
from dashscope.api_entities.dashscope_response import Role

class Tikogpt_chat():
    def __init__(self, model, history, clint):
        self.model = model
        self.history = history
        self.client = clint

    def send_message(self, msg, role='user', stream=False):
        self.history.append({'role': role, 'content': msg})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.history,
            stream=stream)
        return response
    
    def add_history(self, role, msg):
        self.history.append({'role': role, 'content': msg})

class Tikogpt():
    def __init__(self, api_key, base_url=None, model="gpt-3.5-turbo"):
        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_content(self, prompt, stream=False):
        message = [{"role": "user", "content": prompt}]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=message,
            stream=stream
        )
        return response

    def start_chat(self, history=[{'role': 'system', 'content': '您好，现在是工作最为紧张的时间，所以我需要你的帮助，我现在正在使用telegram平台跟你聊天，接下来的内容请以朋友聊天的风格回复我，其中可以根据内容附带少量的emoji，但请不要使用markdown语法，谢谢。'}]):
        return Tikogpt_chat(self.model, history, self.client)
    
class Tikoqwen_chat():
    def __init__(self, model, history=[]):
        self.model = model
        self.history = history
    
    def send_message(self, msg, stream=False):
        self.history.append({'role': Role.USER, 'content': msg})
        response = dashscope.Generation.call(
            self.model,
            messages=self.history,
            stream=stream,
            result_format='message')
        return response
    
    def add_history(self, role, msg):
        self.history.append({'role': role, 'content': msg})

class Tikoqwen():
    def __init__(self, api_key, model="qwen-plus"):
        dashscope.api_key = api_key
        self.model = model
        self.chat = None

    def generate_content(self, prompt, stream=False):
        response = dashscope.Generation.call(
            model=self.model,
            prompt=prompt,
            stream=stream,
            result_format='message')
        return response
    
    def start_chat(self, history=[]):
        self.chat = Tikoqwen_chat(self.model, history)
        return self.chat
    
    def generate_image(self, prompt, n=1, size="1024*1024", response_format="url"):
        response = dashscope.ImageSynthesis.call(
            model=self.model,
            prompt=prompt,
            n=n,
            size=size,
            response_format=response_format)
        return response