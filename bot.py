import os
import re
import sys
import time
import hmac
import random
import string
import smtplib
import logging
import threading
from datetime import datetime
from email.mime.text import MIMEText

import telebot
from telebot import types
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# 1. LOGGING & INITIAL SECURITY ASSIGNMENT
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Thread-%(thread)d: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not API_TOKEN:
    logging.critical("Fatal Configuration Missing: TELEGRAM_BOT_TOKEN environment variable not set.")
    raise ValueError("❌ System Environment Variable [TELEGRAM_BOT_TOKEN] Is Undefined!")

bot = telebot.TeleBot(API_TOKEN)
WEB_URL = "https://access.stockgamer.id"

# Multi-account monitoring session state tracking dictionary
# Key architecture uses a compound design pattern: "chat_id-email"
session_lock = threading.Lock()
active_sessions = {}

# ==========================================
# 2. UTILITY HELPER & DEEP ANALYSIS METHODS
# ==========================================
def extract_verification_code(email_body_text):
    """
    Scans raw incoming mail elements using aggressive Regular Expressions 
    to extract 6-digit or 4-digit verification codes cleanly.
    """
    if not email_body_text:
        return None, "Unknown Request Profile"
        
    code_match = re.search(r'\b\d{6}\b', email_body_text)
    if not code_match:
        code_match = re.search(r'\b\d{4}\b', email_body_text)
        
    extracted_code = code_match.group(0) if code_match else None
    
    context = "Account Alteration Request"
    lower_text = email_body_text.lower()
    if "verification" in lower_text:
        context = "New Device Login Verification"
    elif "password" in lower_text:
        context = "Credential / Password Modification Request"
    elif "unbind" in lower_text or "disconnect" in lower_text:
        context = "3rd Party Account Unbind Injection"
        
    return extracted_code, context

def evaluate_mail_routing_gateway(email_address):
    """
    Executes a direct real-time validation query against stockgamer.id incoming mail relay gateways.
    Determines accurately whether routing rules are open (SUBBED) or actively blocked (UNSUBBED/CLONED).
    """
    target_mx_gateway = "mail.stockgamer.id"
    spoofed_sender = f"security-scanner-{random.randint(1000, 9999)}@vinzysecure.me"
    
    logging.info(f"Executing low-level SMTP routing handshake analysis for: {email_address}")
    
    try:
        server = smtplib.SMTP(target_mx_gateway, 25, timeout=7)
        server.ehlo("vinzybot.com")
        server.mail(spoofed_sender)
        
        status_code, server_response_bytes = server.rcpt(email_address)
        server.quit()
        
        server_response = server_response_bytes.decode(errors="ignore")
        logging.info(f"Gateway Handshake Result Code: {status_code} - Response: {server_response}")
        
        if status_code == 250:
            return "SUBBED"
        elif status_code in [550, 554, 501, 551]:
            return "UNSUBBED_OR_CLONED"
        else:
            return "UNDETERMINED"
            
    except Exception as network_error:
        logging.error(f"External SMTP routing execution handshake threw an error: {network_error}")
        return "CONNECTION_FAILURE"

def generate_main_keyboard_menu():
    """
    Generates the high-efficiency 4-button programmatic menu layout interface.
    """
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_protect = types.KeyboardButton("🛡️ Protect Account")
    btn_check = types.KeyboardButton("🔍 Check Status")
    btn_status = types.KeyboardButton("📊 Active Monitors")
    btn_stop = types.KeyboardButton("🛑 Stop Daemon")
    markup.add(btn_protect, btn_check, btn_status, btn_stop)
    return markup

