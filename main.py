import json
from threading import Thread
import time
from time import sleep
from typing import Optional

import pandas as pd
import sqlite3

import telebot
from dotenv import load_dotenv
import os


def write_personal_setting(username, setting_name, value):
    personal_settings = get_personal_settings_dictionary()
    if username not in personal_settings:
        personal_settings[username] = {'notifications': False}
    personal_settings[username][setting_name] = value
    with open('personal_settings.json', 'w') as f:
        json.dump(personal_settings, f)
        f.close()


def get_personal_settings_dictionary():
    f = open('personal_settings.json')
    # returns JSON object as
    # a dictionary
    personal_settings = json.load(f)
    # Closing file
    f.close()
    return personal_settings


def get_usernames_string_for_notifications():
    usernames = ''
    personal_settings = get_personal_settings_dictionary()
    for i in personal_settings:
        if personal_settings[i]["notifications"]:
            usernames += ' @' + str(i)
    return usernames


def send_text(text, disable_notification: Optional[bool] = True):
    bot.send_message(tg_chat_id, text, parse_mode="HTML", disable_notification=disable_notification)


def find_viber_chat_id(chat_token):
    for i in range(len(chat_info_db.Token)):
        if chat_info_db.Token[i] == chat_token:
            viber_chat_id = chat_info_db.ChatID[i]
            print("chat found. id =", viber_chat_id, "token =", viber_chat_token)
            chat_name = chat_info_db.Name[i]
            if chat_name is not None:
                send_text("<b>" + chat_name + "</b>")
            return viber_chat_id
    print("Can't find chat id by token", chat_token)


load_dotenv()

tg_chat_id = os.getenv("TG_CHAT_ID")
db_path = str(os.getenv("PATH_TO_DB"))
viber_chat_token = str(os.getenv("VIBER_CHAT_TOKEN"))

bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

file = open("last_time", "r")
last_sent_time = int(file.read())
send_text("<b>Starting...</b>")
send_text("looking for messages after " +
          time.strftime("%a, %d %b %Y %H:%M:%S",
                        time.localtime(last_sent_time / 1000)))
file.close()

last_new_messages_check_time = 0

'''@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    if message.text == "/status":
        bot.send_message(message.chat.id, "нет.")
    print("answer sent")
bot.polling(none_stop=True, interval=0)
'''


class CmdListener(Thread):
    def run(self):
        @bot.message_handler(content_types=['text'])
        def get_text_messages(message):
            if (message.text == "/status") | (message.text == "/status@" + bot.get_me().username):
                bot.send_message(message.chat.id, "last check was on " + time.strftime("%a, %d %b %Y %H:%M:%S",
                                                                                       time.localtime(
                                                                                           last_new_messages_check_time)))

            elif (message.text == "/testnotification") | (message.text == "/testnotification@" + bot.get_me().username):
                send_text(get_usernames_string_for_notifications())
            elif (message.text == "/notifications") | (message.text == "/notifications@" + bot.get_me().username):
                username = message.from_user.username
                personal_settings = get_personal_settings_dictionary()
                if username not in personal_settings:
                    personal_settings[username] = {'notifications': False}
                if personal_settings[username]["notifications"]:
                    # if command called when already enabled, turn it off
                    write_personal_setting(message.from_user.username, "notifications", False)
                    send_text("you will <b>not</b> receive @ notifications")
                else:
                    write_personal_setting(message.from_user.username, "notifications", True)
                    send_text("you <b>will</b> receive @ notifications")

        bot.polling(none_stop=True, interval=0)


cmd_listener = CmdListener()
cmd_listener.start()


class Selftest(Thread):
    def run(self):
        send_text("bg self-test started")
        while True:
            sleep(60)
            if time.time() - last_new_messages_check_time > 120:
                send_text("<b>seems like the bridge stopped working! last checked new messages on " +
                          time.strftime("%a, %d %b %Y %H:%M:%S",
                                        time.localtime(last_new_messages_check_time)) + " " + os.getenv(
                    "ADMIN_USERNAME") + "</b>")


t2 = Selftest()
t2.start()

print("command listener started")

viber_db_connection = sqlite3.connect(db_path)

chat_info_db = pd.read_sql_query("SELECT * from ChatInfo", viber_db_connection)
viber_chat_id = find_viber_chat_id(viber_chat_token)
send_text("<b>bot started</b>")
while True:
    viber_db_connection = sqlite3.connect(db_path)
    messages_info_db = pd.read_sql_query("SELECT * from MessageInfo", viber_db_connection)
    contact_db = pd.read_sql_query("SELECT * from Contact", viber_db_connection)
    for iteration in range(len(messages_info_db.ChatID)):
        if messages_info_db.ChatID[iteration] == viber_chat_id:
            if last_sent_time < messages_info_db.TimeStamp[iteration]:
                message_type = messages_info_db.MessageType[iteration]
                last_sent_time = messages_info_db.TimeStamp[iteration]
                contact_id = int(messages_info_db.ContactID[iteration])
                contact_name = 'who'
                for j in range(len(contact_db)):
                    if contact_db.ContactID[j] == contact_id:
                        contact_name = contact_db.ClientName[j]
                message_text = "<b>" + contact_name + ":</b>\n"
                if messages_info_db.Body[iteration] is not None:
                    message_text += messages_info_db.Body[iteration]
                if contact_id == 2:
                    message_text += "\n" + get_usernames_string_for_notifications()
                if message_type == 1:
                    if message_text is not None:
                        send_text(message_text)
                elif message_type == 2:
                    '''
                    print(df3.PayloadPath[iteration])
                    while df3.PayloadPath[iteration] is None:
                        print("test")
                        sleep(1)
                    '''
                    path = messages_info_db.PayloadPath[iteration]
                    if path is not None:
                        photo1 = open(path, 'rb')
                        if message_text is not None:
                            bot.send_photo(tg_chat_id, photo1, message_text)
                        else:
                            bot.send_photo(tg_chat_id, photo1)
                    else:
                        send_text("loading picture from " + contact_name + "...")
                        last_sent_time -= 1
                file = open("last_time", "w")
                file.write(str(last_sent_time))
                file.close()
                sleep(2)
            last_new_messages_check_time = time.time()

    viber_db_connection.close()
    sleep(30)
