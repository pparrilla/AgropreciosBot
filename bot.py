import logging as log
import os
import re
import signal
import sys
import threading
import time
from datetime import datetime, timedelta

import telebot

import pandas as pd
import datetime
import json


data_timer = None
sub_timer = None
subscriptions = []
subscriptions_dict = {}
subscriptions_path = os.environ.get('SUBS_PATH')
subscriptions_dict_path = os.environ.get('SUBS_DICT_PATH')
products_dict = {
    1 : {
        'id': 1,
        'name': 'Tomate Daniela Verde',
        'command': 'tomatedanielaverde'
    },
    2 : {
        'id': 2,
        'name': 'Tomate Daniela',
        'command': 'tomatedaniela'
    },
    3 : {
        'id': 3,
        'name': 'Tomate Pedra',
        'command': 'tomatepera'
    },
    4 : {
        'id': 4,
        'name': 'Tomate Ramo',
        'command': 'tomateramo'
    },
    5 : {
        'id': 5,
        'name': 'Pepino Frances',
        'command': 'pepinofrances'
    },
    6 : {
        'id': 6,
        'name': 'Pepino Espanol',
        'command': 'pepinoespanol'
    },
    7 : {
        'id': 7,
        'name': 'Pepino Almeria',
        'command': 'pepinoalmeria'
    },
    8 : {
        'id': 8,
        'name': 'Calabacin Fino',
        'command': 'calabacinfino'
    },
    9 : {
        'id': 9,
        'name': 'Calabacin Gordo',
        'command': 'calabacingordo'
    },
    10 : {
        'id': 10,
        'name': 'Berenjena Larga',
        'command': 'berenjenalarga'
    },
    11 : {
        'id': 11,
        'name': 'Berenjena Blanca',
        'command': 'berenjenablanca'
    },
    12 : {
        'id': 12,
        'name': 'Judia Helda',
        'command': 'judiahelda'
    },
    13 : {
        'id': 13,
        'name': 'Pimiento Largo Verde',
        'command': 'ptolargoverde'
    },
    14 :{
        'id': 14,
        'name': 'Pimiento Largo Rojo',
        'command': 'ptolargorojo'
    },
    15 : {
        'id': 15,
        'name': 'Pimiento Corto Verde',
        'command': 'ptocortoverde'
    },
    16 : {
        'id': 16,
        'name': 'Pimiento Corto Rojo',
        'command': 'ptocortorojo'
    },
    17 : {
        'id': 17,
        'name': 'Pimiento Corto Amarillo',
        'command': 'ptocortoamarillo'
    },
    18 : {
        'id': 18,
        'name': 'Pimiento Italiano Verde',
        'command': 'ptoitalianoverde'
    }
}

commands_product_list = []
commands_sub_list = []
commands_del_list = []

# Save in commands_product_list the products that the user can use
for key in products_dict:
    commands_product_list.append(products_dict[key]['command'])

for command in commands_product_list:
    commands_sub_list.append(command + '_sub')
    commands_del_list.append(command + '_del')


bot = telebot.TeleBot(os.environ.get('BOT_TOKEN'), threaded=False)

@bot.message_handler(commands=['start'])
def welcome_message(message):
    msg = "Este bot publica el precio del Pepino Almería en las diferentes subastas a las 15:00. Escribe /hoy o /ayer para obtener la tabla de precios"
    msg = msg + "\n\n"
    msg = msg + "Para suscribirse a otro producto, escribe /productos y selecciona el producto que quieres suscribirse"
    msg = msg + "\n\n"
    msg = msg + "Para desuscribirse de un producto, escribe /desuscribir y selecciona el producto que quieres desuscribirse"

    subscriptions_dict[str(message.chat.id)] = [7]
    save_subscriptions_dict()

    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=['ayuda'])
def help_message(message):
    msg = "Este bot publica el precio del Pepino Almería en las diferentes subastas a las 15:00. Escribe /hoy o /ayer para obtener la tabla de precios"
    msg = msg + "\n\n"
    msg = msg + "Para suscribirse a otro producto, escribe /productos y selecciona el producto que quieres suscribirse"
    msg = msg + "\n\n"
    msg = msg + "Para desuscribirse de un producto, escribe /desuscribir y selecciona el producto que quieres desuscribirse"

    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=['hoy', 'ayer'])
def send_menu(message):
    regex = re.compile('\/\w*')
    command = regex.search(message.text).group(0)
    msg = command.replace("/","")

    today = datetime.datetime.today()
    date = today.strftime("%d/%m/%Y")
    if msg == "ayer":
        yesterday = today - datetime.timedelta(days=1)
        date = yesterday.strftime("%d/%m/%Y")

    send_table(str(message.chat.id), date)

