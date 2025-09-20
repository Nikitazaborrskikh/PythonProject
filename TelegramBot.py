import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import F

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен вашего бота (замените на реальный)
BOT_TOKEN = '8390549856:AAFIboWYouh91VssN7_kL2XM5Fza7bLp7Ic'

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключение к SQLite
conn = sqlite3.connect('birthdays.db')
cursor = conn.cursor()

# Создание таблицы, если не существует
cursor.execute('''
CREATE TABLE IF NOT EXISTS birthdays (
    user_id INTEGER,
    name TEXT,
    birthday TEXT,
    PRIMARY KEY (user_id, name)
)
''')
conn.commit()


# Функция для добавления дня рождения
async def add_birthday(user_id: int, name: str, date_str: str) -> str:
    try:
        # Валидация даты: dd.mm
        datetime.strptime(date_str, '%d.%m')
        if not name.strip():
            return "Имя не может быть пустым."

        cursor.execute('INSERT OR REPLACE INTO birthdays (user_id, name, birthday) VALUES (?, ?, ?)',
                       (user_id, name, date_str))
        conn.commit()
        return f"День рождения {name} ({date_str}) добавлен."
    except ValueError:
        return "Неправильный формат даты. Используйте dd.mm, например, 25.12."


# Функция для удаления дня рождения
async def remove_birthday(user_id: int, name: str) -> str:
    cursor.execute('DELETE FROM birthdays WHERE user_id = ? AND name = ?', (user_id, name))
    conn.commit()
    if cursor.rowcount > 0:
        return f"День рождения {name} удален."
    else:
        return f"День рождения для {name} не найден."


# Функция для просмотра всех дней рождения
async def list_birthdays(user_id: int) -> str:
    cursor.execute('SELECT name, birthday FROM birthdays WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    if not rows:
        return "У вас нет сохраненных дней рождения."
    return "\n".join([f"{name}: {date}" for name, date in rows])


# Функция для проверки и отправки напоминаний
async def check_reminders():
    today = datetime.now()
    reminder_date = today + timedelta(days=3)
    reminder_day = reminder_date.day
    reminder_month = reminder_date.month

    cursor.execute('SELECT user_id, name, birthday FROM birthdays')
    rows = cursor.fetchall()

    user_messages = {}
    for user_id, name, birthday in rows:
        bd_day, bd_month = map(int, birthday.split('.'))
        if bd_day == reminder_day and bd_month == reminder_month:
            if user_id not in user_messages:
                user_messages[user_id] = []
            user_messages[user_id].append(f"Через 3 дня день рождения у {name}! ({birthday})")

    for user_id, messages in user_messages.items():
        try:
            await bot.send_message(user_id, "\n".join(messages))
        except Exception as e:
            logging.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")


# Хендлер для /start и /help
@dp.message(Command(commands=['start', 'help']))
async def send_help(message: Message):
    help_text = """
    Привет! Я бот для напоминаний о днях рождения.

    Команды:
    /add имя dd.mm - Добавить день рождения (например, /add Анна 25.12)
    /remove имя - Удалить день рождения
    /list - Просмотреть все дни рождения
    /help - Показать эту помощь

    Напоминания отправляются за 3 дня до события.
    """
    await message.reply(help_text)


# Хендлер для /add
@dp.message(Command(commands=['add']))
async def handle_add(message: Message):
    args = message.text.split()[1:]
    if len(args) != 2:
        await message.reply("Использование: /add имя dd.mm")
        return
    name, date_str = args
    result = await add_birthday(message.from_user.id, name, date_str)
    await message.reply(result)


# Хендлер для /remove
@dp.message(Command(commands=['remove']))
async def handle_remove(message: Message):
    args = message.text.split()[1:]
    if len(args) != 1:
        await message.reply("Использование: /remove имя")
        return
    name = args[0]
    result = await remove_birthday(message.from_user.id, name)
    await message.reply(result)


# Хендлер для /list
@dp.message(Command(commands=['list']))
async def handle_list(message: Message):
    result = await list_birthdays(message.from_user.id)
    await message.reply(result)


# Обработка ошибок (для всех сообщений)
@dp.message(F.text)
async def handle_unknown(message: Message):
    await message.reply("Неизвестная команда. Используйте /help для списка команд.")


async def main():
    # Инициализация планировщика
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_reminders, CronTrigger(hour=9, minute=0))  # Ежедневно в 9:00
    scheduler.start()

    # Запуск polling
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())