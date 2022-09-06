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

debug = True


def write_personal_setting(username, setting_name, value):
    personal_settings = get_personal_settings_dictionary()
    if username not in personal_settings:
        personal_settings[username] = {'notifications': False}
    personal_settings[username][setting_name] = value
    with open('personal_settings.json', 'w') as f:
        json.dump(personal_settings, f)
        f.close()


# notifications subscribers
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
            usernames += '@' + str(i) + " "
        usernames.strip()
    usernames = "\n" + usernames
    return usernames


def send_text(text, disable_notification: Optional[bool] = True):
    bot.send_message(tg_chat_id, text, parse_mode="HTML", disable_notification=disable_notification)


# chat_token is unique for each chat and token of a chat will be same for all users
# chat_id is just an index number of the chat in your local database. we need to find it
def find_viber_chat_id(chat_token):
    for i in range(len(chat_info_db.Token)):
        if chat_info_db.Token[i] == chat_token:
            viber_chat_id = chat_info_db.ChatID[i]
            print("viber chat found. id =", viber_chat_id, "token =", viber_chat_token)
            chat_name = chat_info_db.Name[i]
            if chat_name is not None:
                if debug:
                    send_text("| (viber) <b>" + chat_name + "</b>")
            return viber_chat_id
    print("Can't find viber chat id by token", chat_token)


