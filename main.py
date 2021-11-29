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
create_template = r'[��]����� .+'
plan_category_template = r'[��]��� .+'
delete_template = r'-[��]�� .+'
plan_template = r'[��]������� ([\w ]+) ([\d]+) ([\d]+)'
buy_template = r'[��]���� ([\w ]+) ([\d]+) ([\d]+)'
earn_template = r'[��]���� -?[\d]+'


def check_user_in_bd(user, user_id):
    if not user:
        msg = "���� ��� � ���� ���� ������. ����� ������������ ���� ������������ " \
              "���������� ���������� � ��� ���� ������ � ������� ������� \"������\""
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
               f"{item['count']} ��. �� {item['value']} ���., " \
               f"����� {int(item['count']) * int(item['value'])} ���.\n"
        summ += int(item['count']) * int(item['value'])
    return text, summ


def budget_message(budget):
    return f"���� ������ � {budget} ���."


def planned_budget_message(budget):
    return f"�������������� ��������� {budget} ���."


def update_budget(user_id, value):
    db.users.update_one({'user_id': user_id}, {'$inc': {'budget': value}})
    user = db.users.find_one({'user_id': user_id})
    if value >= 0:
        msg = f"������� � ������ {value} ���."
    else:
        msg = f"����� �� ������� {value} ���."
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

    # �������� (� ����������� �� ��� ������)
    if message.text == "������":
        keyboard = types.InlineKeyboardMarkup()
        key_howre_my_fin = types.InlineKeyboardButton(text='��� ��� �������?', callback_data='greeting')
        keyboard.add(key_howre_my_fin)
        name = message.from_user.first_name
        bot.send_message(user_id, text=f"������, {name}", reply_markup=keyboard)

    # ������
    elif message.text == "/start" or message.text == "/help" or message.text == "������" or message.text == "������":
        msg = "��� ��� � ����:\n" \
              "<code>������</code> - ������� ������ ������\n" \
              "<code>������</code> - ������ ���� ����� �������� (���������� � ���� ������)\n" \
              "<code>������ ����</code> - ������� ��� ���������� � ���� �� ���� ������\n" \
              "<code>������ *���������*</code> - ������� ����� ���������\n" \
              "<code>-��� *���������*</code> - ������� ���������\n" \
              "<code>���������</code> - ���������� ������ ���� ���������. " \
                    "����� ����� ������� ��������� � ������ ��������� ����������� � ���\n" \
              "<code>���� *���������*</code> - ���������� ��������������� ������� � ���������\n" \
              "<code>�������� *�������* *���������* *����������*</code> - ������������� �����\n" \
              "<code>����� *�������* *���������* *����������*</code> - �������� �����. �������, ����� ��� ���� " \
                    "������ ���������������� ���������� �������������, �� ��� ���� �� ������������.\n" \
              "<code>-��� *�������*</code> - ������� ������� (�� ������������)\n" \
              "<code>����� *��������*</code> - �������� �����. ����� �������� ������������� ��������\n" \
              "<code>������</code> - �������� ������\n" \
              "<code>������ ����</code> - ��������, ������� �������� ����� ��������������� �������\n" \
              "<code>���������� *������*</code> - ������ ���������� �� ���������� " \
                    "�� ��������� ������ (����/������/�����/���/��� �����) (�� ������������)\n\n" \
              "��������� �� �������������:\n" \
              "1. � ��������� ��������� � ������� ����� ���� ����� �������, " \
                    "� ��� ����� ����� � �������, �� �� ��������� :. " \
                    "�������������� �� ��� ���� �� �����\n" \
              "2. �� ��������������� � ������ ����, ���������� � �������� ��������� � �������. " \
                    "���� ������� \"��������\" � \"�����\" �� ��������, ��, ��������, " \
                    "�� ��������� �������� ������� ������� �������/����. " \
                    "����� ����������� �������� ������� � ��������� � ����� �������� ��������� ��� " \
                    "��������� ���� �������\n"
        bot.send_message(user_id, text=msg, parse_mode="html")
        if not user:
            bot.send_message(user_id, text="����� ������ ����������� ���� ������������ ������ \"������\"")

    # ���������� � ��
    elif re.match(r"[��]���[�]�\b", message.text):
        # ������������ �������
        if user:
            msg = "�� ��� ���� � ���� ����"
            bot.send_message(user_id, text=msg)
            return

        template = {"user_id": user_id,
                    "budget": 0,
                    "planned_budget": 0,
                    "categories": {}}
        db.users.insert_one(template)
        msg = "������� ���� � ���� ����"
        bot.send_message(user_id, text=msg)

    # ��������� �� ��
    elif re.match(r"[��]����� ����\b", message.text):
        # ������������ �������
        if not user:
            msg = "���� � ��� �� ���� � ���� ����"
            bot.send_message(user_id, text=msg)
            return

        db.users.delete_one({'user_id': user_id})
        msg = "������ ���� �� ����� ����"
        bot.send_message(user_id, text=msg)

    # ������� ���������
    elif re.match(create_template, message.text):
        # ������������ �������
        if not check_user_in_bd(user, user_id):
            return

        category = message.text.split(' ', 1)[1]

        # ������������ �������
        if category in user['categories']:
            msg = f"��������� {category} ��� ����������"
            bot.send_message(user_id, text=msg)
            return

        template = {'items': [],
                    'planned_items': []}
        db.users.update_one({'user_id': user_id}, {'$set': {f'categories.{category}': template}})
        msg = f"������ ����� ��������� \"{category}\""
        bot.send_message(user_id, text=msg)

    # ������� ���������
    elif re.match(delete_template, message.text):
        # ������������ �������
        if not check_user_in_bd(user, user_id):
            return

        category = message.text.split(' ', 1)[1]

        # ������������ �������
        if not (category in user['categories']):
            msg = f"��������� \"{category}\" �� ����������"
            bot.send_message(user_id, text=msg)
            return

        user['categories'].pop(category)
        db.users.update_one({'user_id': user_id}, {'$set': {'categories': user['categories']}})
        msg = f"������ ��������� \"{category}\""
        bot.send_message(user_id, text=msg)

    # ������ ���������
    elif re.match(r"[��]��������\b", message.text):
        # ������������ �������
        if not check_user_in_bd(user, user_id):
            return

        # ������������ �������
        if not user['categories']:
            msg = "�� ��� �� ������ �� ����� ���������. " \
                  "����� ������� ���������, ��������� ������� \"������ *��� ���������*\". " \
                  "��������: ������ ���� � �����������"
            bot.send_message(user_id, text=msg)
            return

        keyboard = types.InlineKeyboardMarkup()
        for category in user['categories']:
            key = types.InlineKeyboardButton(text=category, callback_data=f"cat {category}")
            keyboard.add(key)
        msg = "��� ������ ���� ����� ���������. ����� �� ��������� ����� ������ � ��� ������"
        bot.send_message(user_id, text=msg, reply_markup=keyboard)

    # ������ �������
    elif re.match(earn_template, message.text):
        # ������������ �������
        if not check_user_in_bd(user, user_id):
            return

        value = int(message.text.split(' ', 1)[1])
        user, msg = update_budget(user_id, value)
        bot.send_message(user_id, text=msg)
        bot.send_message(user_id, text=budget_message(user['budget']))

    # �������� ������
    elif re.match(r'[��]�����$', message.text):
        # ������������ �������
        if not check_user_in_bd(user, user_id):
            return

        bot.send_message(user_id, text=budget_message(user['budget']))

    # �������� ��������������� ������
    elif re.match(r'[��]����� ����', message.text):
        # ������������ �������
        if not check_user_in_bd(user, user_id):
            return

        bot.send_message(user_id, text=planned_budget_message(user['planned_budget']))

    # ������ ������� � ��������� ��� �����������
    elif re.match(buy_template, message.text) or re.match(plan_template, message.text):
        # ������������ �������
        if not check_user_in_bd(user, user_id):
            return
        if not user['categories']:
            msg = "�� ��� �� ������ �� ����� ���������, ����� ��������� ���� �������. " \
                  "����� ������� ���������, ��������� ������� \"������ *��� ���������*\". " \
                  "��������: ������ ���� � �����������"
            bot.send_message(user_id, text=msg)
            return

        keyboard = types.InlineKeyboardMarkup()
        for category in user['categories']:
            key = types.InlineKeyboardButton(text=category, callback_data=f"{message.text}:{category}")
            keyboard.add(key)
        msg = "� ����� ��������� �� ������ ������� ��� �������?"
        bot.send_message(user_id, text=msg, reply_markup=keyboard)

    # ���������� ��������������� � ���������
    elif re.match(plan_category_template, message.text):
        category = message.text.split(' ', 1)[1]

        # ������������ �������
        if not (category in user['categories']):
            msg = f"��������� {category} �� ����������. ������ �� � ������� ������� \"������ {category}\""
            bot.send_message(user_id, text=msg)
            return

        msg = f"������������� ������� � ��������� {category}:\n\n"
        items = user['categories'][category]['planned_items']
        text, summ = generate_item_list(items, write_date=False)
        msg += text
        bot.send_message(user_id, msg)
        msg = f"����� ����������� ��������� {summ} ���."
        bot.send_message(user_id, msg)

    else:
        bot.send_message(user_id, "� ���� �� �������. ������ \"������\".")

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

    # �������� (� ����������� �� ��� ������)
    if call.data == "greeting":
        msg = "������������!"
        bot.send_message(user_id, msg)

    # ���������� � ���������, ��������� ���� �� ������ ����� ������� "���������"
    elif re.match(r"cat .+", call.data):
        category = call.data.split(' ', 1)[1]
        msg = f"������� � ��������� {category} �� ��� �����:\n\n"
        text, summ = generate_item_list(user['categories'][category]['items'])
        msg += text
        bot.send_message(user_id, msg)
        msg = f"����� �� ��� ����� ��������� {summ} ���."
        bot.send_message(user_id, msg)

        msg = "������������� �������:\n\n"
        text, summ = generate_item_list(user['categories'][category]['planned_items'], write_date=False)
        msg += text
        bot.send_message(user_id, msg)
        msg = f"����� ����������� ��������� {summ} ���."
        bot.send_message(user_id, msg)

    # ������ ������� � ��������� ��� ���������������
    elif re.match(buy_template, call.data) or re.match(plan_template, call.data):
        info = call.data.split(':', 1)
        category = info[1]
        command = re.match(buy_template, info[0])
        if command:
            value = - int(command[2]) * int(command[3])
            user, msg = update_budget(user_id, value)
            template = buy_template
            path = "items"
            word = "���������"
        else:
            command = re.match(plan_template, info[0])
            value = int(command[2]) * int(command[3])
            user = update_planned_budget(user_id, value)
            template = plan_template
            path = "planned_items"
            word = "���������������"
        item, value, count = re.findall(template, info[0])[0]
        new_position = {'date': str(date.today()),
                    'item': item,
                    'value': value,
                    'count': count}
        db.users.update_one({'user_id': user_id}, {'$push': {f"categories.{category}.{path}": new_position}})

        msg = f"������� ����� ������� \"{item}\" ���������� {value} � ���������� {count} � {word} � ��������� {category}"
        bot.send_message(user_id, msg)
        bot.send_message(user_id, text=budget_message(user['budget']))
        bot.send_message(user_id, text=planned_budget_message(user['planned_budget']))

    log = "    answered successfully at " + str(datetime.now()) + "\n"
    file.write(log)
    file.close()


bot.polling(none_stop=True, interval=0)
