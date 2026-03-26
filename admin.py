import asyncio
import logging
import qrcode
import io
import requests
import urllib.parse
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton

# --- ТВОИ ДАННЫЕ ---
API_TOKEN = '8755254010:AAEe5G3upx_Nk4rjuGZHgrXFvvDN_ZnXfRg'
ADMIN_ID = 623203896 
# Сюда вставь ссылку на свой index.html (где он у тебя лежит в сети)
BASE_URL = "https://твой-сайт.com/index.html" 

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def get_booking_data(url):
    """Парсит название и фото с Booking"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Название
        name_tag = soup.find("h2", {"class": "pp-header__title"}) or soup.find("h1")
        name = name_tag.text.strip() if name_tag else "Apartment"
        
        # Фото
        photo_tag = soup.find("meta", property="og:image")
        photo = photo_tag['content'] if photo_tag else ""
        
        return name, photo
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return "Apartment", ""

# Обработка /start и /add_booking
@dp.message(F.text.in_({"/start", "/add_booking", "➕ Добавить Booking"}))
async def start_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    kb = [[KeyboardButton(text="➕ Добавить Booking")]]
    markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Пришли ссылку на объект с Booking.com, и я сделаю QR-код:", reply_markup=markup)

# Обработка ссылки
@dp.message(F.text.contains("booking.com"))
async def link_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    url = message.text.strip()
    wait_msg = await message.answer("⌛️ Собираю данные и генерирую QR...")
    
    name, photo = get_booking_data(url)
    
    # Формируем ссылку для твоего сайта
    params = {
        "platform": "booking",
        "name": name,
        "photo": photo
    }
    final_link = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    
    # Делаем QR
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(final_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # В байты для отправки
    bio = io.BytesIO()
    img.save(bio, format='PNG')
    bio.seek(0)
    input_file = BufferedInputFile(bio.read(), filename="qr.png")
    
    caption = (f"✅ <b>Готово!</b>\n\n"
               f"🏠 <b>Объект:</b> {name}\n\n"
               f"🔗 <b>Твоя ссылка для QR:</b>\n<code>{final_link}</code>")
    
    await message.answer_photo(photo=input_file, caption=caption, parse_mode='HTML')
    await wait_msg.delete()

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен и готов к работе...")
    # Удаляем старые апдейты, чтобы бот не спамил ответами на старые сообщения
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())