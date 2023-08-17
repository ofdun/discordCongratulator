from postcards import download_todays_postcards
import os
import logging
import sqlite3
import schedule
from datetime import datetime
from threading import Thread
import discord
from discord.ext import commands
import json
from const import HELP
from random import choice


with open('settings.json') as f:
    SETTINGS = json.load(f)['settings']


bot = commands.Bot(command_prefix=SETTINGS['prefix'],
                   intents=discord.Intents.all(),
                   case_insensitive=True,
                   self_bot=True)

@bot.slash_command(name="help", guild_ids=[363961340345188353])
async def help(ctx) -> None:
    """
    Displays default info in chat
    """
    await ctx.respond(HELP)
    
@bot.slash_command(name="gz", guild_ids=[363961340345188353])
async def gz(ctx: discord.commands.context.ApplicationContext) -> None:
    """
    Congratulates author with the todays holiday
    """
    if os.listdir('cache') == 0:
        return await ctx.respond('Сегодня нет праздников :(')
    picture_path = 'cache/' + choice(os.listdir('cache'))
    with open(picture_path, 'rb') as file:
        picture = discord.File(file)
    return await ctx.respond(file=picture)
    


def setup_logging() -> None:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    logging.basicConfig(level=logging.INFO, filename='logs/logs.log',
                        format='%(asctime)s %(levelname)s %(message)s', encoding='UTF-8')
    
def create_db() -> None:
    os.mkdir('instance')
    con = sqlite3.connect('instance/mailing.sqlite3')
    cursor = con.cursor()
    cursor.execute("""
                CREATE TABLE IF NOT EXISTS mailing_servers (
                    server_id INTEGER UNIQUE NOT NULL,
                    channel_id INTEGER NOT NULL,
                    time TEXT NOT NULL
                )
                """)
    con.commit()
    con.close()
    
    logging.info("mailing_servers database were successfully created")
    
def add_server_to_db(server_id: str, channel_id: str, time: str) -> None:
    con = sqlite3.connect('instance/mailing.sqlite3')
    cursor = con.cursor()
    cursor.execute(f"""
                   INSERT INTO mailing_servers (server_id, channel_id, time)
                   VALUES ({server_id}, {channel_id}, "{time}")
                   """)
    con.commit()
    con.close()
    
    logging.info(f"User {server_id} subscribed for mailing")
    
def remove_server_from_db(server_id: str) -> None:
    con = sqlite3.connect('instance/mailing.sqlite3')
    cursor = con.cursor()
    cursor.execute(f"""
                   DELETE FROM mailing_servers WHERE server_id={server_id}
                   """)
    con.commit()
    con.close()
    
    logging.info(f"Server {server_id} was deleted from mailing_servers_db")
    
def start_mailing() -> None:
    current_time = datetime.today().strftime("%H:%M")
    con = sqlite3.connect('instance/mailing.sqlite3')
    cursor = con.cursor()
    cursor.execute(f"""
                   SELECT * FROM mailing_servers
                   """)
    row = cursor.fetchall()
    con.close()
    
    for server_id, channel_id, time in row:
        if time == current_time:
            pass
            # TODO sending to a chat

# Downloading and checking mailing
def start_schedule_tasks() -> None:
    setup_logging()
    if not os.path.exists('instance'):
        create_db()
    if not os.path.exists('cache'):
        os.mkdir('cache')
        download_todays_postcards()
    elif len(os.listdir('cache')) == 0:
        download_todays_postcards()
    schedule.every().day.at("00:15").do(download_todays_postcards)
    schedule.every().minute.do(start_mailing)
    logging.info("schedule tasks were started")
    while True:
        schedule.run_pending()

if __name__ == '__main__':
    Thread(target=start_schedule_tasks).start()
    bot.run(SETTINGS['token'])