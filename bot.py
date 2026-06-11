import os
import telebot
import threading
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Pulling sensitive tokens cleanly from environment variables
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not API_TOKEN:
    raise ValueError("❌ ERROR: TELEGRAM_BOT_TOKEN is missing from Koyeb Environment variables!")

bot = telebot.TeleBot(API_TOKEN)
WEB_URL = "https://access.stockgamer.id"

# Active monitoring threads state: { chat_id: { "running": True, "email": "...", "password": "..." } }
active_sessions = {}

def send_interceptor_msg(chat_id, message_text):
    try:
        bot.send_message(chat_id, f"📩 **[Vinzy Anti-Code Safe]**\n\n{message_text}", parse_mode="Markdown")
    except Exception as e:
        print(f"Failed to message chat {chat_id}: {e}")

def zimbra_monitor_worker(chat_id, email, password):
    print(f"🎬 Starting background monitor thread for Chat ID: {chat_id}")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 15)
        
        driver.get(WEB_URL)
        user_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        pass_input = driver.find_element(By.NAME, "password")
        login_btn = driver.find_element(By.CSS_SELECTOR, "input.z-submitbutton, input[type='submit']")
        
        user_input.send_keys(email)
        pass_input.send_keys(password)
        login_btn.click()
        
        send_interceptor_msg(chat_id, "✅ **Successfully linked!** Anti-Code protection is now active on your Zimbra mail. Running background scan loops...")
        
        while active_sessions.get(chat_id, {}).get("running", False):
            driver.refresh()
            time.sleep(3)
            
            unread_messages = driver.find_elements(By.CLASS_NAME, "Unread")
            
            if unread_messages:
                for msg in unread_messages:
                    msg.click()
                    time.sleep(1)
                    
                    body_element = wait.until(EC.presence_of_element_located((By.ID, "zv__CONV__body")))
                    email_text = body_element.text
                    
                    send_interceptor_msg(chat_id, f"🚨 **CODE INTERCEPTED!**\n\n```\n{email_text}\n
```\n\n*Mail instantly deleted from inbox and server trash bin.*")
                    
                    delete_btn = driver.find_element(By.ID, "zb__CONV__DELETE")
                    delete_btn.click()
                    time.sleep(0.5)
                    
                    driver.execute_script("ZmMailApp.prototype.emptyTrash();")
                    driver.get(f"{WEB_URL}/?app=mail&folder=Inbox")
            
            time.sleep(2)
            
    except Exception as e:
        print(f"Error in session {chat_id}: {e}")
        send_interceptor_msg(chat_id, "⚠️ **Session Disconnected.** Incorrect password or Zimbra page timed out. Use `/protect` to restart.")
    finally:
        if driver:
            driver.quit()
        if chat_id in active_sessions:
            active_sessions[chat_id]["running"] = False
        print(f"🛑 Stopped thread for Chat ID: {chat_id}")

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "👋 Welcome to **Vinzy Anti-Code Safe Bot**!\n\nProtect your BM MLBB accounts from hackers. Use `/protect` to start guarding your Zimbra mailbox.", parse_mode="Markdown")

@bot.message_handler(commands=['protect'])
def start_protection(message):
    chat_id = message.chat.id
    
    if chat_id in active_sessions and active_sessions[chat_id]["running"]:
        bot.reply_to(message, "❌ You already have an active anti-code monitoring script running!")
        return
        
    msg = bot.reply_to(message, "⚡ Enter your Zimbra Email and Password separated by a space:\nExample: `user@stockgamer.id pass123`", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_credentials)

def process_credentials(message):
    chat_id = message.chat.id
    try:
        text = message.text.strip()
        parts = text.split(" ")
        if len(parts) != 2:
            bot.reply_to(message, "❌ Invalid format. Please run `/protect` and try again using a single space.")
            return
            
        email = parts[0]
        password = parts[1]
        
        active_sessions[chat_id] = {
            "running": True,
            "email": email,
            "password": password
        }
        
        t = threading.Thread(target=zimbra_monitor_worker, args=(chat_id, email, password))
        t.daemon = True
        t.start()
        
        bot.reply_to(message, "⏳ Connecting to `stockgamer.id` mail servers... Please wait.")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error initializing project handler: {e}")

@bot.message_handler(commands=['stop'])
def stop_protection(message):
    chat_id = message.chat.id
    if chat_id in active_sessions and active_sessions[chat_id]["running"]:
        active_sessions[chat_id]["running"] = False
        bot.reply_to(message, "🛑 Stop signal sent. Your private browser monitor is closing down.")
    else:
        bot.reply_to(message, "ℹ️ You don't have any active mail scripts running right now.")

if __name__ == "__main__":
    print("🚀 Vinzy Public Multi-User Anti-Code Safe Bot Started!")
    bot.infinity_polling()
