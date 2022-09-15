from telebot.types import Message
from red_team_telebot.telegram import bot
import red_team_telebot.db as db
from red_team_telebot.admins import admin_start
from red_team_telebot.students import student_start


@bot.message_handler(commands=['start'])
async def start(msg: Message):
    admins = db.db['Admins']
    admin = await admins.find_one({'chat_id': msg.from_user.id})
    if admin is not None:
        await admin_start(msg)
        return
    await student_start(msg)
