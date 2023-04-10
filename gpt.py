import os
import requests
import time
import json

if not os.path.isfile("api_key"):
    print("Please put the api_key in 'api_key' file")
    exit()
api_key = open("api_key").read().strip()
if not api_key:
    print("Please put the api_key in 'api_key' file")
    exit()

proxies = {}
header = {"Authorization": f"Bearer {api_key}"}
url = "https://api.openai.com/v1"


class ChatGPT:

    def __init__(self, settings: str = "") -> None:
        self.content = []
        if settings:
            self.content.append({"role": "system", "content": settings})

    def add_user_talk(self, text):
        self.content.append({"role": "user", "content": text})

    def add_gpt_reply(self, text):
        self.content.append({"role": "assistant", "content": text})

    def __str__(self) -> str:
        role_map = {
            "system": "设定",
            "user": "用户",
            "assistant": "讲述人",
        }
        return "\n===============================\n".join(
            [f"{role_map[x['role']]}: {x['content']}" for x in self.content]
        )

    @staticmethod
    def get_single(text: str) -> str:
        path = "/chat/completions"
        body = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": text}],
        }
        res = requests.post(
            url + path, headers=header, json=body, timeout=15, proxies=proxies
        )
        try:
            return res.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return res.text

    def get_chat_stream(
        self,
        text: str,
        max_time=60,
        max_tokens=2000,
        watch_output=False,
        model="gpt-4",
        yield_time=0.0,
    ):
        path = "/chat/completions"
        self.add_user_talk(text)
        body = {
            "model": model,
            "messages": self.content,
            "stream": True,
            "max_tokens": max_tokens,
        }
        res = requests.post(
            url + path,
            headers=header,
            json=body,
            proxies=proxies,
            stream=True,
            timeout=10,
        )
        res_text = ""
        start_time = time.time()
        single_line_time = start_time
        for line in res.iter_lines():
            # filter out keep-alive new lines
            if line:
                decoded_line = line.decode("utf-8")
                if decoded_line.startswith("data:") and not decoded_line.endswith(
                    "[DONE]"
                ):
                    data = json.loads(decoded_line[5:].strip())
                    if "content" in data["choices"][0]["delta"]:
                        tmp_res = data["choices"][0]["delta"]["content"]
                        if not res_text and len(tmp_res.strip()) == 0:
                            continue
                        res_text += tmp_res
                        if watch_output:
                            print(tmp_res, end="", flush=True)
                        if yield_time and time.time() - single_line_time > yield_time:
                            yield res_text.strip()
                            single_line_time = time.time()
            if time.time() - start_time > max_time:
                if watch_output:
                    print("\n[Generate time exceeded]", end="")
                break
        self.add_gpt_reply(res_text.strip())
        return res_text.strip()


if __name__ == "__main__":
    chat = ChatGPT()
    while text := input("[Input]"):
        print("")
        try:
            chat.get_chat_stream(text, watch_output=True)
        except requests.exceptions.Timeout:
            print("[Request timeout]", end="")
        except requests.exceptions.ConnectionError as e:
            print(f"[Connection error]{repr(e)}", end="")
        except Exception as e:
            print(f"[Exception occur]{repr(e)}", end="")
        print("\n")
