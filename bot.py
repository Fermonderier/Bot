import random
import uuid
import json
import telebot
from telebot import types
from PyPDF2 import PdfReader, errors
from PIL import Image, ImageDraw, ImageFont
import pytesseract
from datetime import datetime, timedelta
import os

bot = telebot.TeleBot('7635007621:AAE6JT7SPH23QrtDUjk2vGfaO9195F5oLu4')

# Путь к папке для хранения файлов
files_folder = 'C:\\BOT_bot\\BOT_bot\\students'
os.makedirs(files_folder, exist_ok=True)

# База данных пользователей
users_db = 'users.json'

# Функции для работы с базой данных
def load_users():
    try:
        with open(users_db, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user(user):
    users = load_users()
    users[user["id"]] = user
    with open(users_db, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=3, ensure_ascii=False)

def generate_unique_id():
    return str(random.randint(100000, 999999))  # 6-значное число

# Проверка текста в PDF для принадлежности к AlmaU
def check_if_student_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return "Алматы менеджмент университеті" in text or "Almaty Management University" in text
    except errors.PdfReadError:
        return False  # Вернуть False, если файл PDF некорректный

# Проверка текста в PNG для принадлежности к AlmaU
def check_if_student_png(png_path):
    try:
        text = pytesseract.image_to_string(Image.open(png_path))
        return "Алматы менеджмент университеті" in text or "Almaty Management University" in text
    except Exception as e:
        print("Ошибка при обработке PNG:", e)
        return False

def create_flyer(user_name):
    flyer_template = Image.open('flyer.png').convert('RGB')
    draw = ImageDraw.Draw(flyer_template)

    font = ImageFont.truetype("C:/BOT_bot/BOT_bot/ofont.ru_Kaph.ttf", 45)

    name_position = (150, 800)
    date_position = (140, 860)
    discount_position = (100, 920)
    id_position = (310, 1150)  # Позиция для ID

    user_id = generate_unique_id()

    today = datetime.today()
    friday = today + timedelta((4 - today.weekday()) % 7)
    friday_str = friday.strftime("%d %B %Y")

    draw.text(name_position, f"Имя: {user_name}", font=font, fill=(0, 0, 0))
    draw.text(date_position, f"Дата: {friday_str}", font=font, fill=(0, 0, 0))
    draw.text(discount_position, "Скидка: 5000 - 30% = 3500", font=font, fill=(0, 0, 0))
    draw.text(id_position, f"ID: {user_id}", font=font, fill=(0, 0, 0))

    flyer_path = f"{user_name}_flyer.jpg"
    flyer_template.save(flyer_path)

    return flyer_path

def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Регистрация", "Получить флаер")
    return keyboard

@bot.message_handler(commands=['start'])
def main(message):
    bot.send_message(
        message.chat.id,
        'Добро пожаловать! Данный бот выдаст Вам скидку на посещение наших мероприятий при условии, что вы являетесь студентом университета AlmaU.\n <b> Зарегестрируйтесь перед тем как получить флаер </b>',
        reply_markup=main_keyboard(),
        parse_mode='html'
    )

@bot.message_handler(func=lambda message: message.text in ["Регистрация", "Получить флаер"])
def handle_buttons(message):
    if message.text == "Регистрация":
        bot.send_message(message.chat.id, 'Чтобы зарегистрироваться, отправьте в одном сообщении ваши имя, фамилию и студенческий билет в PDF или PNG формате.')
    elif message.text == "Получить флаер":
        bot.send_message(message.chat.id, "Введите ваше имя и фамилию для получения флаера на скидку.")

@bot.message_handler(func=lambda message: message.text and len(message.text.split()) == 2)
def send_flyer(message):
    full_name = message.text.split()
    first_name, last_name = full_name[0], full_name[1]

    users = load_users()
    for user in users.values():
        if user['entered_first_name'] == first_name and user['entered_last_name'] == last_name:
            flyer_path = create_flyer(f"{first_name} {last_name}")
            with open(flyer_path, 'rb') as flyer:
                bot.send_photo(message.chat.id, flyer)
            os.remove(flyer_path)
            return
    bot.send_message(message.chat.id, 'Вы не зарегистрированы. Пожалуйста, зарегистрируйтесь для получения флаера.')

@bot.message_handler(content_types=['document', 'photo'])
def register_user(message):
    if message.caption is None:
        bot.send_message(message.chat.id, "Пожалуйста, укажите в одном сообщении ваши имя, фамилию и студентческий билет в PDF или PNG формате.")
        return

    full_name = message.caption.split()
    if len(full_name) < 2:
        bot.send_message(message.chat.id, "Пожалуйста, укажите в одном сообщении ваши имя, фамилию и студенческий билет в PDF или PNG формате.")
        return
    entered_first_name, entered_last_name = full_name[0], full_name[1]
    username = message.from_user.username if message.from_user.username else "Не указан"

    if message.content_type == 'document':
        file_info = bot.get_file(message.document.file_id)
        file_extension = file_info.file_path.split('.')[-1].lower()
        file_path = os.path.join(files_folder, f"{message.document.file_id}.{file_extension}")
        downloaded_file = bot.download_file(file_info.file_path)

        with open(file_path, 'wb') as f:
            f.write(downloaded_file)

        if file_extension == 'pdf' and check_if_student_pdf(file_path):
            if check_name_in_file(file_path, entered_first_name, entered_last_name):
                user_registered(message, entered_first_name, entered_last_name, username)
            else:
                bot.send_message(message.chat.id, 'Имя и фамилия не совпадают с данными в студенческом билете.')
        elif file_extension == 'png' and check_if_student_png(file_path):
            if check_name_in_file(file_path, entered_first_name, entered_last_name, is_image=True):
                user_registered(message, entered_first_name, entered_last_name, username)
            else:
                bot.send_message(message.chat.id, 'Имя и фамилия не совпадают с данными в студенческом билете.')
            os.remove(file_path)
        else:
            bot.send_message(message.chat.id, 'Такого студенческого нет.')
            os.remove(file_path)
    else:
        bot.send_message(message.chat.id, "Поддерживаются только PDF и PNG файлы.")

def check_name_in_file(file_path, first_name, last_name, is_image=False):
    if is_image:
        text = pytesseract.image_to_string(Image.open(file_path))
    else:
        text = ""
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text()

    return first_name in text and last_name in text

def user_registered(message, entered_first_name, entered_last_name, username):
    user_id = generate_unique_id()
    user = {
        "id": user_id,
        "first_name": entered_first_name,
        "last_name": entered_last_name,
        "username": username,
        "entered_first_name": entered_first_name,
        "entered_last_name": entered_last_name
    }
    save_user(user)
    bot.send_message(message.chat.id, f'Регистрация прошла успешно! Ваш уникальный ID: {user_id}, Имя пользователя: {username}, Имя, которое вы ввели: {entered_first_name} {entered_last_name}')

bot.polling(none_stop=True)