class CmdListener(Thread):
    def run(self):
        @bot.message_handler(content_types=['text'])
        def get_text_messages(message):
            if (message.text == "/status") | (message.text == "/status@" + bot.get_me().username):
                bot.send_message(message.chat.id,
                                 "Last check viber messages was on " + time.strftime("%a, %d %b %Y %H:%M:%S",
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
                    send_text("You will <b>not</b> receive @ notifications")
                else:
                    write_personal_setting(message.from_user.username, "notifications", True)
                    send_text("You <b>will</b> receive @ notifications")
            else:
                print("unknown command:", message.text)

        while True:
            try:
                bot.polling(none_stop=True, interval=0)
            except Exception as e:
                print(f'error with polling on the main bot. restarting\n {e}')
                time.sleep(5)


# will notify(@) the admin if there were no checks for new messages in last 120 seconds
class SelfTest(Thread):
    def run(self):
        if debug:
            send_text("| (viber) Bg self-test started")
        while True:
            sleep(60)
            if time.time() - last_new_messages_check_time > 120:
                if debug:
                    send_text("<b>Seems like the viber bridge stopped working! Last checked for new messages on " +
                              time.strftime("%a, %d %b %Y %H:%M:%S",
                                            time.localtime(last_new_messages_check_time)) + " " + os.getenv(
                        "ADMIN_USERNAME") + "</b>")


# bridge from another telegram group
class TgToTg(Thread):
    def run(self):
        last_message = None
        second_tg_chat_id = os.getenv("2ND_TG_CHAT_ID")
        second_bot = telebot.TeleBot(os.getenv("2ND_BOT_TOKEN"))

        @second_bot.message_handler(content_types=['text', "photo", "audio"])
        def get_text_messages(message):
            # "(tg) Cool Name:
            # "
            name = "(tg) <b>"
            if message.from_user.first_name is not None:
                name += message.from_user.first_name
            if message.from_user.last_name is not None:
                name += " " + message.from_user.last_name
            name += ":</b>"

            if str(message.chat.id).startswith("-100"):
                message_url = "https://t.me/c/" + str(message.chat.id).replace("-100", "") + "/" + str(message.id)
                name = f"<a href=\"{message_url}\">" + name + "</a>"
                print(message_url)

            name += "\n"

            # check the message came from proper chat and user with specified id
            if (message.chat.id == int(second_tg_chat_id)) & (message.from_user.id == int(os.getenv("ID_TO_LISTEN"))):
                if message.content_type == 'text':
                    text = name + message.text
                    if message.from_user.id == int(os.getenv("ID_TO_LISTEN")):
                        text += get_usernames_string_for_notifications()
                    print(text)
                    send_text(text, False)

                elif message.content_type == 'photo':
                    raw = message.photo[2].file_id
                    print("len(message.photo) =", len(message.photo))
                    filename = "tmpfile"
                    file_info = second_bot.get_file(raw)
                    downloaded_file = second_bot.download_file(file_info.file_path)
                    sleep(2)
                    with open(filename, 'wb') as new_file:
                        new_file.write(downloaded_file)
                    img = open(filename, 'rb')
                    text = name
                    if message.caption is not None:
                        text += message.caption
                    if message.from_user.id == int(os.getenv("ID_TO_LISTEN")):
                        text += get_usernames_string_for_notifications()
                    bot.send_photo(tg_chat_id, img, text, parse_mode='HTML')
            else:
                print("ignoring tg message (maybe from another chat or person):", message)
                print("message.chat.id=" + str(message.chat.id), "message.from_user.id=" + str(message.from_user.id))

        while True:
            try:
                second_bot.polling(none_stop=True, interval=0)
            except Exception as e:
                try:
                    text = "error"
                    if last_message is not None:
                        if last_message.content_type == 'text':
                            text = last_message.text
                            text += "\nerror"
                    send_text(text, False)
                except Exception as ex:
                    print('error sending error message')
                    last_message = None
                print(f'error with polling on the second bot. restarting\n {e}')
                time.sleep(5)


load_dotenv()

tg_chat_id = os.getenv("TG_CHAT_ID")
db_path = str(os.getenv("PATH_TO_DB"))
viber_chat_token = str(os.getenv("VIBER_CHAT_TOKEN"))

bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

file = open("last_time", "r")
last_sent_time = int(file.read())
file.close()
if debug:
    send_text("<b>| Starting...</b>")
    send_text("| (viber) Looking for messages after " +
              time.strftime("%a, %d %b %Y %H:%M:%S",
                            time.localtime(last_sent_time / 1000)))

# for self-test
last_new_messages_check_time = 0

cmd_listener = CmdListener()
cmd_listener.start()

self_test = SelfTest()
self_test.start()

tg_to_tg = TgToTg()
tg_to_tg.start()

print("command listener started")

viber_db_connection = sqlite3.connect(db_path)

chat_info_db = pd.read_sql_query("SELECT * from ChatInfo", viber_db_connection)
viber_chat_id = find_viber_chat_id(viber_chat_token)

viber_db_connection.close()

if debug:
    send_text("<b>| Bot started</b>")
# main cycle of checking for new messages in the database
while True:
    viber_db_connection = sqlite3.connect(db_path)
    messages_info_db = pd.read_sql_query("SELECT * from MessageInfo", viber_db_connection)
    contact_db = pd.read_sql_query("SELECT * from Contact", viber_db_connection)
    for iteration in range(len(messages_info_db.ChatID)):
        # check it came from the proper chat
        if messages_info_db.ChatID[iteration] == viber_chat_id:
            # check if it is an old message that we don't need to resend
            if last_sent_time < messages_info_db.TimeStamp[iteration]:
                message_type = messages_info_db.MessageType[iteration]
                last_sent_time = messages_info_db.TimeStamp[iteration]
                contact_id = int(messages_info_db.ContactID[iteration])

                # this string will be kept if no contact will be found by appropriate ContactID
                contact_name = 'Can not find in the Contact database'

                # find name in 'Contact' db
                for j in range(len(contact_db)):
                    if contact_db.ContactID[j] == contact_id:
                        contact_name = contact_db.ClientName[j]
                        break
                message_text = "(viber) <b>" + contact_name + ":</b>\n"

                # append text of the message if text exists
                if messages_info_db.Body[iteration] is not None:
                    message_text += messages_info_db.Body[iteration]

                # if the message sent by predefined important contact, tag all which subscribed to the notifications
                if contact_id == 2:
                    disable_notifications = False
                    message_text += get_usernames_string_for_notifications()
                else:
                    disable_notifications = True

                # 1 = text message, 2 = photo (can be with text)
                if message_type == 1:
                    if message_text is not None:
                        send_text(message_text, disable_notifications)
                elif message_type == 2:
                    # waiting while picture is loading
                    #
                    # note that viber won't load pictures when working in the background.
                    # although sometimes it loads pictures even in the background
                    if messages_info_db.PayloadPath[iteration] is None:
                        send_text("| (viber) Loading picture from " + contact_name + "...")
                    while messages_info_db.PayloadPath[iteration] is None:
                        viber_db_connection.close()
                        viber_db_connection = sqlite3.connect(db_path)
                        messages_info_db = pd.read_sql_query("SELECT * from MessageInfo", viber_db_connection)
                        print("(viber) Loading picture from " + contact_name + "...")
                        sleep(2)

                    picture_path = messages_info_db.PayloadPath[iteration]
                    picture = open(picture_path, 'rb')
                    if message_text is not None:
                        bot.send_photo(tg_chat_id, picture, message_text, parse_mode="HTML")
                    else:
                        bot.send_photo(tg_chat_id, picture)
                file = open("last_time", "w")
                file.write(str(last_sent_time))
                file.close()
                sleep(2)
            last_new_messages_check_time = time.time()

    viber_db_connection.close()
    sleep(30)
