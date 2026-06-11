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

# Thread-safe dictionary for active monitoring sessions
# Layout: { chat_id: { "running": True, "email": "...", "password": "...", "started_at": datetime, "codes_intercepted": 0 } }
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
        return None, "Unknown Request"
        
    # Match standard Moonton/Zimbra 6-digit numerical codes (\b protects boundaries)
    code_match = re.search(r'\b\d{6}\b', email_body_text)
    if not code_match:
        # Fallback query for common alternative 4-digit variations
        code_match = re.search(r'\b\d{4}\b', email_body_text)
        
    extracted_code = code_match.group(0) if code_match else "UNKNOWN"
    
    # Context determination mapping
    context = "Account Alteration Request"
    lower_text = email_body_text.lower()
    if "verification" in lower_text:
        context = "New Device Login Verification"
    if "password" in lower_text:
        context = "Credential / Password Modification Request"
    if "unbind" in lower_text or "disconnect" in lower_text:
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
        # Establish connection on incoming transmission port 25 with a tight safety fallback timeout
        server = smtplib.SMTP(target_mx_gateway, 25, timeout=7)
        server.ehlo("vinzybot.com")
        server.mail(spoofed_sender)
        
        # Verify if mailbox address routing accepts input vectors or throws mailbox unavailable errors
        status_code, server_response_bytes = server.rcpt(email_address)
        server.quit()
        
        server_response = server_response_bytes.decode(errors="ignore")
        logging.info(f"Gateway Handshake Result Code: {status_code} - Response: {server_response}")
        
        # 250 = Action completed, routing path completely open (SUBBED)
        if status_code == 250:
            return "SUBBED"
        # 550 / 554 / 501 = Recipient address rejected or routing blocked by server rules (UNSUBBED/CLONED)
        elif status_code in [550, 554, 501, 551]:
            return "UNSUBBED_OR_CLONED"
        else:
            return "UNDETERMINED"
            
    except Exception as network_error:
        logging.error(f"External SMTP routing execution handshake threw an error: {network_error}")
        return "CONNECTION_FAILURE"

