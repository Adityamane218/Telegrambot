import logging
import sqlite3
import time
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ================= RENDER DUMMY SERVER =================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully on Render!")

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

# ================= CONFIG =================
BOT_TOKEN = "8673131026:AAH_c0-NY-J6yVOM3K4_ILiUu6XfbqjDZtM"   # 🔴 CHANGE THIS
ADMIN_ID = 8316067434                # 🔴 CHANGE THIS (your Telegram ID)

# ==========================================

logging.basicConfig(level=logging.INFO)

# ================= DATABASE =================
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    status TEXT DEFAULT 'new',
    is_paid INTEGER DEFAULT 0,
    join_date INTEGER,
    last_action INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")
conn.commit()

# ================= SET LINK =================
async def set_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Use: /setlink https://t.me/yourchannel")
        return

    new_link = context.args[0]
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('channel_link', ?)", (new_link,))
    conn.commit()

    await update.message.reply_text(f"✅ Link Updated: {new_link}")

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, ?)",
                   (user_id, int(time.time())))
    conn.commit()

    keyboard = [
        [InlineKeyboardButton("BUY PREMIUM 💎", callback_data="buy")],
        [InlineKeyboardButton("PROOFS 📁", callback_data="proofs")]
    ]

    await update.message.reply_text(
        "Welcome! Click below:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BUTTON =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "buy":
        await query.message.edit_text(
            "Pay ₹199 and send screenshot",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("I PAID", callback_data="paid")]
            ])
        )

    elif query.data == "proofs":
        await query.message.edit_text("Proof channel:\nhttps://t.me/+p-B5NceERVhmYjM9")  # 🔴 CHANGE THIS

    elif query.data == "paid":
        await query.message.edit_text("Send screenshot now")

    # ================= APPROVE FIXED =================
    elif query.data.startswith("approve_"):
        user_id = int(query.data.split("_")[1])

        # ✅ GET LINK FROM DATABASE
        cursor.execute("SELECT value FROM settings WHERE key='channel_link'")
        result = cursor.fetchone()

        if not result:
            await query.message.reply_text("⚠️ Set link first using /setlink")
            return

        channel_link = result[0]

        cursor.execute("UPDATE users SET status='paid', is_paid=1 WHERE user_id=?", (user_id,))
        conn.commit()

        await context.bot.send_message(user_id, f"✅ Approved!\nJoin:\n{channel_link}")
        await query.message.edit_text("Approved")

    elif query.data.startswith("reject_"):
        user_id = int(query.data.split("_")[1])

        await context.bot.send_message(user_id, "❌ Payment rejected")
        await query.message.edit_text("Rejected")

# ================= SCREENSHOT =================
async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if update.message.photo:
        photo = update.message.photo[-1].file_id

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Approve", callback_data=f"approve_{user.id}"),
                InlineKeyboardButton("Reject", callback_data=f"reject_{user.id}")
            ]
        ])

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo,
            caption=f"User: {user.id}",
            reply_markup=keyboard
        )

        await update.message.reply_text("Sent for review")

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    total = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    await update.message.reply_text(f"Users: {total}")

# ================= MAIN =================
def main():
    threading.Thread(target=keep_alive, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("setlink", set_link))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, screenshot))

    print("Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
