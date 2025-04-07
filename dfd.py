import telebot
import sqlite3
from telebot import types

TOKEN = "7918097187:AAGdznSAGXRQMe8KsX0tFljDbIdanAN84YY"
ADMIN_ID = 7006067266
BOT_USERNAME = "rcnfrm_bot"

bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect('bot.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0,
    blocked INTEGER DEFAULT 0,
    referred INTEGER DEFAULT 0
)
""")
conn.commit()

cursor.execute("PRAGMA table_info(users)")
columns = [column[1] for column in cursor.fetchall()]
if 'referral_link' not in columns:
    cursor.execute("ALTER TABLE users ADD COLUMN referral_link TEXT")
    conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS promocodes (
    name TEXT PRIMARY KEY,
    usage_count INTEGER,
    reward REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS promo_usage (
    user_id INTEGER,
    promo_name TEXT,
    PRIMARY KEY (user_id, promo_name)
)
""")
conn.commit()

withdrawal_states = {}

def get_user(user_id, username):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if user is None:
        referral_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        cursor.execute(
            "INSERT INTO users (user_id, username, balance, blocked, referred, referral_link) VALUES (?, ?, 0, 0, 0, ?)",
            (user_id, username, referral_link)
        )
        conn.commit()
        return (user_id, username, 0, 0, 0, referral_link)
    elif user[5] is None:
        referral_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        cursor.execute("UPDATE users SET referral_link=? WHERE user_id=?", (referral_link, user_id))
        conn.commit()
        user = list(user)
        user[5] = referral_link
        return tuple(user)
    return user

def update_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def set_blocked(user_id, blocked):
    cursor.execute("UPDATE users SET blocked = ? WHERE user_id = ?", (1 if blocked else 0, user_id))
    conn.commit()

@bot.message_handler(commands=['start'])
def handle_start(message):
    user = get_user(message.from_user.id, message.from_user.username or message.from_user.first_name)
    if message.text and len(message.text.split()) > 1:
        param = message.text.split()[1]
        try:
            referrer_id = int(param)
            if referrer_id != message.from_user.id and user[4] == 0:
                cursor.execute("UPDATE users SET referred=1 WHERE user_id=?", (message.from_user.id,))
                conn.commit()
                update_balance(referrer_id, 100)
                update_balance(message.from_user.id, 100)
                bot.send_message(message.chat.id, "Вы были приглашены! Вам и пригласившему начислено +100 RCN.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка обработки реферального ID: {e}")
    bot.send_message(message.chat.id, "Привет, список команд можно узнать через /help")

@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = (
        "Список команд для пользователей:\n"
        "/Click – получить +0.5 RCN\n"
        "/Balance – показать баланс\n"
        "/info – информация о боте\n"
        "/bonus – ваша реферальная ссылка\n"
        "/promokod <название> – активация промокода\n"
        "/pay <user_id> <сумма> – перевод RCN другому пользователю\n"
        "/akk – информация о вашем аккаунте\n"
        "/vyvod – запрос на вывод средств\n"
        "/"
    )
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['admin'])
def handle_admin(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "У вас нет прав для использования этой команды.")
        return
    admin_text = (
        "Список команд для администратора:\n"
        "/promcreate <название> <количество использований> <награда> – создать промокод\n"
        "/ban <user_id или юзернейм> – блокировка пользователя\n"
        "/banup <user_id> – разблокировка пользователя\n"
        "/listusr – список пользователей"
    )
    bot.send_message(message.chat.id, admin_text)

@bot.message_handler(commands=['Click'])
def handle_click(message):
    user = get_user(message.from_user.id, message.from_user.username or message.from_user.first_name)
    if user[3] == 1:
        bot.send_message(message.chat.id, "Вы заблокированы!")
        return
    update_balance(message.from_user.id, 0.5)
    bot.send_message(message.chat.id, "На ваш баланс начислено +0.5 RCN.")

@bot.message_handler(commands=['Balance'])
def handle_balance(message):
    user = get_user(message.from_user.id, message.from_user.username or message.from_user.first_name)
    if user[3] == 1:
        bot.send_message(message.chat.id, "Вы заблокированы!")
        return
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
    balance = cursor.fetchone()[0]
    bot.send_message(message.chat.id, f"Ваш баланс: {balance} RCN.")

