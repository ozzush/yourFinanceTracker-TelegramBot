# -*- coding: cp1251 -*-

import telebot
from telebot import types
from pymongo import MongoClient
from datetime import date
from datetime import datetime
import re
import sys

sys.stderr = open("error_log.txt", "a")

bot = telebot.TeleBot('token')
client = MongoClient()
db = client.FinanceTracker

# templates
create_template = r'[Сс]оздай .+'
plan_category_template = r'[Пп]лан .+'
delete_template = r'-[Кк]ат .+'
plan_template = r'[Пп]ланирую ([\w ]+) ([\d]+) ([\d]+)'
buy_template = r'[Кк]упил ([\w ]+) ([\d]+) ([\d]+)'
earn_template = r'[Дд]оход -?[\d]+'


def check_user_in_bd(user, user_id):
    if not user:
        msg = "Тебя нет в моей базе данных. Чтобы пользоваться моим функционалом " \
              "необходимо добавиться в мою базу данных с помощью команды \"начнем\""
        bot.send_message(user_id, text=msg)
        return False
    return True


def generate_item_list(item_list, write_date=True):
    text = ""
    summ = 0
    for item in item_list:
        if write_date:
            text += f"{item['date']}: "
        text += f"{item['item']}, " \
               f"{item['count']} шт. по {item['value']} руб., " \
               f"всего {int(item['count']) * int(item['value'])} руб.\n"
        summ += int(item['count']) * int(item['value'])
    return text, summ


def budget_message(budget):
    return f"Твой бюджет — {budget} руб."


def planned_budget_message(budget):
    return f"Запланированно потратить {budget} руб."


def update_budget(user_id, value):
    db.users.update_one({'user_id': user_id}, {'$inc': {'budget': value}})
    user = db.users.find_one({'user_id': user_id})
    if value >= 0:
        msg = f"Добавил в бюджет {value} руб."
    else:
        msg = f"Вычел из бюджета {value} руб."
    return user, msg


def update_planned_budget(user_id, value):
    db.users.update_one({'user_id': user_id}, {'$inc': {'planned_budget': value}})
    user = db.users.find_one({'user_id': user_id})
    return user


