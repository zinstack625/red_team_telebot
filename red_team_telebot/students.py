from red_team_telebot.telegram import bot
from asyncio import gather
import red_team_telebot.db as db
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton, User


def get_name(user: User):
    return user.username if user.username is not None\
           else user.first_name + f" {user.last_name}" if user.last_name is not None else ""


async def student_start(msg: Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*[KeyboardButton(option)
                   for option in ['Get mail']])
    await bot.send_message(msg.from_user.id,
                           'Hi, student',
                           reply_markup=keyboard)


@bot.message_handler(func=lambda x: x.text == 'Get mail')
async def get_mail(msg: Message):
    student = await db.db['Students'].find_one({'chat_id': msg.from_user.id})
    if student is not None and student['email'] is not None:
        await bot.send_message(msg.from_user.id,
                               'You\'ve already got an email address:\n'
                               f'{student["email"]["email"]}\n'
                               f'<tg-spoiler>{student["email"]["password"]}</tg-spoiler>')
        return
    email = await db.db['Emails'].find_one({})
    if student is not None:
        if email is None:
            await bot.send_message(msg.from_user.id,
                                   'No emails available yet. '
                                   'I\'m gonna make sure you get one as soon as possible. '
                                   'You\'re in queue!')
            return
        await gather(bot.send_message(msg.from_user.id,
                                      'There is an email available! Here you go:\n'
                                      f'{email["email"]}\n'
                                      f'<tg-spoiler>{email["password"]}</tg-spoiler>'),
                     *[bot.send_message(admin['chat_id'],
                                        f'Student: <a href="tg://user?id={msg.from_user.id}">{get_name(msg.from_user)}</a> '
                                        f'got email {email["email"]}')
                       async for admin in db.db['Admins'].find({})],
                     db.db['Students'].update_one({'_id': student['_id']},
                                                  {'$set': {'email': email}}),
                     db.db['Emails'].delete_one({'_id': email['_id']}))
        return
    student = {'chat_id': int(msg.from_user.id), 'name': get_name(msg.from_user)}
    if email is not None:
        student['email'] = email
        await bot.send_message(msg.from_user.id,
                               'There is an email available! Here you go:\n'
                               f'{email["email"]}\n'
                               f'<tg-spoiler>{email["password"]}</tg-spoiler>')
    else:
        await bot.send_message(msg.from_user.id,
                               'There\'s no more emails available! '
                               'Try contacting your teacher about getting some more!')
    await db.db['Students'].insert_one(student)
