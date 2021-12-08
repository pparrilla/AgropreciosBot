import logging as log
import os
import re
import signal
import sys
import threading
import time
from datetime import datetime, date, timedelta

import telebot

import pandas as pd
import datetime


data_timer = None
sub_timer = None
subscriptions = []


bot = telebot.TeleBot(os.environ.get('BOT_TOKEN'), threaded=False)

@bot.message_handler(commands=['start'])
def welcome_message(message):
    msg = "Este bot publica el precio del Pepino Almería en las diferentes subastas. Escribe /hoy o /ayer para obtener la tabla de precios"
    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=['hoy', 'ayer'])
def send_menu(message):
    suggest_subscription_msg = '*NOVEDAD*: Ahora puedes suscribirte y *recibir el precio diario automáticamente*. Para ello, utiliza el comando /suscripcion'
    bot.send_message(message.chat.id, suggest_subscription_msg,
                     parse_mode='markdown')

    regex = re.compile('\/\w*')
    command = regex.search(message.text).group(0)
    msg = command.replace("/","")

    today = datetime.datetime.today()
    date = today.strftime("%d/%m/%Y")
    if msg == "ayer":
        yesterday = today - datetime.timedelta(days=1)
        date = yesterday.strftime("%d/%m/%Y")

    send_table(message.chat.id, date)

@bot.message_handler(commands=['suscripcion'])
def subscribe(message):

    if message.chat.id in subscriptions:
        msg = 'Ya estás suscrito. Recibirás el precio cada día a las *15:00*. Puedes cancelar la suscripcion usando /cancelarsuscripcion'
        bot.send_message(message.chat.id, msg, parse_mode='markdown')
        return

    subscriptions.append(message.chat.id)
    persist_subscriptions()

    msg = '¡Suscrito con éxito!. Recibirás el precio cada día a las *15:00*. Puedes cancelar la suscripcion usando /cancelarsuscripcion'
    bot.send_message(message.chat.id, msg, parse_mode='markdown')


@bot.message_handler(commands=['cancelarsuscripcion'])
def unsubscribe(message):

    if message.chat.id in subscriptions:
        subscriptions.remove(message.chat.id)
        persist_subscriptions()

    msg = '¡Suscripción cancelada!. Puedes volver a suscribirte en cualquier momento usando el comando /suscripcion'
    bot.send_message(message.chat.id, msg)


def read_html(date):
    dfs = pd.read_html('https://www.agroprecios.com/precios-producto-tabla.php?prod=7&fec=' + date)

    table = "```\n"

    for i in range(len(dfs[1][0])-2):
        row = ""
        for j in range(4):
            row = row + dfs[1][j][i+1] + "\t"
        table = table + row + "\n"

    table = table + "```"
    return table

def send_table(chat, date):
    msg = read_html(date)
    bot.send_message(chat, msg, parse_mode='markdown')


def load_subscriptions():
    global subscriptions
    if os.path.exists('subscriptions.txt'):
        file = open('subscriptions.txt', 'r')
        for sub in file.readlines():
            subscriptions.append(int(sub.replace('\n', '')))


def persist_subscriptions():
    file = open('subscriptions.txt', 'w')
    for sub in subscriptions:
        file.write(str(sub) + '\n')
    file.close()


def process_subscriptions():
    today = datetime.datetime.today()
    date = today.strftime("%d/%m/%y")

    for sub in subscriptions:
        send_table(sub, date)

    schedule_subscription_processing()


def schedule_subscription_processing():
    """Send menu every day at 15:00 (local date)"""
    global sub_timer

    now = datetime.datetime.now()
    next = now

    if now.hour < 15:
        next = now.replace(hour=15, minute=0)
    elif now.hour >= 15:
        next = now + timedelta(days=1)
        next = next.replace(hour=15, minute=0)

    # if next.weekday() == 7:
    #     # Dining hall closed on sundays, so schedule to next monday
    #     next = next + timedelta(days=1)

    delta = next.timestamp() - now.timestamp()
    log.info('Subscriptions processing delta: ' + str(delta / 3600) + ' hours')
    sub_timer = threading.Timer(delta, process_subscriptions)
    sub_timer.start()


def main():
    log.basicConfig(level=log.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

    load_subscriptions()
    schedule_subscription_processing()

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        try:
            log.info('Starting bot polling...')
            bot.polling()
        except Exception as err:
            log.error("Bot polling error: {0}".format(err.args))
            bot.stop_polling()
            time.sleep(30)


def signal_handler(signal_number, frame):
    print('Received signal ' + str(signal_number)
          + '. Trying to end tasks and exit...')
    bot.stop_polling()
    data_timer.cancel()
    sub_timer.cancel()
    sys.exit(0)

if __name__ == "__main__":
    main()
