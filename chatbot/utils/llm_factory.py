"""
utils/llm_factory.py
SEA-LION 试用版 API 调用封装
对话模型：aisingapore/Qwen-SEA-LION-v4-32B-IT
推理模型：aisingapore/Llama-SEA-LION-v3.5-70B-R
备用：Cloudflare Gemma-SEA-LION-v4（限流时自动切换）
"""
import json as _json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SEALION_BASE_URL = os.getenv("SEALION_BASE_URL", "https://api.sea-lion.ai/v1")
SEALION_API_KEY  = os.getenv("SEALION_API_KEY", "")

# Cloudflare 备用（SEA-LION试用版限流时自动切换）
CF_BASE_URL  = "https://cf-sealion.e1521205.workers.dev"

# 对话用：Triage、陪伴Agent、闲聊Agent
INSTRUCT_MODEL  = "aisingapore/Qwen-SEA-LION-v4-32B-IT"

# 推理用：专家Agent
REASONING_MODEL = "aisingapore/Llama-SEA-LION-v3.5-70B-R"


def call_sealion(system_prompt: str, user_message: str, reasoning: bool = False) -> str:
    """单轮调用"""
    return call_sealion_with_history(system_prompt, [
        {"role": "user", "content": user_message}
    ], reasoning=reasoning)


def call_sealion_with_history(system_prompt: str, messages: list, reasoning: bool = False) -> str:
    """
    带对话历史的调用
    限流时自动切换到 Cloudflare Gemma 备用
    """
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    model         = REASONING_MODEL if reasoning else INSTRUCT_MODEL

    # ── 主线：SEA-LION 试用版 ────────────────────────
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {SEALION_API_KEY}",
    }
    payload = {"model": model, "messages": full_messages}

    try:
        resp = requests.post(
            f"{SEALION_BASE_URL}/chat/completions",
            json=payload, headers=headers, timeout=30
        )
        if resp.status_code == 429:
            raise Exception("429 限流")
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        print(f"[SEA-LION] {'推理' if reasoning else '对话'}模型调用成功")
        return content

    except Exception as e:
        print(f"[SEA-LION] {e}，切换到 Cloudflare Gemma 备用")
        return _call_cloudflare_fallback(system_prompt, messages)


def _call_cloudflare_fallback(system_prompt: str, messages: list) -> str:
    """Cloudflare Gemma-SEA-LION 备用"""
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    headers = {"Content-Type": "application/json"}
    payload = {"messages": full_messages}

    try:
        resp = requests.post(
            f"{CF_BASE_URL}/chat",
            json=payload, headers=headers, timeout=30
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        print(f"[Cloudflare Gemma] 备用调用成功")
        return content
    except Exception as e:
        print(f"[Cloudflare Gemma] 也失败了：{e}")
        return "抱歉，服务暂时不可用，请稍后再试。"


def call_sealion_with_history_stream(
    system_prompt: str, messages: list, reasoning: bool = False
) -> str:
    """
    流式调用。reasoning=True 时使用推理模型并自动跳过 <think> 块输出。
    限流时自动降级为 Cloudflare 非流式备用。
    """
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    model   = REASONING_MODEL if reasoning else INSTRUCT_MODEL
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {SEALION_API_KEY}",
    }
    payload = {"model": model, "messages": full_messages, "stream": True}

    try:
        resp = requests.post(
            f"{SEALION_BASE_URL}/chat/completions",
            json=payload, headers=headers, timeout=30, stream=True
        )
        if resp.status_code == 429:
            raise Exception("429 限流")
        resp.raise_for_status()

        full_content = ""
        in_think     = reasoning   # 推理模型：进入时先抑制输出直到 </think>
        think_buf    = ""

        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8")
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                delta = _json.loads(data)["choices"][0]["delta"].get("content", "")
                if not delta:
                    continue
                if in_think:
                    think_buf += delta
                    if "</think>" in think_buf:
                        in_think = False
                        after = think_buf.split("</think>", 1)[1]
                        if after:
                            print(after, end="", flush=True)
                            full_content += after
                else:
                    print(delta, end="", flush=True)
                    full_content += delta
            except Exception:
                continue

        print()  # 换行
        return full_content

    except Exception as e:
        print(f"\n[SEA-LION] {e}，切换到 Cloudflare Gemma 备用")
        content = _call_cloudflare_fallback(system_prompt, messages)
        print(content)
        return content


def format_history_for_sealion(history: list) -> list:
    """把ChatState的history转成SEA-LION messages格式"""
    return [
        {"role": h["role"], "content": h["content"]}
        for h in history
        if h.get("role") in ["user", "assistant"] and h.get("content")
    ]
