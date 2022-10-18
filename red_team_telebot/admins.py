from telebot.asyncio_handler_backends import StatesGroup, State
from telebot import asyncio_filters
from telebot.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from red_team_telebot.telegram import bot
import json
from bson.objectid import ObjectId
import red_team_telebot.db as db
from asyncio import gather
import re

bot.add_custom_filter(asyncio_filters.StateFilter(bot))
bot.add_custom_filter(asyncio_filters.IsDigitFilter())


class AdminStates(StatesGroup):
    add_email = State()
    add_email_json = State()


async def admin_start(msg: Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*[KeyboardButton(option)
                   for option in ['Add email', 'Add email (json)', 'List and remove', 'Students']])
    await bot.send_message(msg.from_user.id, 'Hi, admin', reply_markup=keyboard)


async def give_out_email(msg: Message, email: dict):
    student = await db.db['Students'].find_one({'email': {'$exists': False}})
    if student is not None:
        await gather(bot.send_message(msg.from_user.id,
                                      f'There was a student waiting, {email["email"]}:{email["password"]} went out to '
                                      f'<a href="tg://user?id={student["chat_id"]}">@{student["name"]}</a>'),
                     bot.send_message(student['chat_id'], 
                                      'There is an email available! Here you go:\n'
                                      f'{email["email"]}\n'
                                      f'<tg-spoiler>{email["password"]}</tg-spoiler>'),
                     db.db['Students'].update_one({'_id': student['_id']},
                                                  {'$set': {'email': email}}))
        return
    await db.db['Emails'].insert_one(email)


@bot.message_handler(func=lambda x: x.text == 'Add email')
async def add_email(msg: Message):
    admin = await db.db['Admins'].find_one({'chat_id': msg.from_user.id})
    if admin is None:
        # keep silent and act like nothing happened
        return
    await gather(bot.set_state(msg.from_user.id, AdminStates.add_email),
                 bot.send_message(msg.from_user.id,
                                  'Listening for emails. '
                                  'Write them in the following messages one at a time. \n\n'
                                  '<i>Format</i>:\n'
                                  'email@example.com:p4s$w0rd\n\n'
                                  'When you\'re ready to stop, send "__Stop__"'))


@bot.message_handler(state=AdminStates.add_email)
async def stateful_add_email(msg: Message):
    if str.lower(msg.text) == "stop":
        await gather(bot.delete_state(msg.from_user.id),
                     bot.send_message(msg.from_user.id, 'Ok, stopping'))
        return
    tasks = []
    for line in msg.text.split('\n'):
        match = re.match('(.*):(.*)', line)
        if match is None:
            await gather(bot.delete_state(msg.from_user.id),
                         bot.send_message(msg.from_user.id, f'Invalid format: {line}\nskipping...'))
            continue
        email = match.group(1)
        password = match.group(2)
        if await db.db['Emails'].find_one({'email': email}) is not None:
            await bot.send_message(msg.from_user.id, 'This one already exists, not adding...')
            continue
        tasks.append(give_out_email(msg, {'email': email, 'password': password}))
    await gather(bot.send_message(msg.from_user.id, 'Got it'),
                 *tasks)

@bot.message_handler(func=lambda x: x.text == 'Add email (json)')
async def add_email_json(msg: Message):
    admin = await db.db['Admins'].find_one({'chat_id': msg.from_user.id})
    if admin is None:
        # keep silent and act like nothing happened
        return
    await gather(bot.set_state(msg.from_user.id, AdminStates.add_email_json),
                 bot.send_message(msg.from_user.id,
                                  'Listening for emails. '
                                  'Write them in the following messages one at a time. \n\n'
                                  '<i>Format</i>:\n'
                                  '{ "json": "email@example.com",\n'
                                  '"password": "p4s$w0rd" }\n\n'
                                  'When you\'re ready to stop, send "__Stop__"'))


@bot.message_handler(state=AdminStates.add_email_json)
async def state_add_email_json(msg: Message):
    if str.lower(msg.text) == "stop":
        await gather(bot.delete_state(msg.from_user.id),
                     bot.send_message(msg.from_user.id, 'Ok, stopping'))
        return
    try:
        msg_dict = json.loads(msg.text)
    except json.JSONDecodeError:
        await gather(bot.delete_state(msg.from_user.id),
                     bot.send_message(msg.from_user.id, 'No format detected, stopping listening'))
        return
    if type(msg_dict) is dict:
        if await db.db['Emails'].find_one({'email': str(msg_dict['email'])}) is not None:
            await bot.send_message(msg.from_user.id, 'This one already exists, not adding')
            return
        await gather(give_out_email({'email': str(msg_dict['email']), 'password': str(msg_dict['password'])}),
                     bot.send_message(msg.from_user.id, 'Got it'))
    elif type(msg_dict) is list:
        tasks = []
        for pair in msg_dict:
            if await db.db['Emails'].find_one({'email': str(pair['email'])}) is not None:
                tasks.append(bot.send_message(msg.from_user.id, f'This one: {str(pair["email"])}:{str(pair["password"])}\nalready exists, not adding'))
                continue
            tasks.append(give_out_email({'email': str(pair['email']), 'password': str(pair['password'])}))
        await gather(bot.send_message(msg.from_user.id, 'Got it'),
                     *tasks)


@bot.message_handler(func=lambda x: x.text == 'List and remove')
async def list_and_remove(msg: Message):
    admin = await db.db['Admins'].find_one({'chat_id': msg.from_user.id})
    if admin is None:
        # keep silent and act like nothing happened
        return
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(*[InlineKeyboardButton(f'{doc["email"]}', callback_data=f'remove_email_{doc["_id"]}')
                   async for doc in db.db['Emails'].find({})])
    await bot.send_message(msg.from_user.id, 'Here\'s some', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda x: x.data.startswith('remove_email_'))
async def remove_email(call: CallbackQuery):
    await db.db['Emails'].delete_one({'_id': ObjectId(call.data[13:])})

    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(*[InlineKeyboardButton(f'{doc["email"]}', callback_data=f'remove_email_{doc["_id"]}')
                   async for doc in db.db['Emails'].find({})])
    await gather(bot.edit_message_reply_markup(call.from_user.id, call.message.id, reply_markup=keyboard),
                 bot.answer_callback_query(call.id))


@bot.message_handler(func=lambda x: x.text == 'Students')
async def students(msg: Message):
    message = "".join([f'Student: <a href="tg://user?id={student["chat_id"]}">@{student["name"]}</a>\n'
                       f'Email: {student["email"]["email"]}\n\n'
                       async for student in db.db['Students'].find({})])
    await bot.send_message(msg.from_user.id, message)
