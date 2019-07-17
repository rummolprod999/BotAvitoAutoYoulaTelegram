import os
import sqlite3

import telebot

PROXY_FILE = 'proxy.txt'
PROXY_LIST = []
BOT_TOKEN = '756646456'
CHANNEL_NAME = '@64564564'
SINGLE_RUN = True
FILE_LOG = 'bot_log.log'
WITH_PROXY = 0
DBNAME = 'avito.sqlite'
bot = telebot.TeleBot(BOT_TOKEN)


def get_proxy():
    with open(PROXY_FILE) as f:
        proxy_l = f.readlines()
    for i in proxy_l:
        PROXY_LIST.append(f'https://{i.strip()}')


def clear_log():
    if os.path.getsize(FILE_LOG) > 10 ** 6:
        with open(FILE_LOG, "w") as f:
            f.write("Log clears")


def create_db_if_notexist():
    if not os.path.exists(DBNAME):
        open(DBNAME, 'a').close()
        conn = sqlite3.connect(DBNAME)
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE `avito` (
 `id` INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
 `id_av` TEXT,
 `price` TEXT
)""", )
        conn.commit()
        cursor.execute("""CREATE INDEX `id_av` ON `avito` (
 `id_av`
)""", )
        conn.commit()
        cursor.execute("""CREATE INDEX `price` ON `avito` (
 `price`
)""", )
        conn.commit()
        cursor.execute("""CREATE INDEX `prim` ON `avito` (
`id`
)""", )
        conn.commit()
        cursor.close()
        conn.close()
