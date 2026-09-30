import os
import re
import asyncio
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
load_dotenv()
# Твій токен бота
TOKEN = os.getenv("BOT_TOKEN")

# Шлях до папки з картинками та відео (img)
IMG_DIR = os.path.join(os.path.dirname(__file__), "img")


# Функція для команди /start (Головне меню)
FEEDBACK_EMAIL = os.getenv("FEEDBACK_EMAIL", "b71724496@gmail.com")
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))

DONATION_URL = "https://send.monobank.ua/jar/2g8MEijhoY"

map_keyboard = [
    [
        InlineKeyboardButton(
            "🗺️ Відкрити карту",
            url="https://www.google.com/maps/search/?api=1&query=49.82971,24.00498",
        )
    ]
]


async def send_feedback_email(user, user_email, feedback_text):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        raise RuntimeError(
            "Не налаштовані SMTP_EMAIL та SMTP_PASSWORD."
        )

    user_name = user.full_name or "Без імені"
    username = f"@{user.username}" if user.username else "немає"

    message = EmailMessage()
    message["Subject"] = "📝 Новий відгук — Рієлторський форум 3.0"
    message["From"] = SMTP_EMAIL
    message["To"] = FEEDBACK_EMAIL
    message["Reply-To"] = user_email

    message.set_content(
        f"Новий відгук з Telegram-бота Рієлторського форуму 3.0\n\n"
        f"Email автора: {user_email}\n"
        f"Ім'я: {user_name}\n"
        f"Username: {username}\n"
        f"Telegram ID: {user.id}\n\n"
        f"Відгук:\n{feedback_text}"
    )

    def _send():
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
            smtp.send_message(message)

    await asyncio.to_thread(_send)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("waiting_feedback", None)

    text = (
        "<b>Рієлторський форум 3.0</b>\n"
        "НАЙОЧІКУВАНІША ПОДІЯ РОКУ 2026 🔥\n\n"
        "📅 9 жовтня 2026 року\n"
        "📍 Львів, вул. Мельника, 18\n\n"
        "Оберіть потрібний розділ нижче 👇"
    )

    keyboard = [
        [KeyboardButton("🎉 Про 3.0"), KeyboardButton("📅 Програма")],
        [KeyboardButton("🎤 Спікери"), KeyboardButton("🤝 Партнери")],
        [KeyboardButton("Нагороди"), KeyboardButton("Купити квитки")],
        [KeyboardButton("🪩 Афтерпаті"), KeyboardButton("🗺️ Локація")],
        [KeyboardButton("💬 Комюніті чат"), KeyboardButton("🌟 Благодійність")],
        [KeyboardButton("🌐 Ми в соц-мережах"), KeyboardButton("☎️ Контакти")],
      ##  [KeyboardButton("📝 Залишити відгук")],

    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    main_video_path = os.path.join(IMG_DIR, "RF Animation.mp4")
    
    try:
        with open(main_video_path, "rb") as video_file:
            await update.message.reply_video(video=video_file, caption=text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    except FileNotFoundError:
        await update.message.reply_text(text=text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


# Обробник натискання нижніх кнопок тексту
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    # Перший крок: користувач вводить свою електронну пошту.
    if context.user_data.get("waiting_feedback_email"):
        user_email = user_text.strip()
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", user_email):
            await update.message.reply_text(
                "❗ Введіть коректну електронну пошту.\n"
                "Наприклад: example@gmail.com"
            )
            return

        context.user_data["feedback_email"] = user_email
        context.user_data.pop("waiting_feedback_email", None)
        context.user_data["waiting_feedback"] = True
        await update.message.reply_text(
            "✅ Пошту збережено.\n\n"
            "💬 Тепер напишіть ваш коментар або відгук:"
        )
        return

    # Другий крок: користувач вводить текст коментаря.
    if context.user_data.get("waiting_feedback"):
        feedback_text = user_text.strip()
        if not feedback_text:
            await update.message.reply_text("❗ Будь ласка, напишіть текст відгуку.")
            return

        user_email = context.user_data.get("feedback_email")
        if not user_email:
            context.user_data.pop("waiting_feedback", None)
            context.user_data["waiting_feedback_email"] = True
            await update.message.reply_text("📧 Спочатку введіть вашу електронну пошту:")
            return

        try:
            await send_feedback_email(update.effective_user, user_email, feedback_text)
            context.user_data.pop("waiting_feedback", None)
            context.user_data.pop("feedback_email", None)
            await update.message.reply_text(
                "✅ Дякуємо за ваш відгук!\n"
                "Коментар успішно надіслано організаторам."
            )
        except Exception as error:
            print(f"Помилка відправки відгуку: {error}")
            await update.message.reply_text(
                "❌ Не вдалося надіслати відгук. "
                "Перевірте налаштування пошти та спробуйте ще раз."
            )
        return

    if user_text == "📝 Залишити відгук":
        context.user_data.pop("feedback_email", None)
        context.user_data.pop("waiting_feedback", None)
        context.user_data["waiting_feedback_email"] = True
        await update.message.reply_text(
            "📝 <b>Залишити відгук</b>\n\n"
            "📧 Спочатку введіть вашу електронну пошту:\n"
            "Наприклад: example@gmail.com",
            parse_mode=ParseMode.HTML,
        )
        return


    # 1. ОБРОБКА КНОПКИ "🎉 ПРО ПОДІЮ"
    if user_text == "🎉 Про 3.0":
        about_text = (
            "<b>Рієлторський форум 3.0</b>\n"
            "Не для тих, хто чекає змін. Для тих, хто їх робить. 🔥\n\n"
            "Це щорічна зустріч професіоналів з усієї України, де ринок не обговорюють — його формують. "
            "Тут народжуються партнерства, запускаються проєкти і зростає те, що не купиш за гроші — довіра.\n\n"
            "Бо найцінніша інвестиція сьогодні — це люди, з якими ти поруч. "
            "Ми не просто збираємось на форум. Ми збираємо тил тих, хто тримає країну на ногах. "
            "Тут зустрічаються ті, хто будує не лише будинки, а й довіру, спільноту, майбутнє. ✨\n\n"
            "Ми вкладаємося не лише у метри. Ми інвестуємо у людей, бізнес, землю, технології. "
            "У все, що зміцнює Україну — щодня, попри все. 🇺🇦\n\n"
            "Бо справжній рієлтор — це не просто посередник. Це strategie. Амбасадор стабільності. І трошки чарівник."
        )
        photo_path = os.path.join(IMG_DIR, "forum.jpg")
        try:
            with open(photo_path, "rb") as photo_file:
                await update.message.reply_document(document=photo_file, caption=about_text, parse_mode=ParseMode.HTML)
        except FileNotFoundError:
            await update.message.reply_text(text=about_text, parse_mode=ParseMode.HTML)

    # 2. ОБРОБКА КНОПКИ "🗺️ ЛОКАЦІЯ"
    elif user_text == "🗺️ Локація": 
        location_caption = ( "📍 **Локація події — BARVY, LEOLAND**\n" 
                            "Сучасний та стильний простір для найочікуванішої події року!\n\n"
                            "📅 **Дата:** 9 жовтня 2026 року\n"
                            "📬 **Адреса:** Львів, вул. Мельника, 18\n\n"
                            "🚗 **Як добратися?**\n" "Локація знаходиться у зручній частині Львова. " "Швидко та комфортно можна доїхати на таксі (Uklon, Bolt) " "або власному авто.\n\n" 
                            "Зустрінемося на локації! 🏢✨" ) # Відправляємо текст 
        await update.message.reply_text( text=location_caption, parse_mode=ParseMode.MARKDOWN ) # Відправляємо справжню карту Telegram 
        await update.message.reply_location( latitude=49.82971, longitude=24.00498 ) # Кнопка для відкриття маршруту 
        await update.message.reply_text( "📍 **BARVY Event Hall / LEOLAND**\n" "вул. Мельника, 18, Львів", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(map_keyboard) )
    # 3. ОБРОБКА КНОПКИ "📅 ПРОГРАМА"
    elif user_text == "📅 Програма":
        program_text = (
            "<b>📅 Програма Рієлторського Форуму 3.0</b>\n"
            "📍 Leoland Hall | Львів\n"
            "🗓️ <b>9 ЖОВТНЯ 2026</b>\n\n"
            "🤝 <b>НайТОПовіші партнери ринку</b>\n\n"
            "👤 <b>Спеціальна гостя форуму</b> — народна депутатка України <b>Олена Шуляк</b> з актуальною темою:\n"
            "<i>«Майбутнє ринку нерухомості, закон про рієлторську діяльність та відбудова України»</i>\n\n"
            "🏛️ <b>Панельна дискусія</b> за участю представників влади\n\n"
            "🏢 <b>Ексклюзивна панельна дискусія провідних львівських забудовників:</b>\n"
            "LEV Development, IKON Development, Resident Development та Будинки і Люди\n\n"
            "🎵 <b>Виступ популярного виконавця</b> — Нікіта Кісельов\n\n"
            "🎲 <b>ДВІ масштабні гри</b> — а це вдвічі більше подарунків та сюрпризів!\n\n"
            "🏆 <b>Унікальні нагороди</b> для найкращих рієлторів Львівщини, створені відомою скульпторкою Мар’яною Мотикою\n\n"
            "✨ <b>Креативні інтерактиви</b>, які створюватимуть нову історію професії просто на ваших очах!"
        )
        program_photo_path = os.path.join(IMG_DIR, "program_day1.jpg")
        try:
            with open(program_photo_path, "rb") as photo_file:
                await update.message.reply_photo(photo=photo_file, caption=program_text, parse_mode=ParseMode.HTML)
        except FileNotFoundError:
            await update.message.reply_text(text=program_text, parse_mode=ParseMode.HTML)

    # 4. ОБРОБКА КНОПКИ "🎤 СПІКЕРИ"
    elif user_text == "🎤 Спікери":
        speakers_keyboard = [
            [InlineKeyboardButton("🔮 Майбутнє ринку нерухомості та відбудова", callback_data="theme_future")],
            [InlineKeyboardButton("🏢 Панельна дискусія забудовників", callback_data="theme_builders")],
            [InlineKeyboardButton("📈 Інвестиції, тренди та аналітика ринку", callback_data="theme_investments")]
        ]
        reply_markup = InlineKeyboardMarkup(speakers_keyboard)
        await update.message.reply_text(
            text="📋 **Оберіть тему виступу, щоб переглянути спікерів:**",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    # 5. ОБРОБКА КНОПКИ "🤝 ПАРТНЕРИ"
    elif user_text == "🤝 Партнери":
        partners_keyboard = [
            [InlineKeyboardButton(
                "🏢 Нерухомість та медіа",
                callback_data="partners_realestate"
            )],
            [InlineKeyboardButton(
                "🛋️ Меблі та інтер'єр",
                callback_data="partners_furniture"
            )],
            [InlineKeyboardButton(
                "🌸 Квіти та lifestyle",
                callback_data="partners_lifestyle"
            )],
            [InlineKeyboardButton(
                "🤝 Інші партнери",
                callback_data="partners_other"
            )]
        ]

        reply_markup = InlineKeyboardMarkup(partners_keyboard)

        await update.message.reply_text(
            "🤝 <b>Партнери Рієлторського Форуму 3.0</b>\\n\\n"
            "Оберіть категорію:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

    # 6. ОБРОБКА КНОПКИ "💬 Комюніті чат"
    elif user_text == "💬 Комюніті чат":
        chat_keyboard = [
            [InlineKeyboardButton("🚀 Приєднатися до чату", url="https://t.me/+e_xVciTD2fJhMDAy")]
        ]
        reply_markup = InlineKeyboardMarkup(chat_keyboard)
        
        await update.message.reply_text(
            text="💬 <b>Доєднуйся до офіційного комюніті чату Рієлторського форуму!</b>\n\n"
                 "Тут спілкуються професіонали, обговорюють головні новини ринку, "
                 "знаходять партнерів та діляться досвідом. Не втрачай можливість бути в центрі подій! 🔥",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

    # ОБРОБКА КНОПКИ "Купити квитки"
    elif user_text == "Купити квитки":
        ticket_keyboard = [
            [InlineKeyboardButton("🎟️ Зареєструватись для участі", url="https://secure.wayforpay.com/payment/sd00e490c8e01")]
        ]
        reply_markup = InlineKeyboardMarkup(ticket_keyboard)
        await update.message.reply_text(
            text="Для участі в <b>Рієлторському Форумі 3.0</b> натисніть кнопку нижче, щоб перейти до реєстрації та оплати через систему WayForPay 👇",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

# ОБРОБКА КНОПКИ "🌐 Ми в соц-мережах" (ПОВНІСТЮ УКОМПЛЕКТОВАНО)
    elif user_text == "🌐 Ми в соц-мережах":
        social_keyboard = [
            [
                InlineKeyboardButton("👥 Facebook", url="https://www.facebook.com/events/%D0%BB%D1%8C%D0%B2%D1%96%D0%B2-%D1%83%D0%BA%D1%80%D0%B0%D1%97%D0%BD%D0%B0/%D1%80%D1%96%D0%B5%D0%BB%D1%82%D0%BE%D1%80%D1%81%D1%8C%D0%BA%D0%B8%D0%B9-%D1%84%D0%BE%D1%80%D1%83%D0%BC/2661636843997521/"),
                InlineKeyboardButton("📸 Instagram", url="https://www.instagram.com/realtors_forum/")
            ],
            [
                InlineKeyboardButton("🎬 TikTok", url="https://www.tiktok.com/@realtors_forum?_t=ZM-8yIjFgwJngE&_r=1"),
                InlineKeyboardButton("📺 YouTube", url="https://www.youtube.com/@rieltorforum-o5l")
            ],
            [
                InlineKeyboardButton("🌐 Наш сайт", url="https://www.rieltorforum.in.ua/")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(social_keyboard)
        await update.message.reply_text(
            text="🌐 <b>Стежте за Рієлторським Форумом 3.0 у соціальних мережах!</b>\n\n"
                 "Обирайте зручну платформу, щоб першими бачити бекстейджі, фотозвіти та головні новини події 👇",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

    # 7. ОБРОБКА КНОПКИ "☎️ КОНТАКТИ"
    elif user_text == "☎️ Контакти":
        contacts_text = (
            "Координатор Ріелторського форуму\nНіна Бенях\n📱 +38 (067) 995 83 82\nrealtorlviv.ng@gmail.com\n\n"
            "З питань квитків:\nЄлизавета Боровець\n📱 +380 68 992 83 82\n\n"
            "З питань програми та ЗМІ:\nЛюбомир Жмінковський\n📱 +380 (97) 335 06 73"
        )
        await update.message.reply_text(text=contacts_text)

    # 🌟 БЛАГОДІЙНІСТЬ
    elif user_text == "🌟 Благодійність":
        donation_keyboard = [
            [InlineKeyboardButton("🔗 Відкрити Банку", url=DONATION_URL)]
        ]

        donation_text = (
            "<b>🇺🇦 Збір коштів для ЗСУ</b>\n\n"
            "Збір коштів для бійців.\n"
            "У кожній людині повинна бути доброта. ❤️\n\n"
            "🎯 <b>Ціль: 200 000.00 ₴</b>\n\n"
            "🔗 <b>Посилання на Банку:</b>\n"
            f"{DONATION_URL}\n\n"
            "💳 <b>Номер картки Банки:</b>\n"
            "5375 4112 0206 2852"
        )

        await update.message.reply_text(
            donation_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(donation_keyboard),
        )

    # ЗАГЛУШКИ ДЛЯ ІНШИХ КНОПОК
    elif user_text in ["Нагороди", "🪩 Афтерпаті", "Форум 2.0", "Рієлторський форум", "🗓️ Side Events | Premium | VIP", "🏚️ Day 3 | Premium | VIP", "🗣️ Нетворкінг"]:
        await update.message.reply_text(
            f"Інформація для розділу '{user_text}' зараз оновлюється. Слідкуйте за анонсами! 🕒"
        )


# ОБРОБНИК ІНЛАЙН-КНОПОК
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # --- ПАРТНЕРИ ЗА КАТЕГОРІЯМИ ---

    if query.data == "partners_realestate":
        try:
            media_group = [
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-6.jpg"), "rb"),
                    caption="🏢 <b>Нерухомість та медіа</b>\\n\\nЛУН",
                    parse_mode=ParseMode.HTML
                ),
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-7.jpg"), "rb"),
                    caption="Рієлтор від ЛУН"
                ),
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-3.jpg"), "rb"),
                    caption="UA.News"
                )
            ]
            await query.message.reply_media_group(media=media_group)
        except FileNotFoundError:
            await query.message.reply_text(
                "❌ Не знайдено фото партнерів цієї категорії."
            )

    elif query.data == "partners_furniture":
        try:
            media_group = [
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-8.jpg"), "rb"),
                    caption="🛋️ <b>Меблі та інтер'єр</b>\\n\\nFRANKOF",
                    parse_mode=ParseMode.HTML
                ),
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-12.jpg"), "rb"),
                    caption="Meblero"
                )
            ]
            await query.message.reply_media_group(media=media_group)
        except FileNotFoundError:
            await query.message.reply_text(
                "❌ Не знайдено фото партнерів цієї категорії."
            )

    elif query.data == "partners_lifestyle":
        try:
            media_group = [
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-9.jpg"), "rb"),
                    caption="🌸 <b>Квіти та lifestyle</b>\\n\\nLemberg Flowers",
                    parse_mode=ParseMode.HTML
                ),
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-5.jpg"), "rb"),
                    caption="РОСА"
                ),
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-4.jpg"), "rb"),
                    caption="Aroma"
                ),
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-10.jpg"), "rb"),
                    caption="MON TOUTOU"
                )
            ]
            await query.message.reply_media_group(media=media_group)
        except FileNotFoundError:
            await query.message.reply_text(
                "❌ Не знайдено фото партнерів цієї категорії."
            )

    elif query.data == "partners_other":
        try:
            media_group = [
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-1.jpg"), "rb"),
                    caption="🤝 <b>Інші партнери</b>\\n\\nСпарта-Захід",
                    parse_mode=ParseMode.HTML
                ),
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-2.jpg"), "rb"),
                    caption="Дарія Панчишин"
                ),
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-11.jpg"), "rb"),
                    caption="Мар'яна Мотика"
                ),
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-13.jpg"), "rb"),
                    caption="ЛОР"
                ),
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-14.jpg"), "rb"),
                    caption="Варлам"
                ),
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-15.jpg"), "rb"),
                    caption="Микола Іщук"
                ),
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "partner-16.jpg"), "rb"),
                    caption="Микола Іщук"
                )
            ]
            await query.message.reply_media_group(media=media_group)
        except FileNotFoundError:
            await query.message.reply_text(
                "❌ Не знайдено фото партнерів цієї категорії."
            )

    # --- СПІКЕРИ ЗА ТЕМАМИ ---
    
    # ТЕМА 1: Майбутнє ринку нерухомості
    if query.data == "theme_future":
        await query.message.reply_text("⏳ Завантажую спікерів теми «Майбутнє ринку нерухомості»...")
        try:
            media_group = [
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "speacer-1.jpg"), "rb"), 
                    caption="🎤 **Спікери теми:**\n«Майбутнє ринку нерухомості, закон про рієлторську діяльність та відбудова України»", 
                    parse_mode=ParseMode.MARKDOWN
                ),
                InputMediaPhoto(media=open(os.path.join(IMG_DIR, "speacer-2.jpg"), "rb")),
                InputMediaPhoto(media=open(os.path.join(IMG_DIR, "speacer-8.jpg"), "rb")),
                InputMediaPhoto(media=open(os.path.join(IMG_DIR, "speacer-9.jpg"), "rb"))
            ]
            await query.message.reply_media_group(media=media_group)
        except FileNotFoundError:
            await query.message.reply_text("❌ Помилка: Переконайся, що файли спікерів для цієї теми є в папці `img`.")

    # ТЕМА 2: Панельна дискусія забудовників
    elif query.data == "theme_builders":
        await query.message.reply_text("⏳ Завантажую спікерів панельної дискусії забудовників...")
        try:
            media_group = [
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "speacer-3.jpg"), "rb"), 
                    caption="🏢 **Учасники панельної дискусії забудовників:**\nLEV Development, IKON Development, Resident Development та Будинки і Люди", 
                    parse_mode=ParseMode.MARKDOWN
                ),
                InputMediaPhoto(media=open(os.path.join(IMG_DIR, "speacer-4.jpg"), "rb")),
                InputMediaPhoto(media=open(os.path.join(IMG_DIR, "speacer-5.jpg"), "rb"))
            ]
            await query.message.reply_media_group(media=media_group)
        except FileNotFoundError:
            await query.message.reply_text("❌ Помилка: Переконайся, що файли забудовників є в папці `img`.")

    # ТЕМА 3: Інвестиції, тренди та аналітика ринку
    elif query.data == "theme_investments":
        await query.message.reply_text("⏳ Завантажую спікерів теми «Інвестиції та аналітика»...")
        try:
            media_group = [
                InputMediaPhoto(
                    media=open(os.path.join(IMG_DIR, "speacer-6.jpg"), "rb"), 
                    caption="📈 **Спікери теми:**\n«Інвестиції, тренди та аналітика ринку нерухомості 2026»", 
                    parse_mode=ParseMode.MARKDOWN
                ),
                InputMediaPhoto(media=open(os.path.join(IMG_DIR, "speacer-7.jpg"), "rb"))
            ]
            await query.message.reply_media_group(media=media_group)
        except FileNotFoundError:
            await query.message.reply_text("❌ Помилка: Переконайся, що файли `speacer-6.jpg` та `speacer-7.jpg` є в папці `img`.")


# Налаштування додатка бота
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_callback))

# Запуск бота
if __name__ == "__main__":
    print("Бот запущений! Перевірте його роботу в Telegram.")
    app.run_polling()