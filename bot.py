import sys
import subprocess
import os

# ============================================================
# АВТОУСТАНОВКА AIOGRAM
# ============================================================
try:
    import aiogram
except ImportError:
    print("Установка aiogram...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiogram"])
    os.execv(sys.executable, ['python'] + sys.argv)

# -*- coding: utf-8 -*-
import logging
import sqlite3
import datetime
import asyncio
import contextlib
import re

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, MenuButtonCommands,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# ============================================================
# НАСТРОЙКИ ПАРТНЕРСКОГО БОТА (@aipredictor_signals)
# ============================================================
PARTNER_BOT_TOKEN = "9059976355:AAFAsyVX5lQ2TRO4EgSHeS0iQzjFSNj_AAw"
ADMIN_ID = "6109042131" 

# Твои ссылки на игровые боты
LINK_MINES = "https://t.me/MINESSIGNALSONEWINBOT"
LINK_AVIATOR = "https://t.me/aviatora1winibot"
LINK_SLOTS = "https://t.me/slotaipredictorbot"
LINK_AI_SIGNALS = "https://t.me/aipredictor_signals"

# ============================================================
BASE_DIR = os.getenv("DATA_DIR") or os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "partners.db")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("partner_bot")

class PartnerStates(StatesGroup):
    waiting_payout = State()
    waiting_creative_submission = State()
    waiting_support_msg = State()