@bot.message_handler(commands=['info'])
def handle_info(message):
    info_text = "Добро пожаловать, в бота @rcnfrm_bot!"
    bot.send_message(message.chat.id, info_text)

@bot.message_handler(commands=['bonus'])
def handle_bonus(message):
    user = get_user(message.from_user.id, message.from_user.username or message.from_user.first_name)
    if user[3] == 1:
        bot.send_message(message.chat.id, "Вы заблокированы!")
        return
    referral_link = f"https://t.me/{BOT_USERNAME}?start={message.from_user.id}"
    text = (
        "Для получения бонуса перешлите реферальную ссылку человеку.\n"
        "Когда он перейдёт по ней, вы получите приз!\n"
        f"Вот ваша реферальная ссылка: {referral_link}"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['promcreate'])
def handle_promcreate(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "У вас нет прав для использования этой команды.")
        return
    try:
        parts = message.text.split()
        if len(parts) != 4:
            bot.send_message(message.chat.id, "Неверный формат команды. Используйте:\n/promcreate <название> <количество использований> <награда в RCN>")
            return
        name = parts[1]
        usage_count = int(parts[2])
        reward = float(parts[3])
        cursor.execute("INSERT OR REPLACE INTO promocodes (name, usage_count, reward) VALUES (?, ?, ?)", (name, usage_count, reward))
        conn.commit()
        bot.send_message(message.chat.id, f"Промокод {name} создан.")
    except Exception as e:
        bot.send_message(message.chat.id, "Ошибка при создании промокода.")

@bot.message_handler(commands=['promokod'])
def handle_promokod(message):
    user = get_user(message.from_user.id, message.from_user.username or message.from_user.first_name)
    if user[3] == 1:
        bot.send_message(message.chat.id, "Вы заблокированы!")
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.send_message(message.chat.id, "Неверный формат команды. Используйте:\n/promokod <название>")
        return
    name = parts[1]
    cursor.execute("SELECT usage_count, reward FROM promocodes WHERE name=?", (name,))
    promo = cursor.fetchone()
    if not promo:
        bot.send_message(message.chat.id, "Такого промокода не существует.")
        return
    cursor.execute("SELECT * FROM promo_usage WHERE user_id=? AND promo_name=?", (message.from_user.id, name))
    if cursor.fetchone():
        bot.send_message(message.chat.id, "Вы уже использовали этот промокод.")
        return
    usage_count, reward = promo
    if usage_count <= 0:
        bot.send_message(message.chat.id, "Лимит использования промокода исчерпан.")
        return
    cursor.execute("UPDATE promocodes SET usage_count = usage_count - 1 WHERE name=?", (name,))
    cursor.execute("INSERT INTO promo_usage (user_id, promo_name) VALUES (?, ?)", (message.from_user.id, name))
    conn.commit()
    update_balance(message.from_user.id, reward)
    bot.send_message(message.chat.id, f"Промокод активирован. Вам начислено {reward} RCN.")

@bot.message_handler(commands=['pay'])
def handle_pay(message):
    user = get_user(message.from_user.id, message.from_user.username or message.from_user.first_name)
    if user[3] == 1:
        bot.send_message(message.chat.id, "Вы заблокированы!")
        return
    parts = message.text.split()
    if len(parts) != 3:
        bot.send_message(message.chat.id, "Неверный формат команды. Используйте:\n/pay <user_id> <сумма>")
        return
    try:
        target_id = int(parts[1])
        amount = float(parts[2])
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
        sender_balance = cursor.fetchone()[0]
        if sender_balance < amount:
            bot.send_message(message.chat.id, "Недостаточно средств для перевода.")
            return
        update_balance(message.from_user.id, -amount)
        update_balance(target_id, amount)
        bot.send_message(message.chat.id, f"Вы успешно перевели {amount} RCN пользователю {target_id}.")
    except Exception:
        bot.send_message(message.chat.id, "Ошибка при выполнении перевода.")

