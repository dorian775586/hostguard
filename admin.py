import asyncio
import logging
import qrcode
import io
import urllib.parse
import re
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton
from curl_cffi import requests

# --- НАСТРОЙКИ ---
API_TOKEN = '8755254010:AAEe5G3upx_Nk4rjuGZHgrXFvvDN_ZnXfRg'
ADMIN_ID = 623203896 
BASE_URL = "https://hostguard.vercel.app/"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def get_booking_data(url):
    """Парсит Booking и вытягивает лучшее фото"""
    # Запасное имя из URL
    fallback_name = "Apartment"
    try:
        path = urllib.parse.urlparse(url).path
        path_parts = [p for p in path.split('/') if p]
        for part in path_parts:
            if '.html' in part:
                fallback_name = part.split('.')[0].replace('-', ' ').title()
                break
    except: pass

    # Запасное фото (качественное)
    photo = "https://cf.bstatic.com/xdata/images/hotel/max1024x768/10332541.jpg"
    name = fallback_name

    try:
        # Имитируем Chrome для обхода заглушки
        res = requests.get(url, impersonate="chrome110", timeout=12)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. Ищем название
        og_title = soup.find("meta", property="og:title")
        if og_title:
            name = og_title.get('content')
        else:
            name_tag = soup.find("h2", {"class": "pp-header__title"}) or soup.find("h1")
            if name_tag:
                name = name_tag.text.strip()

        # 2. Ищем фото
        og_img = soup.find("meta", property="og:image")
        if og_img:
            photo = og_img.get('content')
        
        # Увеличиваем размер фото, если оно маленькое
        if "bstatic.com" in photo:
            photo = re.sub(r'/(max|square|rw)\d*(x\d+)?/', '/max1024x768/', photo)

    except Exception as e:
        print(f"⚠️ Ошибка парсинга: {e}")

    # Чистим имя от мусора (JS disabled, Booking.com и т.д.)
    if not name or "JavaScript" in name:
        name = fallback_name
    name = " ".join(name.split())
    for junk in ["|", ":", "-", "Цены", "Booking.com", "Обновленные цены", "Отель"]:
        if junk in name:
            name = name.split(junk)[0].strip()

    # Очищаем URL фото от параметров после знака ?
    photo = photo.split('?')[0]
    if photo.startswith('//'):
        photo = 'https:' + photo
            
    return name, photo

@dp.message(F.text.in_({"/start", "➕ Добавить Booking"}))
async def start_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = [[KeyboardButton(text="➕ Добавить Booking")]]
    markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Пришли ссылку на отель с Booking.com:", reply_markup=markup)

@dp.message(F.text.contains("booking.com"))
async def link_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    input_url = message.text.strip().split("?")[0]
    wait_msg = await message.answer("⌛️ Обработка данных...")
    
    name, photo = get_booking_data(input_url)
    
    # Кодируем параметры для безопасной передачи в URL
    params = {
        "platform": "booking",
        "name": name,
        "photo": photo
    }
    
    # Генерируем ссылку
    query_string = urllib.parse.urlencode(params)
    final_link = f"{BASE_URL}?{query_string}"
    
    # Генерация QR
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(final_link)
    qr.make(fit=True)
    
    bio = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(bio, format='PNG')
    bio.seek(0)
    
    caption = (
        f"🏠 <b>{name}</b>\n\n"
        f"🔗 <b>Ссылка:</b>\n<code>{final_link}</code>"
    )
    
    await message.answer_photo(
        photo=BufferedInputFile(bio.read(), filename="qr.png"), 
        caption=caption, 
        parse_mode='HTML'
    )
    await wait_msg.delete()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())