#!/usr/bin/end python3

from asyncio import run
import red_team_telebot.db as db
import red_team_telebot.telegram
import motor
# from logging import basicConfig, DEBUG
import sys
import signal

import argparse


def signal_handler(sig, frame):
    sys.exit(0)


async def main():
    import red_team_telebot.admins
    import red_team_telebot.common
    import red_team_telebot.students
    await red_team_telebot.telegram.bot.infinity_polling()

if __name__ == '__main__':
    # basicConfig(level=DEBUG)
    cli_args = argparse.ArgumentParser()
    cli_args.add_argument('-t', '--token', required=True)
    cli_args.add_argument('-d', '--db', required=True)
    args = cli_args.parse_args()
    red_team_telebot.telegram.InitBot(args.token)
    db.client = motor.motor_asyncio.AsyncIOMotorClient(args.db)
    db.db = db.client['red_team']
    signal.signal(signal.SIGINT, signal_handler)
    run(main())
