import requests
import json
import random

api_key = "U5nAxC97WSQzn6NMOb06Vwtaq72I50jU"
_system_prompt = "You are chatbot created to paraphrase given texts. Your role is to use as many synonyms as possible, so there will be no AI traces. Avoid using numerations and exclude markdown from the text. Use natural, conversational language and ensure the text is engaging and easy to read. Add personal thoughts or experiences when needed."

# [!] Ограничение на 30 запросов в минуту. 
# Если тексты большие, стоит перейти на локальную версию ЛЛМ (либо уходить в таймаут и снова продолжать)
def ai21_paraphrase_text(text): 
    url = "https://api.ai21.com/studio/v1/paraphrase"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "jamba-instruct",
        "presence_penalty": 2,
        "role": {
            "system": _system_prompt
        },
        "text": text,
        "style": "general",
        "temperature": 2,
        "top_p": 0.95
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        result = response.json()

        variants = result['suggestions']
        vlen = len(variants)
        random_index = random.randint(vlen > 0 and 1 or 0, len(variants)-1)
        
        phrase_by_idx = variants[random_index]['text'] or variants[0]['text']

        return phrase_by_idx
    else:
        return ''