@bot.message_handler(commands=['akk'])
def handle_akk(message):
    user = get_user(message.from_user.id, message.from_user.username or message.from_user.first_name)
    if user[3] == 1:
        bot.send_message(message.chat.id, "Вы заблокированы!")
        return
    info_text = (
        f"Ваш номер: {user[0]}\n"
        f"Ваше имя: {user[1]}\n"
        f"Ваш баланс: {user[2]} RCN."
    )
    bot.send_message(message.chat.id, info_text)

@bot.message_handler(commands=['ban'])
def handle_ban(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "У вас нет прав для использования этой команды.")
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.send_message(message.chat.id, "Неверный формат команды. Используйте:\n/ban <юзернейм или ID>")
        return
    identifier = parts[1]
    try:
        user_id = int(identifier)
    except ValueError:
        cursor.execute("SELECT user_id FROM users WHERE username=?", (identifier,))
        result = cursor.fetchone()
        if result:
            user_id = result[0]
        else:
            bot.send_message(message.chat.id, "Пользователь не найден.")
            return
    set_blocked(user_id, True)
    bot.send_message(message.chat.id, f"Пользователь {user_id} заблокирован.")

@bot.message_handler(commands=['listusr'])
def handle_listusr(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "У вас нет прав для использования этой команды.")
        return
    cursor.execute("SELECT user_id, username, balance FROM users")
    users = cursor.fetchall()
    response = ""
    for u in users:
        response += f"ID: {u[0]} | Имя: {u[1]} | Баланс: {u[2]} RCN;\n"
    bot.send_message(message.chat.id, response if response else "Нет пользователей.")

@bot.message_handler(commands=['vyvod'])
def handle_vyvod(message):
    user = get_user(message.from_user.id, message.from_user.username or message.from_user.first_name)
    if user[3] == 1:
        bot.send_message(message.chat.id, "Вы заблокированы!")
        return
    withdrawal_states[message.chat.id] = {'step': 'ask_nick'}
    bot.send_message(message.chat.id, "Введите ваш ник для вывода:")

@bot.message_handler(func=lambda message: message.chat.id in withdrawal_states)
def process_withdrawal(message):
    state = withdrawal_states.get(message.chat.id)
    if not state:
        return
    user = get_user(message.from_user.id, message.from_user.username or message.from_user.first_name)
    if state['step'] == 'ask_nick':
        state['nick'] = message.text
        state['step'] = 'confirm_nick'
        bot.send_message(message.chat.id, f"Подтвердите ваш ник: {message.text}\nНапишите 'Да' для подтверждения или 'Нет' для отмены.")
    elif state['step'] == 'confirm_nick':
        if message.text.lower() == 'да':
            state['step'] = 'ask_amount'
            bot.send_message(message.chat.id, "Введите сумму для вывода:")
        else:
            bot.send_message(message.chat.id, "Операция отменена.")
            withdrawal_states.pop(message.chat.id, None)
    elif state['step'] == 'ask_amount':
        try:
            amount = float(message.text)
            cursor.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
            balance = cursor.fetchone()[0]
            if balance < amount:
                bot.send_message(message.chat.id, "Недостаточно средств для вывода.")
                withdrawal_states.pop(message.chat.id, None)
            else:
                update_balance(message.from_user.id, -amount)
                bot.send_message(message.chat.id, f"Запрос на вывод {amount} RCN отправлен администратору. Ожидайте на 42 гриф.")
                bot.send_message(ADMIN_ID, f"Пользователь {user[1]} (ID: {user[0]}) запросил вывод {amount} RCN.\nНик для вывода: {state['nick']}")
                withdrawal_states.pop(message.chat.id, None)
        except ValueError:
            bot.send_message(message.chat.id, "Введите корректное число.")

@bot.message_handler(commands=['banup'])
def handle_banup(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "У вас нет прав для использования этой команды.")
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.send_message(message.chat.id, "Неверный формат команды. Используйте:\n/banup <ID_User>")
        return
    try:
        user_id = int(parts[1])
        set_blocked(user_id, False)
        bot.send_message(message.chat.id, f"Пользователь {user_id} разблокирован.")
    except ValueError:
        bot.send_message(message.chat.id, "Неверный ID пользователя.")

bot.polling(none_stop=True)