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
BASE_URL = "https://hostguard.vercel.app/"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def get_booking_data(url):
    """Парсит название и фото с Booking, обходя защиту JS и ошибки NoneType"""
    
    # 1. ЖЕЛЕЗОБЕТОННЫЙ ПЛАН Б: Достаем имя из самой ссылки (если парсинг не сработает)
    fallback_name = "Apartment"
    try:
        parsed = urllib.parse.urlparse(url)
        # Убираем пустые части пути и берем части до .html
        path_parts = [p for p in parsed.path.split('/') if p]
        for part in path_parts:
            if '.html' in part:
                raw_name = part.split('.')[0]
                fallback_name = raw_name.replace('-', ' ').title()
                break
            elif len(part) > 5: # На случай если ссылки без .html
                fallback_name = part.replace('-', ' ').title()
    except:
        pass

    # Заголовки для маскировки под реальный браузер
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    name = fallback_name
    # Красивая картинка-заглушка на случай, если фото не найдено
    photo = "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?q=80&w=800&auto=format&fit=crop"

    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Фикс ошибки NoneType: проверяем наличие заголовка страницы
        page_title = soup.title.string if (soup.title and soup.title.string) else ""
        
        # Проверка на блокировку Букингом
        forbidden_words = ["JavaScript", "Enable", "Access Denied", "Attention Required"]
        is_blocked = any(word in page_title for word in forbidden_words)

        if not is_blocked:
            # Ищем название (проверяем несколько возможных тегов)
            name_tag = (soup.find("h2", {"class": "pp-header__title"}) or 
                        soup.find("h1") or 
                        soup.find("meta", property="og:title"))
            
            if name_tag:
                if name_tag.name == 'meta':
                    name = name_tag.get('content', name)
                else:
                    name = name_tag.text.strip()
            
            # Ищем фото
            photo_tag = soup.find("meta", property="og:image")
            if photo_tag and photo_tag.get('content'):
                photo = photo_tag['content']
                
    except Exception as e:
        print(f"Ошибка парсинга (используем план Б): {e}")
        
    # Чистим название от мусора типа "Обновленные цены 2026"
    for junk in ["|", ":", "-", "Цены", "Booking.com"]:
        if junk in name:
            name = name.split(junk)[0].strip()
            
    return name, photo

# Обработка /start и кнопок
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
    wait_msg = await message.answer("⌛️ Обхожу защиту и генерирую QR...")
    
    name, photo = get_booking_data(url)
    
    # Формируем ссылку для твоего сайта на Vercel
    params = {
        "platform": "booking",
        "name": name,
        "photo": photo
    }
    
    # Кодируем параметры, чтобы ссылка не ломалась от пробелов и спецсимволов
    final_link = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    
    # Создание QR-кода
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(final_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Подготовка файла для отправки
    bio = io.BytesIO()
    img.save(bio, format='PNG')
    bio.seek(0)
    input_file = BufferedInputFile(bio.read(), filename="qr.png")
    
    caption = (f"✅ <b>Готово!</b>\n\n"
               f"🏠 <b>Объект:</b> {name}\n\n"
               f"🔗 <b>Твоя ссылка (в QR):</b>\n<code>{final_link}</code>")
    
    await message.answer_photo(photo=input_file, caption=caption, parse_mode='HTML')
    await wait_msg.delete()

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен и готов к работе...")
    # Очистка очереди сообщений
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")