import asyncio
import json

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from bestconfig import Config

# Токен вашего бота, полученный от @BotFather
config = Config()
with open("./app/users.json", encoding="utf-8") as f:
    users: dict = json.load(f)

# Инициализация бота и диспетчера
bot = Bot(token=config.get("bot_token"))
# dp = Dispatcher()


async def send_signal(text: str):
    tasks = []
    for user in users.keys():
        tasks.append(
            bot.send_message(
                user,
                text,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True,
            )
        )
    await asyncio.gather(*tasks)


# # Обработчик команды /start
# @dp.message(CommandStart())
# async def cmd_start(message: types.Message):
#     # Отправляем приветственное сообщение
#     await message.answer("Привет! Я демонстрационный бот.")
