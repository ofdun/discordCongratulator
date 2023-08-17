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
from random import choice, randint
from exceptions import ImpossibleTimeError
import asyncio


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
    Congratulates with the todays holiday
    """
    if os.listdir('cache') == 0:
        return await ctx.respond('Сегодня нет праздников :(')
    picture_path = 'cache/' + choice(os.listdir('cache'))
    with open(picture_path, 'rb') as file:
        picture = discord.File(file)
    return await ctx.respond(file=picture)
    
@bot.slash_command(name="settime", guild_ids=[363961340345188353])
@commands.has_permissions(administrator=True)
async def settime(ctx: discord.commands.context.ApplicationContext,
                  time: discord.Option(str)) -> None:
    """
    Set time for everyday mailing
    """
    try:
        time = validate_time(time)
    except (ValueError, ImpossibleTimeError):
        return await ctx.respond(f"Твое iq равно {str(randint(30, 60))}")
    else:
        if server_in_db(server_id=ctx.guild_id):
            current_time = servers_mailing_time(server_id=ctx.guild_id)
            remove_server_from_db(server_id=ctx.guild_id)
            add_server_to_db(ctx.guild_id, ctx.channel_id, time)
            return await ctx.respond(f'Время рассылки изменено с {current_time} на {time}🤙🤣🤣')
        else:
            add_server_to_db(ctx.guild_id, ctx.channel_id, time)
            return await ctx.respond(f'Рассылка в {time} успешно подключена🤙🤣🤣')
        
@bot.slash_command(name="removemailing", guild_ids=[363961340345188353])
@commands.has_permissions(administrator=True)
async def removemailing(ctx: discord.commands.context.ApplicationContext) -> None:
    """
    Remove server from mailing list
    """
    remove_server_from_db(ctx.guild_id)
    return await ctx.respond("Рассылка отключена 😢🥺🥹☹️😓😞😖😭😥")
    
def validate_time(time: str) -> str:
    small_version = str( int( time.replace(':', '') ) )
    time_length = len(small_version)
    if time_length < 3 or time_length > 5:
        raise ImpossibleTimeError
    if time_length == 3:
        time = '0' + small_version[0] + ':' + small_version[1:]
    if int(time[3:])>60 or int(time[3:])<0 or int(time[:2])>=24 or int(time[:2])<0:
        raise ImpossibleTimeError
    return time


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
    
def servers_mailing_time(server_id: str) -> str:
    con = sqlite3.connect('instance/mailing.sqlite3')
    cursor = con.cursor()
    cursor.execute(f"SELECT * FROM mailing_servers WHERE server_id={server_id}")
    row = cursor.fetchone()
    con.close()
    
    return row[2]
    
def server_in_db(server_id: str) -> bool:
    con = sqlite3.connect('instance/mailing.sqlite3')
    cursor = con.cursor()
    cursor.execute(f"SELECT * FROM mailing_servers WHERE server_id={server_id}")
    row = cursor.fetchone()
    con.close()
    
    return row is not None
    
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
    
def send_photo(channel_id):
    channel = bot.get_channel(channel_id)
    if len(os.listdir('cache')) == 0:
        asyncio.run_coroutine_threadsafe(channel.send("Сегодня нет праздников 😢🥺🥹☹️😓😞😖😭😥"), bot.loop)
    else:
        photo_path = 'cache/' + choice(os.listdir('cache'))
        with open(photo_path, 'rb') as file:
            photo = discord.File(file)
        asyncio.run_coroutine_threadsafe(channel.send(file=photo), bot.loop)
                
def start_mailing() -> None:
    current_time = datetime.today().strftime("%H:%M")
    con = sqlite3.connect('instance/mailing.sqlite3')
    cursor = con.cursor()
    cursor.execute(f"""
                   SELECT * FROM mailing_servers
                   """)
    row = cursor.fetchall()
    con.close()
    
    for _, channel_id, time in row:
        if time == current_time:
            send_photo(channel_id=channel_id)
            

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