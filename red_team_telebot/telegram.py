from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage

bot = None


def InitBot(token: str):
    global bot
    bot = AsyncTeleBot(token,
                       state_storage=StateMemoryStorage(),
                       parse_mode='HTML')