@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    user_id = message.from_user.id
    user = db.users.find_one({'user_id': user_id})
    file = open("logs.txt", "a")
    log = str(datetime.now()) + ": message from " + message.from_user.first_name + ": " + message.text + "\n"
    file.write(log)

    # Пасхалка (я тестировала на ней кнопки)
    if message.text == "Привет":
        keyboard = types.InlineKeyboardMarkup()
        key_howre_my_fin = types.InlineKeyboardButton(text='Как мои финансы?', callback_data='greeting')
        keyboard.add(key_howre_my_fin)
        name = message.from_user.first_name
        bot.send_message(user_id, text=f"Привет, {name}", reply_markup=keyboard)

    # Помощь
    elif message.text == "/start" or message.text == "/help" or message.text == "помощь" or message.text == "Помощь":
        msg = "Вот что я умею:\n" \
              "<code>помощь</code> - вывести список команд\n" \
              "<code>начнем</code> - начать учет своих финансов (добавиться в базу данных)\n" \
              "<code>забудь меня</code> - удалить всю информацию о себе из базы данных\n" \
              "<code>создай *категория*</code> - создать новую категорию\n" \
              "<code>-кат *категория*</code> - удалить категорию\n" \
              "<code>категории</code> - посмотреть список всех категорий. " \
                    "Далее можно выбрать категорию и узнать подробную инфоромацию о ней\n" \
              "<code>план *категория*</code> - посмотреть запланированные расходы в категории\n" \
              "<code>планирую *позиция* *стоимость* *количество*</code> - запланировать трату\n" \
              "<code>купил *позиция* *стоимость* *количество*</code> - записать трату. Хочется, чтобы при этом " \
                    "список запланированного обновлялся автоматически, но это пока не реализованно.\n" \
              "<code>-поз *позиция*</code> - удалить позицию (не реализованно)\n" \
              "<code>доход *значение*</code> - записать доход. Можно записать отрицательное значение\n" \
              "<code>бюджет</code> - показать бюджет\n" \
              "<code>бюджет план</code> - показать, сколько суммарно стоят запланированные покупки\n" \
              "<code>статистика *период*</code> - узнать статистику по категориям " \
                    "за прошедший период (день/неделя/месяц/год/все время) (не реализованно)\n\n" \
              "Замечания по использованию:\n" \
              "1. В названиях категорий и позиций могут быть любые символы, " \
                    "в том числе цифры и пробелы, но не двоеточие :. " \
                    "Предупреждение на это пока не стоит\n" \
              "2. Не экспериментируй с длиной цены, количества и названий категорий и позиций. " \
                    "Если команды \"планирую\" и \"купил\" не проходят, то, вероятно, " \
                    "ты пытаешься записать слишком длинную позицию/цену. " \
                    "Можно попробовать записать позицию в категорию с более коротким названием или " \
                    "укоротить саму позицию\n"
        bot.send_message(user_id, text=msg, parse_mode="html")
        if not user:
            bot.send_message(user_id, text="Чтобы начать пользоватся моим функционалом напиши \"начнем\"")

    # Записаться в БД
    elif re.match(r"[Нн]ачн[её]м\b", message.text):
        # Корректность запроса
        if user:
            msg = "Ты уже есть в моей базе"
            bot.send_message(user_id, text=msg)
            return

        template = {"user_id": user_id,
                    "budget": 0,
                    "planned_budget": 0,
                    "categories": {}}
        db.users.insert_one(template)
        msg = "Добавил тебя в свою базу"
        bot.send_message(user_id, text=msg)

    # Удалиться из БД
    elif re.match(r"[Зз]абудь меня\b", message.text):
        # Корректность запроса
        if not user:
            msg = "Тебя и так не было в моей базе"
            bot.send_message(user_id, text=msg)
            return

        db.users.delete_one({'user_id': user_id})
        msg = "Удалил тебя из своей базы"
        bot.send_message(user_id, text=msg)

    # Создать категорию
    elif re.match(create_template, message.text):
        # Корректность запроса
        if not check_user_in_bd(user, user_id):
            return

        category = message.text.split(' ', 1)[1]

        # Корректность запроса
        if category in user['categories']:
            msg = f"Категория {category} уже существует"
            bot.send_message(user_id, text=msg)
            return

        template = {'items': [],
                    'planned_items': []}
        db.users.update_one({'user_id': user_id}, {'$set': {f'categories.{category}': template}})
        msg = f"Создал новую категорию \"{category}\""
        bot.send_message(user_id, text=msg)

    # Удалить категорию
    elif re.match(delete_template, message.text):
        # Корректность запроса
        if not check_user_in_bd(user, user_id):
            return

        category = message.text.split(' ', 1)[1]

        # Корректность запроса
        if not (category in user['categories']):
            msg = f"Категории \"{category}\" не существует"
            bot.send_message(user_id, text=msg)
            return

        user['categories'].pop(category)
        db.users.update_one({'user_id': user_id}, {'$set': {'categories': user['categories']}})
        msg = f"Удалил категорию \"{category}\""
        bot.send_message(user_id, text=msg)

    # Список категорий
    elif re.match(r"[Кк]атегории\b", message.text):
        # Корректность запроса
        if not check_user_in_bd(user, user_id):
            return

        # Корректность запроса
        if not user['categories']:
            msg = "Ты еще не создал ни одной категории. " \
                  "Чтобы создать категорию, используй команду \"создай *имя категории*\". " \
                  "Например: создай Игры и развлечения"
            bot.send_message(user_id, text=msg)
            return

        keyboard = types.InlineKeyboardMarkup()
        for category in user['categories']:
            key = types.InlineKeyboardButton(text=category, callback_data=f"cat {category}")
            keyboard.add(key)
        msg = "Вот список всех твоих категорий. Нажми на категорию чтобы узнать о ней больше"
        bot.send_message(user_id, text=msg, reply_markup=keyboard)

    # Запись доходов
    elif re.match(earn_template, message.text):
        # Корректность запроса
        if not check_user_in_bd(user, user_id):
            return

        value = int(message.text.split(' ', 1)[1])
        user, msg = update_budget(user_id, value)
        bot.send_message(user_id, text=msg)
        bot.send_message(user_id, text=budget_message(user['budget']))

    # Показать бюджет
    elif re.match(r'[Бб]юджет$', message.text):
        # Корректность запроса
        if not check_user_in_bd(user, user_id):
            return

        bot.send_message(user_id, text=budget_message(user['budget']))

    # Показать запланированный бюджет
    elif re.match(r'[Бб]юджет план', message.text):
        # Корректность запроса
        if not check_user_in_bd(user, user_id):
            return

        bot.send_message(user_id, text=planned_budget_message(user['planned_budget']))

    # Запись позиций в купленное или планируемое
    elif re.match(buy_template, message.text) or re.match(plan_template, message.text):
        # Корректность запроса
        if not check_user_in_bd(user, user_id):
            return
        if not user['categories']:
            msg = "Ты еще не создал ни одной категории, чтобы доабвлять туда позиции. " \
                  "Чтобы создать категорию, используй команду \"создай *имя категории*\". " \
                  "Например: создай Игры и развлечения"
            bot.send_message(user_id, text=msg)
            return

        keyboard = types.InlineKeyboardMarkup()
        for category in user['categories']:
            key = types.InlineKeyboardButton(text=category, callback_data=f"{message.text}:{category}")
            keyboard.add(key)
        msg = "К какой категории ты хочешь отнести эту позицию?"
        bot.send_message(user_id, text=msg, reply_markup=keyboard)

    # Посмотреть запланированное в категории
    elif re.match(plan_category_template, message.text):
        category = message.text.split(' ', 1)[1]

        # Корректность запроса
        if not (category in user['categories']):
            msg = f"Категории {category} не существует. Создай ее с помощью команды \"создай {category}\""
            bot.send_message(user_id, text=msg)
            return

        msg = f"Планирующиеся покупки в категории {category}:\n\n"
        items = user['categories'][category]['planned_items']
        text, summ = generate_item_list(items, write_date=False)
        msg += text
        bot.send_message(user_id, msg)
        msg = f"Всего планируется потратить {summ} руб."
        bot.send_message(user_id, msg)

    else:
        bot.send_message(user_id, "Я тебя не понимаю. Напиши \"помощь\".")

    log = "    answered successfully at " + str(datetime.now()) + "\n"
    file.write(log)
    file.close()


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    user_id = call.from_user.id
    user = db.users.find_one({'user_id': user_id})
    file = open("logs.txt", "a")
    log = str(datetime.now()) + ": callback query from " + call.from_user.first_name + ": " + call.data + "\n"
    file.write(log)

    # Пасхалка (я тестировала на ней кнопки)
    if call.data == "greeting":
        msg = "Замечательно!"
        bot.send_message(user_id, msg)

    # Статистика в категории, переходим сюда по кнопке после команды "категории"
    elif re.match(r"cat .+", call.data):
        category = call.data.split(' ', 1)[1]
        msg = f"Покупки в категории {category} за все время:\n\n"
        text, summ = generate_item_list(user['categories'][category]['items'])
        msg += text
        bot.send_message(user_id, msg)
        msg = f"Всего за все время потрачено {summ} руб."
        bot.send_message(user_id, msg)

        msg = "Планирующиеся покупки:\n\n"
        text, summ = generate_item_list(user['categories'][category]['planned_items'], write_date=False)
        msg += text
        bot.send_message(user_id, msg)
        msg = f"Всего планируется потратить {summ} руб."
        bot.send_message(user_id, msg)

    # Запись позиции в купленное или запланированное
    elif re.match(buy_template, call.data) or re.match(plan_template, call.data):
        info = call.data.split(':', 1)
        category = info[1]
        command = re.match(buy_template, info[0])
        if command:
            value = - int(command[2]) * int(command[3])
            user, msg = update_budget(user_id, value)
            template = buy_template
            path = "items"
            word = "купленное"
        else:
            command = re.match(plan_template, info[0])
            value = int(command[2]) * int(command[3])
            user = update_planned_budget(user_id, value)
            template = plan_template
            path = "planned_items"
            word = "запланированное"
        item, value, count = re.findall(template, info[0])[0]
        new_position = {'date': str(date.today()),
                    'item': item,
                    'value': value,
                    'count': count}
        db.users.update_one({'user_id': user_id}, {'$push': {f"categories.{category}.{path}": new_position}})

        msg = f"Добавил новую позицию \"{item}\" стоимостью {value} в количестве {count} в {word} в категории {category}"
        bot.send_message(user_id, msg)
        bot.send_message(user_id, text=budget_message(user['budget']))
        bot.send_message(user_id, text=planned_budget_message(user['planned_budget']))

    log = "    answered successfully at " + str(datetime.now()) + "\n"
    file.write(log)
    file.close()


bot.polling(none_stop=True, interval=0)
