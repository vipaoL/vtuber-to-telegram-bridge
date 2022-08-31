from threading import Thread
from time import sleep
import pandas as pd
import sqlite3

import telebot
from dotenv import load_dotenv
import os


def send_text(text):
    bot.send_message(tg_chat_id, text, parse_mode="HTML")


load_dotenv()

tg_chat_id = os.getenv("TG_CHAT_ID")
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))
send_text("token loaded")

file = open("last_time", "r")

last_sent_time = int(file.read())
send_text("looking for messages after " + str(last_sent_time))
file.close()

db_path = str(os.getenv("PATH_TO_DB"))
viber_chat_token = str(os.getenv("VIBER_CHAT_TOKEN"))

'''@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    if message.text == "/status":
        bot.send_message(message.chat.id, "нет.")
    print("answer sent")
bot.polling(none_stop=True, interval=0)

class Thread1(Thread):
    def run(self):
        @bot.message_handler(content_types=['text'])
        def get_text_messages(message):
            if message.text == "/status":
                bot.send_message(message.chat.id, "нет.")
        bot.polling(none_stop=True, interval=0)

t1 = Thread1()
t1.start()

print("polling started")
'''
send_text("bot started")
while True:
    con = sqlite3.connect(db_path)
    df3 = pd.read_sql_query("SELECT * from MessageInfo", con)
    df4 = pd.read_sql_query("SELECT * from ChatInfo", con)
    contact = pd.read_sql_query("SELECT * from Contact", con)
    for i in range(len(df4.Token)):
        if df4.Token[i] == viber_chat_token:
            chatId = df4.ChatID[i]
            for iteration in range(len(df3.ChatID)):
                if df3.ChatID[iteration] == chatId:
                    if last_sent_time < df3.TimeStamp[iteration]:
                        m_type = df3.MessageType[iteration]
                        last_sent_time = df3.TimeStamp[iteration]
                        print(last_sent_time)
                        contact_id = int(df3.ContactID[iteration])
                        contact_name = 'who'
                        for j in range(len(contact)):
                            id = contact.ContactID[j]
                            if id == contact_id:
                                contact_name = contact.ClientName[j]
                        message_text = "<b>" + contact_name + ":</b>\n"
                        if df3.Body[iteration] is not None:
                            message_text += df3.Body[iteration]
                        if m_type == 1:
                            if message_text is not None:
                                send_text(message_text)
                        elif m_type == 2:
                            '''
                            print(df3.PayloadPath[iteration])
                            while df3.PayloadPath[iteration] is None:
                                print("test")
                                sleep(1)
                            '''
                            path = df3.PayloadPath[iteration]
                            if path is not None:
                                photo1 = open(path, 'rb')
                                if message_text is not None:
                                    bot.send_photo(tg_chat_id, photo1, message_text)
                                else:
                                    bot.send_photo(tg_chat_id, photo1)
                            else:
                                send_text("loading picture from " + contact_name + "...")
                                last_sent_time -= 1
                        if contact_id == 2:
                            send_text("@vipaoL @vapoltavecs")
                        file = open("last_time", "w")
                        file.write(str(last_sent_time))
                        file.close()
                        sleep(2)

    con.close()
    sleep(30)