@bot.message_handler(commands=['cancelarsuscripcion'])
def unsubscribe(message):
    msg = 'Los productos disponibles para eliminar la suscripcion son: ' + '\n'

    for product in subscriptions_dict[str(message.chat.id)]:
        msg = msg + products_dict[product]['name'] + ' - /' + products_dict[product]['command'] + '_del' + '\n'

    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=commands_del_list)
def delete_products(message):
    product_name = message.text.replace("/","")
    product_name = product_name.replace("_del","")
    product_id = 0

    # Find the product id from the product name
    for product in products_dict:
        if products_dict[product]['command'] == product_name:
            product_id = products_dict[product]['id']
            break

    if subscriptions_dict[str(message.chat.id)] != [] and product_id in subscriptions_dict[str(message.chat.id)]:
        subscriptions_dict[str(message.chat.id)].remove(product_id)
        save_subscriptions_dict()

    msg = 'Eliminada la suscripción con éxito a ' + products_dict[product_id]['name'] +'!'
    msg = msg + '\n'
    msg = msg + 'Tus productos actuales son: '
    for product in subscriptions_dict[str(message.chat.id)]:
        msg = msg + products_dict[product]['name'] + ', '

    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=['suscripcion'])
def show_products(message):
    msg = 'Los productos disponibles para suscribirse son: ' + '\n'
    for product in products_dict:
        msg = msg + products_dict[product]['name'] + ' - /' + products_dict[product]['command'] + '_sub\n'

    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=commands_sub_list)
def save_products(message):
    product_name = message.text.replace("/","")
    product_name = product_name.replace("_sub","")
    product_id = 0

    # Find the product id from the product name
    for product in products_dict:
        if products_dict[product]['command'] == product_name:
            product_id = products_dict[product]['id']
            break

    if subscriptions_dict[str(message.chat.id)] == [] or not product_id in subscriptions_dict[str(message.chat.id)]:
        subscriptions_dict[str(message.chat.id)].append(product_id)
        save_subscriptions_dict()

    msg = '¡Suscrito con éxito a ' + products_dict[product_id]['name'] +'!'
    msg = msg + '\n'
    msg = msg + 'Tus productos actuales son: '
    for product in subscriptions_dict[str(message.chat.id)]:
        msg = msg + products_dict[product]['name'] + ', '

    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=['productos'])
def show_products(message):
    msg = 'Los productos para ver son: ' + '\n'
    for product in products_dict:
        msg = msg + products_dict[product]['name'] + ' - /' + products_dict[product]['command'] + '\n'

    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=commands_product_list)
def show_product(message):
    product_name = message.text.replace("/","")
    product_id = 0

    # Find the product id from the product name
    for product in products_dict:
        if products_dict[product]['command'] == product_name:
            product_id = products_dict[product]['id']
            break

    today = datetime.datetime.today()
    date = today.strftime("%d/%m/%Y")

    bot.send_message(message.chat.id, read_html(product_id, date), parse_mode='markdown')


def read_html(product_id, date):

    dfs = pd.read_html('https://www.agroprecios.com/precios-producto-tabla.php?prod=' + str(product_id) + '&fec=' + date)

    table = "```\n"
    table += products_dict[product_id]['name'] + '\n'

    for i in range(len(dfs[1][0])-2):
        row = ""
        for j in range(4):
            row = row + dfs[1][j][i+1] + "\t"
        table = table + row + "\n"

    table = table + "```"
    return table

def send_table(chat, date):
    for product_id in subscriptions_dict[chat]:
        msg = read_html(product_id, date)
        bot.send_message(chat, msg, parse_mode='markdown')

def load_subscriptions():
    global subscriptions_dict
    if os.path.exists(subscriptions_dict_path):
        with open(subscriptions_dict_path) as f:
            subscriptions_dict = json.load(f)

def save_subscriptions_dict():
    # Save dict to json file
    with open(subscriptions_dict_path, 'w') as outfile:
        json.dump(subscriptions_dict, outfile)

def process_subscriptions():
    today = datetime.datetime.today()
    date = today.strftime("%d/%m/%Y")

    for sub in subscriptions_dict.keys():
        send_table(sub, date)

    schedule_subscription_processing()


def schedule_subscription_processing():
    """Send menu every day at 15:00 (local date)"""
    global sub_timer

    now = datetime.datetime.now()
    next = now

    if now.hour < 14:
        next = now.replace(hour=14, minute=0)
    elif now.hour >= 14:
        next = now + timedelta(days=1)
        next = next.replace(hour=14, minute=0)

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