# ============================================================
# БАЗА ДАННЫХ
# ============================================================
@contextlib.contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.execute("PRAGMA journal_mode=WAL;")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS partners (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 0,
                referrer_id INTEGER,
                added_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS creatives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                country TEXT,
                niche TEXT,
                title TEXT,
                text TEXT
            )
        """)
        try: conn.execute("ALTER TABLE partners ADD COLUMN referrer_id INTEGER")
        except sqlite3.OperationalError: pass
        
        count = conn.execute("SELECT COUNT(*) FROM creatives").fetchone()[0]
        if count == 0:
            load_default_creatives(conn)

def load_default_creatives(conn):
    c = []
    c.append(("tiktok", "cis", "sliv", "💸 СНГ | TikTok: Сторителлинг (Слив)", "📱 <b>Формат:</b> Говорящая голова.\n🗣 <b>Текст:</b> «Я слил 500 баксов в Минусе за 10 минут. Думал всё, конец. Но друг скинул бота, который просчитывает ловушки. Он выдал 3 безопасные ячейки... Ссылка в шапке».\n🎵 <b>Музыка:</b> Грустная -> бас."))
    c.append(("tiktok", "cis", "halyava", "🤑 СНГ | TikTok: Зеленый экран (Халява)", "📱 <b>Формат:</b> Green Screen.\n🗣 <b>Текст:</b> «Разработчики 1win в панике. Этот бот-нейросеть показывает, где спрятаны бомбы. Копируешь, вставляешь, забираешь кэш. Ссылка в профиле»."))
    c.append(("tiktok", "cis", "ai", "🧠 СНГ | TikTok: Разбор алгоритма (Скептики)", "📱 <b>Формат:</b> Быстрый монтаж (IT-стиль).\n🗣 <b>Текст:</b> «Думаете Mines — это удача? Нет. В основе PRNG. Нейросеть анализирует паттерны. Тестировал 2 недели, результат 90% попаданий. Ссылка в профиле»."))
    c.append(("tiktok", "cis", "aviator", "✈️ СНГ | TikTok: Авиатор (Скринкаст)", "📱 <b>Формат:</b> Запись экрана.\n🗣 <b>Текст:</b> «Замечали, что самолет падает на 1.2х? Это не случайность. Бот анализирует графики и показывает, когда забирать кэш. Ссылка в профиле»."))
    c.append(("reels", "cis", "lifestyle", "👩 СНГ | Reels: Эстетика (Для девушек)", "📸 <b>Формат:</b> Замедленная съемка.\n🗣 <b>Текст:</b> «Меня спрашивают, откуда деньги на путешествия. Секрет: ИИ делает деньги в Минусе, пока я пью кофе. Ссылка в профиле».\n🎵 <b>Музыка:</b> Aesthetic Lo-Fi."))
    c.append(("shorts", "cis", "challenge", "🧠 СНГ | Shorts: Челлендж 7 дней", "▶️ <b>Формат:</b> Быстрая нарезка.\n🗣 <b>Текст:</b> «Я проверял бота 7 дней. День 1: сомневался. День 3: 4 звезды. День 7: вывел иксы. Ссылка в описании»."))
    
    conn.executemany("INSERT INTO creatives (platform, country, niche, title, text) VALUES (?, ?, ?, ?, ?)", c)

# ============================================================
# БОТ И ДИСПЕТЧЕР
# ============================================================
bot = Bot(token=PARTNER_BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML", link_preview_is_disabled=True))
dp = Dispatcher(storage=MemoryStorage())

# ============================================================
# КЛАВИАТУРЫ
# ============================================================
def get_partner_kb():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔗 Мои ссылки для трафика"), KeyboardButton(text="👥 Пригласить трафера (5%)")],
            [KeyboardButton(text="📊 Моя статистика"), KeyboardButton(text="👑 Топ траферов")],
            [KeyboardButton(text="🎬 База креативов"), KeyboardButton(text="📤 Предложить креатив")],
            [KeyboardButton(text="📩 Связаться с админом"), KeyboardButton(text="💰 Вывести деньги")]
        ],
        resize_keyboard=True
    )
    return kb

def get_admin_kb():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📈 Список партнеров")]
        ],
        resize_keyboard=True
    )
    return kb

# ============================================================
# ХЕНДЛЕРЫ
# ============================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    uid = message.from_user.id
    uname = message.from_user.username or "no_username"
    ref = command.args
    
    if str(uid) == str(ADMIN_ID):
        await message.answer("👑 <b>Привет, Админ!</b>\nТы в панели управления.", reply_markup=get_admin_kb())
        return

    with get_db() as conn:
        is_new = conn.execute("SELECT 1 FROM partners WHERE tg_id = ?", (uid,)).fetchone() is None
        
        ref_id = None
        if ref and ref.startswith("ref_") and ref[4:].isdigit():
            ref_id = int(ref[4:])
            if ref_id == uid: ref_id = None 

        if is_new:
            conn.execute("INSERT INTO partners (tg_id, username, referrer_id, added_at) VALUES (?, ?, ?, ?)", 
                         (uid, uname, ref_id, datetime.datetime.now().isoformat()))
            
            try:
                await bot.send_message(ADMIN_ID, f"🆕 <b>НОВЫЙ ТРАФЕР ЗАШЕЛ!</b>\n\n👤 Имя: {message.from_user.first_name}\n🔗 Юзернейм: @{uname}\n🆔 ID: <code>{uid}</code>")
                
                if ref_id:
                    # Фишка: Красивое уведомление пригласившему
                    await bot.send_message(
                        ref_id, 
                        f"🔥 <b>ПО ТВОЕЙ ССЫЛКЕ ЗАЛЕТЕЛ НОВЫЙ ТРАФЕР!</b>\n\n"
                        f"👤 Его ник: @{uname}\n"
                        f"💸 Теперь ты получаешь <b>5%</b> от его профита!\n\n"
                        f"Твой пассивный доход начинает расти. Продолжай в том же духе! 🚀"
                    )
            except Exception: pass

    # Фишка: Мощное приветствие, продающее пассивный доход
    await message.answer(
        "🔥 <b>ДОБРО ПОЖАЛОВАТЬ В ЭЛИТНУЮ ПАРТНЕРСКУЮ КОМАНДУ!</b>\n\n"
        "Здесь ты не просто льёшь трафик. Ты строишь свою <b>собственную сеть</b>.\n\n"
        "💰 <b>ТВОИ УСЛОВИЯ:</b>\n"
        "• <b>$15</b> за каждого игрока с депозитом (FTD)\n"
        "• <b>50% RevShare</b> от проигрышей твоих игроков\n\n"
        "👑 <b>СИСТЕМА ПАССИВНОГО ДОХОДА:</b>\n"
        "Приглашай других траферов по своей ссылке и получай <b>5% от их заработка</b>! Ничего не делаешь — деньги капают.\n\n"
        "🎁 <b>БОНУСЫ:</b>\n"
        "• 50.000 просмотров? <b>+$10</b>\n"
        "• 100.000 просмотров? <b>+$30</b>\n"
        "• Свой крутой креатив? <b>+$10!</b>\n\n"
        "👇 <i>Твоя империя начинается здесь. Выбирай действие:</i>",
        reply_markup=get_partner_kb()
    )

@dp.message(F.text == "👥 Пригласить трафера (5%)")
async def partner_invite_trafficker(message: types.Message):
    uid = message.from_user.id
    b_info = await bot.get_me()
    ref_link = f"https://t.me/{b_info.username}?start=ref_{uid}"
    
    text = (
        f"👑 <b>ТВОЯ РЕФЕРАЛЬНАЯ ССЫЛКА (Пассивный доход 5%)</b>\n\n"
        f"Копируй эту ссылку и отправляй друзьям-траферам:\n"
        f"<code>{ref_link}</code>\n\n"
        f"💸 <b>Как это работает?</b>\n"
        f"1️⃣ Твой друг переходит по ссылке и регистрируется.\n"
        f"2️⃣ Он начинает лить трафик и зарабатывать.\n"
        f"3️⃣ Ты автоматически получаешь <b>5% от его профита</b> на свой баланс!\n\n"
        f"🔥 <i>Создавай свою сеть и получай деньги, даже когда спишь!</i>"
    )
    await message.answer(text)

@dp.message(F.text == "👑 Топ траферов")
async def partner_leaderboard(message: types.Message):
    with get_db() as conn:
        # Ищем топ-5 траферов по количеству приглашенных
        top = conn.execute("""
            SELECT referrer_id, COUNT(*) as ref_count 
            FROM partners 
            WHERE referrer_id IS NOT NULL 
            GROUP BY referrer_id 
            ORDER BY ref_count DESC LIMIT 5
        """).fetchall()
        
    text = "👑 <b>ЗАЛ СЛАВЫ ПАРТНЕРСКОЙ СЕТИ</b> 👑\n\n"
    
    if not top:
        text += "Пока никто не приглашал траферов. Стань первым лидером! 🚀"
    else:
        for i, (ref_id, count) in enumerate(top, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} ID: <code>{ref_id}</code> — <b>{count} траферов</b>\n"
            
    await message.answer(text)

@dp.message(F.text == "📊 Моя статистика")
async def partner_stats(message: types.Message):
    uid = message.from_user.id
    with get_db() as conn:
        refs = conn.execute("SELECT COUNT(*) FROM partners WHERE referrer_id = ?", (uid,)).fetchone()[0]
        
    await message.answer(
        f"📊 <b>Твой профиль:</b>\n\n"
        f"👆 Переходы: <i>считаются</i>\n"
        f"✅ Регистрации: <i>считаются</i>\n"
        f"👥 Приглашено траферов: <b>{refs}</b>\n"
        f"💸 Твой пассивный доход: <i>запроси у админа</i>\n\n"
        f"<i>(Полная статистика обновляется вручную. Пиши админу для сверки)</i>"
    )

# ============================================================
# ОБРАТНАЯ СВЯЗЬ
# ============================================================
@dp.message(F.text == "📩 Связаться с админом")
async def support_msg(message: types.Message, state: FSMContext):
    await message.answer("💬 <b>Напиши свой вопрос или предложение админу прямо сюда:</b>")
    await state.set_state(PartnerStates.waiting_support_msg)

@dp.message(PartnerStates.waiting_support_msg)
async def process_support_msg(message: types.Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    uname = message.from_user.username or "no_username"
    
    try:
        await bot.send_message(
            ADMIN_ID, 
            f"📩 <b>СООБЩЕНИЕ ОТ ТРАФЕРА</b>\n"
            f"👤 От: <code>{uid}</code> | @{uname}\n\n"
            f"{message.text}\n\n"
            f"<i>(Чтобы ответить, зажми это сообщение и нажми «Ответить»)</i>"
        )
        await message.answer("✅ Сообщение отправлено! Админ ответит вам в ближайшее время.")
    except Exception:
        await message.answer("❌ Ошибка отправки. Попробуйте позже.")

@dp.message(F.from_user.id == int(ADMIN_ID), F.reply_to_message)
async def admin_reply_handler(message: types.Message):
    reply_text = message.reply_to_message.text
    if reply_text and "СООБЩЕНИЕ ОТ ТРАФЕРА" in reply_text:
        match = re.search(r'От:\s*(\d+)', reply_text)
        if match:
            traf_id = int(match.group(1))
            try:
                await bot.send_message(traf_id, f"👑 <b>Ответ от Админа:</b>\n\n{message.text}")
                await message.answer(f"✅ Ответ успешно отправлен траферу <code>{traf_id}</code>!")
            except Exception as e:
                await message.answer(f"❌ Не удалось отправить сообщение. Ошибка: {e}")

# ============================================================
# КРЕАТИВЫ И ВЫВОД (Без изменений, но с кнопками в меню)
# ============================================================
@dp.message(F.text == "📤 Предложить креатив")
async def suggest_creative(message: types.Message, state: FSMContext):
    await message.answer("🎬 <b>Отправь свой креатив!</b>\n\nЕсли админ одобрит, ты получишь <b>БОНУС $10</b>! 🎁\n\n<i>Просто отправь видео, фото или текст сюда:</i>")
    await state.set_state(PartnerStates.waiting_creative_submission)

@dp.message(PartnerStates.waiting_creative_submission, F.content_type.in_({'text', 'photo', 'video', 'video_note'}))
async def process_creative_submission(message: types.Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id; uname = message.from_user.username or "no_username"
    try:
        await bot.send_message(ADMIN_ID, f"📥 <b>НОВЫЙ КРЕАТИВ ОТ ТРАФЕРА!</b>\n👤 От: <code>{uid}</code> | @{uname}\n\n👇 Смотри ниже:")
        await message.copy_to(chat_id=ADMIN_ID)
        await message.answer("✅ <b>Креатив отправлен на проверку!</b> Если админ одобрит, ты получишь <b>$10</b>.")
    except Exception: await message.answer("❌ Ошибка при отправке. Попробуй позже.")

@dp.message(F.text == "🔗 Мои ссылки для трафика")
async def partner_links(message: types.Message):
    uid = message.from_user.id
    text = (
        f"🔗 <b>Твои личные ссылки для залива трафика:</b>\n\n"
        f"💣 <b>Mines:</b>\n<code>{LINK_MINES}?start=tr_{uid}</code>\n\n"
        f"✈️ <b>Aviator:</b>\n<code>{LINK_AVIATOR}?start=tr_{uid}</code>\n\n"
        f"🎰 <b>Slots:</b>\n<code>{LINK_SLOTS}?start=tr_{uid}</code>\n\n"
        f"📊 <b>AI Signals:</b>\n<code>{LINK_AI_SIGNALS}</code>\n\n"
        f"⚠️ <i>Кидай ссылки в TikTok. Все регистрации запишутся на тебя.</i>"
    )
    await message.answer(text)

@dp.message(F.text == "🎬 База креативов")
async def creative_menu_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 TikTok", callback_data="plat_tiktok")],
        [InlineKeyboardButton(text="📸 Instagram Reels", callback_data="plat_reels")],
        [InlineKeyboardButton(text="▶️ YouTube Shorts", callback_data="plat_shorts")]
    ])
    await message.answer("🎯 <b>Выбери платформу:</b>", reply_markup=kb)

@dp.callback_query(F.data.startswith("plat_"))
async def choose_country(call: types.CallbackQuery):
    platform = call.data.split("_")[1]
    await call.message.delete()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 СНГ", callback_data=f"cnt_{platform}_cis")],
        [InlineKeyboardButton(text="🇧🇷 LATAM", callback_data=f"cnt_{platform}_latam")],
        [InlineKeyboardButton(text="🇮🇳 Индия", callback_data=f"cnt_{platform}_ind")],
        [InlineKeyboardButton(text="🇺🇸 Global", callback_data=f"cnt_{platform}_global")]
    ])
    await call.message.answer(f"🌍 <b>Платформа:</b> {platform.upper()}\n\nВыбери регион:", reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data.startswith("cnt_"))
async def choose_niche(call: types.CallbackQuery):
    parts = call.data.split("_"); platform, country = parts[1], parts[2]
    await call.message.delete()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Слив", callback_data=f"nc_{platform}_{country}_sliv")],
        [InlineKeyboardButton(text="🤑 Халява", callback_data=f"nc_{platform}_{country}_halyava")],
        [InlineKeyboardButton(text="🧠 ИИ / Скептики", callback_data=f"nc_{platform}_{country}_ai")],
        [InlineKeyboardButton(text="✈️ Aviator", callback_data=f"nc_{platform}_{country}_aviator")],
        [InlineKeyboardButton(text="👩 Лайфстайл", callback_data=f"nc_{platform}_{country}_lifestyle")],
        [InlineKeyboardButton(text="🔥 Челлендж", callback_data=f"nc_{platform}_{country}_challenge")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"plat_{platform}")]
    ])
    await call.message.answer(f"🎯 <b>{country.upper()}</b>\n\nВыбери нишу:", reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data.startswith("nc_"))
async def show_creatives(call: types.CallbackQuery):
    parts = call.data.split("_"); platform, country, niche = parts[1], parts[2], parts[3]
    with get_db() as conn:
        rows = conn.execute("SELECT title, text FROM creatives WHERE platform = ? AND country = ? AND niche = ?", (platform, country, niche)).fetchall()
    if not rows: await call.answer("В этой связке пока нет креативов.", show_alert=True); return
    await call.message.delete(); await call.answer()
    await call.message.answer(f"🔥 <b>Креативы {country.upper()} ({platform.upper()})</b>")
    for title, text in rows:
        await call.message.answer(f"{title}\n\n{text}"); await asyncio.sleep(0.3)

@dp.message(F.text == "💰 Вывести деньги")
async def partner_payout(message: types.Message, state: FSMContext):
    await message.answer("💳 Напиши реквизиты для вывода (карта или USDT):")
    await state.set_state(PartnerStates.waiting_payout)

@dp.message(PartnerStates.waiting_payout)
async def process_payout(message: types.Message, state: FSMContext):
    reqs = message.text; uid = message.from_user.id; uname = message.from_user.username or "no_username"; await state.clear()
    await message.answer("✅ Заявка создана! Ожидай выплату в течение 24 часов.")
    try: await bot.send_message(ADMIN_ID, f"💸 <b>ЗАЯВКА НА ВЫВОД!</b>\n\n👤 Трафер: <code>{uid}</code> | @{uname}\n💳 Реквизиты:\n<code>{reqs}</code>")
    except Exception: pass

# ============================================================
# АДМИН ПАНЕЛЬ (С ЗАЩИТОЙ ОТ ОБРЫВА)
# ============================================================
@dp.message(F.text == "📈 Список партнеров")
async def cmd_stats(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID): return
    with get_db() as conn: partners = conn.execute("SELECT tg_id, username, referrer_id FROM partners").fetchall()
    if not partners: await message.answer("Партнеров пока нет."); return

    text = f"📈 <b>Всего траферов: {len(partners)}</b>\n\n"
    for p in partners:
        ref_info = f" (Пригласил: {p[2]})" if p[2] else ""
        text += f"👤 <code>{p[0]}</code> | @{p[1]}{ref_info}\n"
        if len(text) > 3500:
            try: await message.answer(text); await asyncio.sleep(0.5)
            except Exception as e: log.error(f"Err: {e}")
            text = "" 
    if text.strip():
        try: await message.answer(text)
        except Exception as e: log.error(f"Err: {e}")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands(text="Меню"))
    log.info("Partner Bot starting polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    init_db()
    asyncio.run(main())