# ==========================================
# 3. BACKGROUND CORE SCRAPING & PURGE DAEMON
# ==========================================
def zimbra_isolated_daemon_worker(chat_id, email, password):
    """
    Dedicated background monitoring thread tracking specific multi-account configurations.
    Polled at ultra-aggressive 0.5-second thresholds with integrated session-drop alarms.
    """
    session_key = f"{chat_id}-{email}"
    logging.info(f"Launching independent headless worker instance for target context: {session_key}")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    
    driver = None
    retry_count = 0
    max_consecutive_retries = 8
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 15)
        
        driver.get(WEB_URL)
        username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        password_field = driver.find_element(By.NAME, "password")
        submit_button = driver.find_element(By.CSS_SELECTOR, "input.z-submitbutton, input[type='submit']")
        
        username_field.send_keys(email)
        password_field.send_keys(password)
        submit_button.click()
        
        time.sleep(4)
        
        if "login" in driver.current_url.lower():
            bot.send_message(chat_id, f"❌ **Authentication Failed for Account:** `{email}`\n\nThe server rejected your credentials or the account was cloned before deployment.")
            with session_lock:
                if session_key in active_sessions:
                    del active_sessions[session_key]
            return

        bot.send_message(
            chat_id, 
            f"🟢 **Vinzy Anti-Code Shield Active**\n\n"
            f"👤 **Target Mailbox:** `{email}`\n"
            f"⚡ **Loop Configuration:** `0.5s Turbo Mode`\n"
            f"🛡️ **Status:** Monitoring layers are active. Your account is isolated.",
            parse_mode="Markdown"
        )
        
        while True:
            with session_lock:
                if session_key not in active_sessions or not active_sessions[session_key]["running"]:
                    break
            
            try:
                current_state_url = driver.current_url.lower()
                if "login" in current_state_url or "err" in current_state_url:
                    raise PermissionError("Authentication cookie dropped by host server")

                driver.refresh()
                time.sleep(0.5)
                
                unread_rows = driver.find_elements(By.CLASS_NAME, "Unread")
                
                if unread_rows:
                    logging.info(f"Intercepted unread transmission payload inside mailbox profile: {email}")
                    
                    for target_row in unread_rows:
                        try:
                            target_row.click()
                            time.sleep(0.5)
                            
                            message_body_container = wait.until(EC.presence_of_element_located((By.ID, "zv__CONV__body")))
                            raw_extracted_text = message_body_container.text
                            
                            secure_code, secure_context = extract_verification_code(raw_extracted_text)
                            
                            with session_lock:
                                if session_key in active_sessions:
                                    active_sessions[session_key]["codes_intercepted"] += 1
                            
                            if secure_code:
                                alert_payload = (
                                    f"🚨 ⚡ **VINZY CODE INTERCEPTED** ⚡ 🚨\n\n"
                                    f"👤 **Target Account:** `{email}`\n"
                                    f"📝 **Context:** `{secure_context}`\n\n"
                                    f"🔑 **EXTRACTED CODE:**\n"
                                    f"```\n{secure_code}\n
```\n\n"
                                    f"🗑️ *Security Action: Email immediately stripped from Inbox and permanently deleted from trash.*"
                                )
                            else:
                                alert_payload = (
                                    f"📩 **NEW INBOUND ZIMBRA TRANSMISSION LOGGED**\n\n"
                                    f"👤 **Target Account:** `{email}`\n"
                                    f"📝 **Log Status:** *System parameters did not match standard digits format. Relaying full content profile:* \n\n"
                                    f"📋 **RAW EMAIL BODY CONTENT:**\n"
                                    f"```\n{raw_extracted_text[:3500]}\n```\n\n"
                                    f"🗑️ *Security Action: Content captured. Email stripped and purged.*"
                                )
                                
                            bot.send_message(chat_id, alert_payload, parse_mode="Markdown")
                            
                            action_delete_button = driver.find_element(By.ID, "zb__CONV__DELETE")
                            action_delete_button.click()
                            time.sleep(0.3)
                            
                            driver.execute_script("if(typeof ZmMailApp !== 'undefined') { ZmMailApp.prototype.emptyTrash(); }")
                            
                            driver.get(f"{WEB_URL}/?app=mail&folder=Inbox")
                            time.sleep(0.5)
                            
                        except Exception as element_error:
                            logging.error(f"Failed to process target sequence layout row: {element_error}")
                            continue
                            
                retry_count = 0
                
            except (PermissionError, Exception) as loop_interruption:
                error_string = str(loop_interruption).lower()
                
                if "cookie" in error_string or "permission" in error_string or "login" in error_string:
                    bot.send_message(
                        chat_id,
                        f"🚨 **CRITICAL ALERT: DETECTION OF MAIL CLONE / SESSION DROP** 🚨\n\n"
                        f"❌ **Mailbox Account:** `{email}`\n"
                        f"⚠️ **Notice:** Your tracking token was dropped by the server infrastructure. The seller or owner has executed a clone command.\n\n"
                        f"🛑 *Shield Shutdown: Monitoring worker loop terminated. Secure your Moonton ID immediately!*",
                        parse_mode="Markdown"
                    )
                    break
                    
                retry_count += 1
                logging.warning(f"Worker tracking fault logged ({retry_count}/{max_consecutive_retries}): {loop_interruption}")
                
                if retry_count >= max_consecutive_retries:
                    bot.send_message(chat_id, f"⚠️ **Network Interruption for `{email}`:** Connection crashed. Attempting hot-reload recovery protocol...")
                    raise loop_interruption
                    
            time.sleep(0.5)
            
    except Exception as execution_crash:
        logging.error(f"Fatal worker breakdown experienced for target {session_key}: {execution_crash}")
        
        with session_lock:
            should_recover = session_key in active_sessions and active_sessions[session_key]["running"]
            
        if should_recover:
            logging.info(f"Triggering programmatic hot-reload thread restart loop sequence for Context: {session_key}")
            time.sleep(4)
            recovery_thread = threading.Thread(target=zimbra_monitor_worker, args=(chat_id, email, password))
            recovery_thread.daemon = True
            recovery_thread.start()
        else:
            bot.send_message(chat_id, f"🛑 **Shield Offline:** Security loop for `{email}` has terminated safely.")
            
    finally:
        if driver:
            try:
                driver.quit()
                logging.info(f"Clean resource collection complete for context: {session_key}")
            except Exception as close_error:
                logging.error(f"Driver resource dump failure: {close_error}")

def zimbra_monitor_worker(chat_id, email, password):
    try:
        zimbra_isolated_daemon_worker(chat_id, email, password)
    except Exception as e:
        logging.critical(f"Uncaught failure state generated inside master worker execution thread: {e}")

# ==========================================
# 4. BOT ROUTING TELEGRAM EVENT HANDLERS
# ==========================================
@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda msg: msg.text == "👋 Start Menu")
def send_welcome_interface(message):
    welcome_text = (
        f"👋 **Welcome to Vinzy Anti-Code Safe System Pro v2.6**\n\n"
        f"Developed specifically for elite security management of BM accounts.\n"
        f"Supports concurrent multi-account background scanning loops running at 0.5s speeds.\n\n"
        f"🛠️ **Quick Action Dashboard Menus Attached Below:**"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=generate_main_keyboard_menu())

@bot.message_handler(commands=['check'])
@bot.message_handler(func=lambda msg: msg.text == "🔍 Check Status")
def handle_status_verification_request(message):
    prompt = bot.send_message(
        message.chat.id, 
        "🔍 **Enter target Zimbra Mailbox to evaluate verification routing status:**\n"
        "Format verification template requires complete domain identifier: `example@stockgamer.id`",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(prompt, execute_live_domain_query)

def execute_live_domain_query(message):
    chat_id = message.chat.id
    target_address = message.text.strip().lower()
    
    if "@stockgamer.id" not in target_address:
        bot.send_message(chat_id, "❌ **Format Refusal:** Target identifier must match the explicit `@stockgamer.id` zone architecture.")
        return
        
    bot.send_message(chat_id, f"📡 **Handshaking with inbound mail relays for `{target_address}`...**", parse_mode="Markdown")
    evaluation_result = evaluate_mail_routing_gateway(target_address)
    
    if evaluation_result == "SUBBED":
        response_payload = (
            f"📊 **Zimbra Domain Routing Status Analysis:**\n\n"
            f"📧 **Mailbox:** `{target_address}`\n"
            f"🟢 **Status:** **SUBBED (Active Delivery Zone)**\n\n"
            f"⚠️ **Security Notice:** Server inbound flow rules are open. All Moonton verification requests will deliver successfully to this address."
        )
    elif evaluation_result == "UNSUBBED_OR_CLONED":
        response_payload = (
            f"📊 **Zimbra Domain Routing Status Analysis:**\n\n"
            f"📧 **Mailbox:** `{target_address}`\n"
            f"🔴 **Status:** **UNSUBBED OR CLONED (Dead Box Zone)**\n\n"
            f"🔒 **Security Notice:** The target server's inbound routing engine threw clear rejection headers. Mail delivery paths are closed. Moonton cannot deliver codes."
        )
    else:
        response_payload = "❌ **Network Interruption:** Connection timeout experienced while performing evaluations. Please attempt again in a few minutes."

    bot.send_message(chat_id, response_payload, parse_mode="Markdown")

@bot.message_handler(commands=['protect'])
@bot.message_handler(func=lambda msg: msg.text == "🛡️ Protect Account")
def deploy_protection_sequence(message):
    prompt = bot.send_message(
        message.chat.id, 
        "⚡ **Enter your account parameters separated by a single space:**\n"
        "Format structure template: `username@stockgamer.id password123`", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(prompt, activate_headless_worker_thread)

def activate_headless_worker_thread(message):
    chat_id = message.chat.id
    try:
        raw_input = message.text.strip()
        parsing_arguments = raw_input.split(" ")
        
        if len(parsing_arguments) != 2:
            bot.reply_to(message, "❌ **Formatting Failure:** Parameters misaligned. Ensure you format your input precisely with a single space separating your account and password.")
            return
            
        extracted_user = parsing_arguments[0].lower()
        extracted_pass = parsing_arguments[1]
        
        if "@stockgamer.id" not in extracted_user:
            bot.reply_to(message, "❌ **Domain Rejection:** This tool only targets `stockgamer.id` backend structures.")
            return
            
        session_key = f"{chat_id}-{extracted_user}"
            
        with session_lock:
            if session_key in active_sessions and active_sessions[session_key]["running"]:
                bot.reply_to(message, f"❌ **Execution Conflict:** A dedicated background daemon is already actively monitoring `{extracted_user}` on your profile.")
                return
                
            active_sessions[session_key] = {
                "running": True,
                "email": extracted_user,
                "password": extracted_pass,
                "started_at": datetime.now(),
                "codes_intercepted": 0
            }
            
        worker_thread = threading.Thread(target=zimbra_monitor_worker, args=(chat_id, extracted_user, extracted_pass))
        worker_thread.daemon = True
        worker_thread.start()
        
        bot.reply_to(message, f"⏳ **Spawning Headless Chromium Isolation Container...** Initializing tracking matrix loops for `{extracted_user}`.")
        
    except Exception as deployment_fault:
        logging.error(f"Failed to process commands setup: {deployment_fault}")
        bot.reply_to(message, f"❌ **System Orchestration Exception Generated:** `{deployment_fault}`")

@bot.message_handler(commands=['status'])
@bot.message_handler(func=lambda msg: msg.text == "📊 Active Monitors")
def show_thread_performance_dashboard(message):
    chat_id = message.chat.id
    active_monitors_found = False
    dashboard_payload = "📊 **Vinzy Anti-Code Active Monitor Profiles:**\n\n"
    
    with session_lock:
        for key, session_data in active_sessions.items():
            if key.startswith(f"{chat_id}-") and session_data["running"]:
                active_monitors_found = True
                running_duration = datetime.now() - session_data["started_at"]
                hours, remainder = divmod(running_duration.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                uptime_string = f"{running_duration.days}d {hours}h {minutes}m {seconds}s"
                
                dashboard_payload += (
                    f"📧 **Account:** `{session_data['email']}`\n"
                    f"⏱️ **Uptime Duration:** `{uptime_string}`\n"
                    f"🚨 **Codes Intercepted & Purged:** `{session_data['codes_intercepted']}`\n"
                    f"────────────────────\n"
                )
                
    if not active_monitors_found:
        bot.reply_to(message, "📊 **System Metrics Dashboard:** You have no background checking threads assigned to your conversation context right now.")
        return
        
    dashboard_payload += "⚙️ *All background containers performing nominally on Koyeb server containers.*"
    bot.reply_to(message, dashboard_payload, parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
@bot.message_handler(func=lambda msg: msg.text == "🛑 Stop Daemon")
def process_termination_sequence(message):
    prompt = bot.send_message(
        message.chat.id, 
        "🛑 **Enter the specific Zimbra address you wish to stop monitoring:**\n"
        "Input template: `example@stockgamer.id` or type `ALL` to terminate every process.",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(prompt, execute_termination_handler)

def execute_termination_handler(message):
    chat_id = message.chat.id
    target_action = message.text.strip().lower()
    terminated_count = 0
    
    with session_lock:
        if target_action == "all":
            for key, session_data in active_sessions.items():
                if key.startswith(f"{chat_id}-") and session_data["running"]:
                    active_sessions[key]["running"] = False
                    terminated_count += 1
        else:
            session_key = f"{chat_id}-{target_action}"
            if session_key in active_sessions and active_sessions[session_key]["running"]:
                active_sessions[session_key]["running"] = False
                terminated_count += 1
                
    if terminated_count > 0:
        bot.reply_to(message, f"🛑 **Termination Directive Issued:** Terminated ({terminated_count}) active scraping threads safely. Reclaiming Koyeb resource containers.")
    else:
        bot.reply_to(message, "⚠️ **Process Match Error:** No active matching mail processes were found linked to your user profile context.")

# ==========================================
# 5. SERVER CONTAINER ENTRY POINT EXECUTION
# ==========================================
if __name__ == "__main__":
    logging.info("Initializing Master Multi-Thread Vinzy Public Security Bot Gateway...")
    bot.infinity_polling()
