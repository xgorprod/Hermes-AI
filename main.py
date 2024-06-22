import logging
import os
import docx2txt
import PyPDF2
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from humanize import split_humanization
from time import sleep

BOT_TOKEN = ''

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

user_states = {}

reply_text = '''<b>Detect AI-generated content 👀</b>\n/detect_ai_content\n\n<b>Humanize the given text 🕵️‍♂️</b>\n/humanize_text'''
detect_reply = "Here is the results:\n• Human score: <b>{}</b> {}\n• AI score: <b>{}</b> {}"
process_reply = "Processing your request ⏳"

def parse_contents(content, mime_type):
    try:
        if mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 
            text = docx2txt.process(content)
        elif mime_type == 'text/plain': 
            text = content.read().decode()
        elif mime_type == 'application/pdf': 
            reader = PyPDF2.PdfReader(content)
            num_of_pages = len(reader.pages)
            text = ''.join([reader.pages[n_page].extract_text() for n_page in range(num_of_pages)])
        else:
            raise ValueError("Unsupported file type")
    except Exception as e:
        print(e)
        raise

    return text

class TextClassifier:
    def __init__(self):
        absolute_path = os.path.dirname(__file__)
        relative_path = "./roberta-v2/"
        full_path = os.path.join(absolute_path, relative_path)
        tokenizer = AutoTokenizer.from_pretrained(full_path, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(full_path, local_files_only=True)
        self.classifier = pipeline("text-classification", model=model, tokenizer=tokenizer)

    def classify_text(self, text):
        if not text:
            return [50, "", 50, "", '']

        res = self.classifier(text, truncation=True, max_length=510)
        label = res[0]['label']
        score = res[0]['score'] * 100

        if label == 'LABEL_1':
            real_score = score
            fake_score = 100 - score
        else:
            fake_score = score
            real_score = 100 - score

        real_score_label = f"{real_score:.0f}%"
        fake_score_label = f"{fake_score:.0f}%"

        return [real_score, real_score_label, fake_score, fake_score_label, '']

classifier = TextClassifier()

# --------------------- #

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply(reply_text, parse_mode=types.ParseMode.HTML)

@dp.message_handler(commands=['detect_ai_content'])
async def detect_ai_content(message: types.Message):
    user_states[message.from_user.id] = 'detect_ai_content'
    await message.reply("Please send the text or file you want to analyze for AI-generated content.")

@dp.message_handler(commands=['humanize_text'])
async def paraphrase_text(message: types.Message):
    user_states[message.from_user.id] = 'humanize_text'
    await message.reply("Please send the text or file you want to humanize.")

@dp.message_handler(content_types=['text'])
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    command = user_states.get(user_id)

    if command == 'detect_ai_content':
        result = classifier.classify_text(text)
        real_score_label, fake_score_label = result[1], result[3]
        sts = result[1] > result[3]

        await message.reply(detect_reply.format(real_score_label, sts and '✅' or '❌', fake_score_label, not sts and '✅' or '❌',), parse_mode=types.ParseMode.HTML)
    elif command == 'humanize_text':
        sleep(0.5)
        await message.reply(process_reply)

        paraphrased_text = split_humanization(text)
        await message.reply(f"{paraphrased_text}")
    else:
        await message.reply(reply_text, parse_mode=types.ParseMode.HTML)

@dp.message_handler(content_types=['document'])
async def handle_document(message: types.Message):
    user_id = message.from_user.id
    document = message.document
    file_id = document.file_id
    command = user_states.get(user_id)

    file = await bot.get_file(file_id)
    file_path = file.file_path

    file_content = await bot.download_file(file_path)

    text = parse_contents(file_content, document.mime_type)

    if command == 'detect_ai_content':
        result = classifier.classify_text(text)
        real_score_label, fake_score_label = result[1], result[3]
        sts = result[1] > result[3]

        await message.reply(detect_reply.format(real_score_label, sts and '✅' or '❌', fake_score_label, not sts and '✅' or '❌'), parse_mode=types.ParseMode.HTML)
    elif command == 'humanize_text':
        sleep(0.5)
        await message.reply(process_reply)

        paraphrased_text = split_humanization(text)
        await message.reply(f"{paraphrased_text}")
    else:
        await message.reply(reply_text, parse_mode=types.ParseMode.HTML)

executor.start_polling(dp, skip_updates=True)