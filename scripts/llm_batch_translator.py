import os
import json
import time

# This is a sample script demonstrating how you can automate the translation of 
# the remaining 78 MBTI items into SJT (Situational Judgement Test) items
# using a Large Language Model API (e.g. DeepSeek, OpenAI, etc.).

# 1. Load the original MBTI items
with open("../backend/data/ipip/mbti_88_items.json", "r", encoding="utf-8") as f:
    mbti_data = json.load(f)

# 2. Example Prompt for the LLM
PROMPT_TEMPLATE = """
你是一个顶级的心理测验专家。请把以下 MBTI 原始题目，转化为面向中国高中生的“情境判断测试题 (SJT)”。
要求：
- 题干必须是一个具体的高中校园生活/学习场景。
- 选项 A 和 选项 B 必须对立，对应 MBTI 原题的倾向，但要伪装在具体行为中，不能过于直白。
- 你需要同时为选项分配一个匹配的霍兰德 (Holland) 职业兴趣维度作为附属权重。

【原始题目】：{title}
【选项 A】：{sel_a}
【选项 B】：{sel_b}

请输出严格的 JSON 格式：
{{
  "scenario": "...",
  "options": [
    {{"val": "A", "text": "...", "weights": [["MBTI_...", 1.5], ["Holland_...", 1.0]]}},
    {{"val": "B", "text": "...", "weights": [["MBTI_...", 1.5], ["Holland_...", 1.0]]}}
  ]
}}
"""

def translate_items_with_llm(api_key: str):
    """
    Loop over the remaining items and call the LLM API.
    (Pseudocode for API integration)
    """
    print("Starting batch translation...")
    # Skip the first 10 which we already manually translated
    remaining_items = mbti_data["questions"][10:]
    
    translated_bank = []
    
    for idx, item in enumerate(remaining_items):
        prompt = PROMPT_TEMPLATE.format(
            title=item["title"],
            sel_a=item["selections"][0],
            sel_b=item["selections"][1]
        )
        
        print(f"Translating item {idx+11}...")
        # ──────────────────────────────────────────────────────────
        # TODO: Insert your OpenAI / DeepSeek / Claude API call here
        # ──────────────────────────────────────────────────────────
        # response = openai.ChatCompletion.create(
        #     model="gpt-4",
        #     messages=[{"role": "user", "content": prompt}],
        # )
        # result_json = json.loads(response.choices[0].message.content)
        # translated_bank.append(result_json)
        
        # Rate limit pause
        time.sleep(1)
        
    # Save the output to a new python/json file
    print("Translation complete! You can now append these to populate_bank_88.py.")

if __name__ == "__main__":
    print("Please add your API key and uncomment the API call code.")