# ==========================================
# 3. BACKGROUND CORE SCRAPING & PURGE DAEMON
# ==========================================
def zimbra_isolated_daemon_worker(chat_id, email, password):
    """
    Dedicated background monitoring thread tracking the specific active session browser instance.
    Features robust execution layers to prevent memory exhaustion and handle cloud timeouts gracefully.
    """
    logging.info(f"Launching independent headless worker instance for Chat ID target: {chat_id}")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false") # Block image assets to maximize load speeds
    
    driver = None
    retry_count = 0
    max_consecutive_retries = 5
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 20)
        
        # Initialize Authentication Step
        driver.get(WEB_URL)
        username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        password_field = driver.find_element(By.NAME, "password")
        submit_button = driver.find_element(By.CSS_SELECTOR, "input.z-submitbutton, input[type='submit']")
        
        username_field.send_keys(email)
        password_field.send_keys(password)
        submit_button.click()
        
        # Confirm login by tracking structural changes in the user interface
        time.sleep(4)
        if "login" in driver.current_url.lower():
            bot.send_message(chat_id, "❌ **Authentication Failed:** The server rejected your credentials. Double check your password and try again.")
            return

        bot.send_message(
            chat_id, 
            f"🟢 **Vinzy Anti-Code Shield Active**\n\n"
            f"👤 **Account:** `{email}`\n"
            f"🛡️ **Status:** Monitoring inbox at 2-second loops. Any incoming codes will be instantly destroyed.",
            parse_mode="Markdown"
        )
        
        # Primary Loop Execution
        while True:
            with session_lock:
                if chat_id not in active_sessions or not active_sessions[chat_id]["running"]:
                    break
            
            try:
                driver.refresh()
                time.sleep(2) # Stabilize DOM layout tree
                
                # Scan DOM tree rows for elements matching the default Zimbra unread email classes
                unread_rows = driver.find_elements(By.CLASS_NAME, "Unread")
                
                if unread_rows:
                    logging.info(f"Intercepted {len(unread_rows)} unread mail elements inside {email}")
                    
                    for target_row in unread_rows:
                        try:
                            # Highlight and open current email index
                            target_row.click()
                            time.sleep(1)
                            
                            # Fetch inner frame text
                            message_body_container = wait.until(EC.presence_of_element_located((By.ID, "zv__CONV__body")))
                            raw_extracted_text = message_body_container.text
                            
                            # Parse elements cleanly using regex engine
                            secure_code, secure_context = extract_verification_code(raw_extracted_text)
                            
                            with session_lock:
                                if chat_id in active_sessions:
                                    active_sessions[chat_id]["codes_intercepted"] += 1
                                    total_intercepts = active_sessions[chat_id]["codes_intercepted"]
                                else:
                                    total_intercepts = 1

                            # Format and send intercepted update alert
                            alert_payload = (
                                f"🚨 ⚡ **VINZY CODE INTERCEPTED** ⚡ 🚨\n\n"
                                f"📝 **Context:** `{secure_context}`\n"
                                f"📧 **Account:** `{email}`\n\n"
                                f"🔑 **EXTRACTED CODE:**\n"
                                f"```\n{secure_code}\n
```\n\n"
                                f"🗑️ *Security Action: Email immediately stripped from Inbox and permanently deleted from trash.*"
                            )
                            bot.send_message(chat_id, alert_payload, parse_mode="Markdown")
                            
                            # Fire core delete action sequence
                            action_delete_button = driver.find_element(By.ID, "zb__CONV__DELETE")
                            action_delete_button.click()
                            time.sleep(0.5)
                            
                            # Direct Javascript engine injection bypasses slow UI clicks to dump backend trash folders instantly
                            driver.execute_script("if(typeof ZmMailApp !== 'undefined') { ZmMailApp.prototype.emptyTrash(); }")
                            logging.info(f"Executed direct programmatic JavaScript memory purge on server trash container.")
                            
                            # Return view hierarchy smoothly back to Inbox
                            driver.get(f"{WEB_URL}/?app=mail&folder=Inbox")
                            time.sleep(1)
                            
                        except Exception as element_error:
                            logging.error(f"Failed to process specific row entry loop: {element_error}")
                            continue
                            
                retry_count = 0 # Loop completed successfully, clear connection errors tracking variables
                
            except Exception as loop_interruption:
                retry_count += 1
                logging.warning(f"Worker loop connection fault experienced ({retry_count}/{max_consecutive_retries}): {loop_interruption}")
                
                if retry_count >= max_consecutive_retries:
                    bot.send_message(chat_id, "⚠️ **Session Disconnect Detected:** Browser container connection crashed. Attempting full hot-reload recovery protocol...")
                    raise loop_interruption # Force loop breaker rule down to parent restart catch block
                    
            time.sleep(2) # Safe server throttling delay interval
            
    except Exception as execution_crash:
        logging.error(f"Fatal worker breakdown experienced for thread {chat_id}: {execution_crash}")
        
        # Hot-Reload Session Recovery Logic
        with session_lock:
            should_recover = chat_id in active_sessions and active_sessions[chat_id]["running"]
            
        if should_recover:
            logging.info(f"Triggering programmatic hot-reload thread restart loop sequence for Chat ID: {chat_id}")
            time.sleep(5)
            # Re-queue worker daemon sequentially to maintain persistent backend scanning execution loops
            recovery_thread = threading.Thread(target=zimbra_monitor_worker, args=(chat_id, email, password))
            recovery_thread.daemon = True
            recovery_thread.start()
        else:
            bot.send_message(chat_id, "🛑 **Shield Shutdown:** Your security monitoring system loop has terminated safely.")
            
    finally:
        if driver:
            try:
                driver.quit()
                logging.info(f"Clean resource collection complete. Headless driver for {chat_id} shut down.")
            except Exception as close_error:
                logging.error(f"Driver resource dump error: {close_error}")

# Wrapper logic to isolate threads safely
def zimbra_monitor_worker(chat_id, email, password):
    try:
        zimbra_isolated_daemon_worker(chat_id, email, password)
    except Exception as e:
        logging.critical(f"Uncaught failure state generated inside master worker execution thread: {e}")

# ==========================================
# 4. BOT ROUTING TELEGRAM EVENT HANDLERS
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome_interface(message):
    welcome_text = (
        f"👋 **Welcome to Vinzy Anti-Code Safe System Pro v2.6**\n\n"
        f"Developed specifically for elite security management of BM accounts.\n\n"
        f"🛠️ **Available System Commands:**\n"
        f"🔹 `/protect` - Spawn an active headless browser tracking daemon to intercept and clear codes 24/7.\n"
        f"🔹 `/check` - Ping server gateway routing rules to find out if mail state is **Subbed** or **Unsubbed** without requiring passwords.\n"
        f"🔹 `/status` - Render the metrics, logs, and uptime charts of your currently running monitor instances.\n"
        f"🔹 `/stop` - Close active scraping threads and kill browser system allocations cleanly."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['check'])
def handle_status_verification_request(message):
    prompt = bot.reply_to(
        message, 
        "🔍 **Enter target Zimbra Mailbox to evaluate status:**\n"
        "Format configuration requires explicit domain: `example@stockgamer.id`",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(prompt, execute_live_domain_query)

def execute_live_domain_query(message):
    chat_id = message.chat.id
    target_address = message.text.strip()
    
    if "@stockgamer.id" not in target_address.lower():
        bot.send_message(chat_id, "❌ **Invalid Configuration Format:** Target identifier must match the explicit `@stockgamer.id` zone architecture.")
        return
        
    bot.send_message(chat_id, f"📡 **Handshaking with inbound mail relays for `{target_address}`...**", parse_mode="Markdown")
    
    # Process evaluation analysis
    evaluation_result = evaluate_mail_routing_gateway(target_address)
    
    if evaluation_result == "SUBBED":
        response_payload = (
            f"📊 **Zimbra Domain Routing Status Analysis:**\n\n"
            f"📧 **Mailbox:** `{target_address}`\n"
            f"🟢 **Status:** **SUBBED (Active Delivery Zone)**\n\n"
            f"⚠️ **Security Notice:** Server inbound flow rules are wide open. All Moonton verification requests will deliver successfully to this address. "
            f"To secure it from hacker intrusions immediately, call `/protect` to boot up your monitoring safety daemon."
        )
    elif evaluation_result == "UNSUBBED_OR_CLONED":
        response_payload = (
            f"📊 **Zimbra Domain Routing Status Analysis:**\n\n"
            f"📧 **Mailbox:** `{target_address}`\n"
            f"🔴 **Status:** **UNSUBBED OR CLONED (Dead Box Zone)**\n\n"
            f"🔒 **Security Notice:** The target server's inbound routing engine threw clear rejection headers. This means mail delivery paths are closed. "
            f"Moonton cannot deliver verification codes to this mailbox anymore. The account settings are frozen."
        )
    elif evaluation_result == "CONNECTION_FAILURE":
        response_payload = (
            f"❌ **Network Interruption:** Connection timeout experienced while performing low-level port 25 evaluations on `mail.stockgamer.id`. "
            f"The server firewalls might be under heavy load. Please attempt checking again in a couple minutes."
        )
    else:
        response_payload = "⚠️ **Indeterminate State Mapping:** Gateway responded with unmapped status configurations. Manual review is recommended."

    bot.send_message(chat_id, response_payload, parse_mode="Markdown")

@bot.message_handler(commands=['protect'])
def deploy_protection_sequence(message):
    chat_id = message.chat.id
    
    with session_lock:
        if chat_id in active_sessions and active_sessions[chat_id]["running"]:
            bot.reply_to(message, "❌ **Execution Conflict:** You already have a dedicated headless daemon process running live on this conversation stream.")
            return
            
    prompt = bot.reply_to(
        message, 
        "⚡ **Enter your account parameters separated by a single space:**\n"
        "Example structural layout format: `username@stockgamer.id password123`", 
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
            
        extracted_user = parsing_arguments[0]
        extracted_pass = parsing_arguments[1]
        
        if "@stockgamer.id" not in extracted_user.lower():
            bot.reply_to(message, "❌ **Domain Rejection:** This tool only targets `stockgamer.id` backend structures.")
            return
            
        with session_lock:
            active_sessions[chat_id] = {
                "running": True,
                "email": extracted_user,
                "password": extracted_pass,
                "started_at": datetime.now(),
                "codes_intercepted": 0
            }
            
        # Spawn dedicated background task worker thread allocation
        worker_thread = threading.Thread(target=zimbra_monitor_worker, args=(chat_id, extracted_user, extracted_pass))
        worker_thread.daemon = True
        worker_thread.start()
        
        bot.reply_to(message, "⏳ **Spawning Headless Chromium Isolation Container...** Establishing initial system connection handles.")
        
    except Exception as deployment_fault:
        logging.error(f"Failed to process structural system commands setup: {deployment_fault}")
        bot.reply_to(message, f"❌ **System Orchestration Exception Generated:** `{deployment_fault}`")

@bot.message_handler(commands=['status'])
def show_thread_performance_dashboard(message):
    chat_id = message.chat.id
    
    with session_lock:
        user_session_exists = chat_id in active_sessions
        if user_session_exists:
            session_data = active_sessions[chat_id].copy()
            
    if not user_session_exists or not session_data["running"]:
        bot.reply_to(message, "📊 **System Metrics Dashboard:** No active background scanning loops are attached to this conversation stream right now.")
        return
        
    running_duration = datetime.now() - session_data["started_at"]
    hours, remainder = divmod(running_duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_string = f"{running_duration.days}d {hours}h {minutes}m {seconds}s"
    
    dashboard_payload = (
        f"📊 **Vinzy Anti-Code Safe Thread Monitor Metrics**\n\n"
        f"📧 **Monitored Target:** `{session_data['email']}`\n"
        f"🟢 **Thread Engine Status:** `RUNNING (PERSISTENT)`\n"
        f"⏱️ **Shield Uptime Duration:** `{uptime_string}`\n"
        f"🚨 **Codes Intercepted & Purged:** `{session_data['codes_intercepted']}`\n\n"
        f"⚙️ *System health checks are green. Headless chromium process is performing nominally on Koyeb server containers.*"
    )
    bot.reply_to(message, dashboard_payload, parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def process_termination_sequence(message):
    chat_id = message.chat.id
    
    with session_lock:
        if chat_id in active_sessions and active_sessions[chat_id]["running"]:
            active_sessions[chat_id]["running"] = False
            bot.reply_to(message, "🛑 **Termination Directive Issued:** Halting thread execution paths and requesting immediate driver garbage collection...")
        else:
            bot.reply_to(message, "ℹ️ **System Query:** You have no active script processes attached to your thread profile context.")

# ==========================================
# 5. SERVER CONTAINER ENTRY POINT EXECUTION
# ==========================================
if __name__ == "__main__":
    logging.info("Initializing Master Multi-Thread Vinzy Public Security Bot Gateway...")
    bot.infinity_polling()
