from deep_translator import GoogleTranslator
from langdetect import detect
import requests
import re
from api_requests import ai21_paraphrase_text

_DEBUG_ = False

def printd(*args):
    if _DEBUG_:
        print(" ".join(str(arg) for arg in args))

# --------------------- #

def gl_translation(text, source_lang='auto', target_lang="en"):
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translation = translator.translate(text)
    except Exception as e:
        print('Translation error:', e)

    return translation or text

with open('yc_init.txt', 'r') as f:
    yc_token = f.readline().strip()
    yc_folder = f.readline().strip()

def yc_translation(text, source_lang='auto', target_lang='en'):
    API_KEY = yc_token
    url = "https://translate.api.cloud.yandex.net/translate/v2/translate"
    headers = {
        'Authorization': f'Bearer {API_KEY}',
    }
    body = {
        "sourceLanguageCode": source_lang if source_lang != 'auto' else None,
        "targetLanguageCode": target_lang,
        "format": "PLAIN_TEXT",
        "texts": [text],
        "folderId" : yc_folder
    }

    if body["sourceLanguageCode"] is None:
        del body["sourceLanguageCode"]

    try:
        response = requests.post(url, json=body, headers=headers)
        response.raise_for_status()
        translated_text = response.json()['translations'][0]['text']
    except requests.exceptions.RequestException as e:
        print('Translation error:', e)
        return text

    return translated_text

def detect_language(text):
    lang = detect(text)
    if lang == "en":
        return "en_XX"
    elif lang == "ru":
        return "ru_RU"
    else:
        return "en_XX"

def text_formatter(text):
    text = text.replace('  ', ' ').replace('\r ', '\r').replace('\n ', '\n') #.replace('. ', '.').replace(', ', ',')
    return text

def adaptive_split(text):
    methods = ['.', '. ', '\n']
    formats = [' \n', '\n', '\n']
    ratings = [0, 0, 0]

    for i, method in enumerate(methods):
        ratings[i] = len(text.split(method))

    rating_delta = ratings[0]-ratings[1]

    if ratings[2] > ratings[0]:
        optimal_method = 2
    else:
        optimal_method = rating_delta <= ratings[0] // 2

    return methods[optimal_method], formats[optimal_method], ratings


def split_humanization(text, split_format=None, text_format=None, beautify=True):
    split_rating = adaptive_split(text)

    if not split_format:
        split_format = split_rating[0]

    if not text_format:
        text_format = split_rating[1]

    input_lang = detect_language(text)
    lang_code = input_lang[:2]

    printd(f"Processing text ({lang_code}): {text[:50]}...\nSplit method: '{split_format}'\nRatings: {split_rating[2]}\n")

    if lang_code != 'en':
        printd('Translating -> EN')
        text = yc_translation(text, source_lang=lang_code, target_lang='en')

    output = ''
    splitted_text = text.split(split_format)
    for i, s in enumerate(splitted_text):
        if len(s) > 0: # (+) trimming
            try:
                processed_text = ai21_paraphrase_text(s)

                if detect(processed_text) != lang_code:
                    try:
                        processed_text = yc_translation(processed_text, source_lang='auto', target_lang=lang_code)
                    except:
                        processed_text = gl_translation(processed_text, source_lang='auto', target_lang=lang_code)

                printd(f'paraphrasing - {i}/{len(splitted_text)}')

                output += processed_text + text_format
            except Exception as e:
                print(f'Error processing text: {e}')
                continue
        else:
            output += '\n'

    printd(f'Translating -> {detect(output)}\n')

    if beautify:
        output = text_formatter(output)
        output = re.sub(r'(\w)\n(\w)', r'\1.\n\2', output) # word\n = word.\n

    return output
