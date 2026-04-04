import logging
import sqlite3
import time
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ================= RENDER DUMMY SERVER =================
# Render Web Service ko ek port chahiye hota hai warna wo "Exited with status 1" deta hai.
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
BOT_TOKEN = "8673131026:AAGtkICvC6szPJwJf2N7AP9aOl-wTe_RSSg"
ADMIN_ID = 8316067434
CHANNEL_ID = -1003781657101

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
conn.commit()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    cursor.execute("""
    INSERT OR IGNORE INTO users (user_id, join_date, status)
    VALUES (?, ?, 'new')
    """, (user_id, int(time.time())))
    conn.commit()

    keyboard = [
        [InlineKeyboardButton("BUY PREMIUM 💎", callback_data="buy")],
        [InlineKeyboardButton("PROOFS 📁💎", callback_data="proofs")],
        [InlineKeyboardButton("CONTACT ADMIN 👤", url="https://t.me/ke_xidn")]
    ]

    caption = """🚀 PREMIUM CONTENT ACCESS

Get instant access to a high-quality private collection curated for premium users.

✔️ Massive updated library  
✔️ High-quality content  
✔️ No ads, no redirects  
✔️ Instant access after payment  
✔️ Lifetime validity  

🔥 New content added regularly  
🔒 Private & secure access  

💰 Price: ₹199  
⏳ Validity: Lifetime  

👉 Pay once and unlock everything instantly.
"""
    # Safe image opening to prevent crash if photo.jpg is missing on Render
    try:
        await update.message.reply_photo(
            photo=open("photo.jpg", "rb"),
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except FileNotFoundError:
        await update.message.reply_text(f"[Image Missing]\n{caption}", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= BUTTON HANDLER =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # BUY
    if query.data == "buy":
        caption = """💎 VIP ACCESS PAYMENT
➖➖➖➖➖➖➖➖➖➖
⚡️ FLASH SALE: Only 2 Spots Left! 🔥
🍑 ONE-TIME PAYMENT: ₹199 ONLY!
🔒 LIFETIME VALIDITY
➖➖➖➖➖➖➖➖➖➖
1️⃣ Scan QR & Pay ₹199
2️⃣ Click 'I HAVE PAID' button below
✅ UPI ID: 9505adity@axl
"""

        keyboard = [
            [InlineKeyboardButton("✅I HAVE PAID (Submit Screenshot)", callback_data="paid")]
        ]

        try:
            await query.message.reply_photo(
                photo=open("qr.jpg", "rb"),
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except FileNotFoundError:
            await query.message.reply_text(f"[QR Code Missing]\n{caption}", reply_markup=InlineKeyboardMarkup(keyboard))


    # PROOFS
    elif query.data == "proofs":
        await query.message.reply_text("📊 Check proofs here:\nhttps://t.me/yourproofchannel")

    # PAID CLICK
    elif query.data == "paid":
        await query.message.reply_text(
            """📸 Send your payment screenshot here for verification.

⚠️ Make sure:
- Screenshot is clear
- Payment amount is visible

⏳ You will be approved within 1–10 minutes"""
        )

    # APPROVE
    elif query.data.startswith("approve_"):
        user_id = int(query.data.split("_")[1])

        invite = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,  # 🔒 only 1 user
            expire_date=int(time.time()) + 1800  # ⏳ expires in 30 min
        )

        cursor.execute("UPDATE users SET is_paid=1, status='paid' WHERE user_id=?", (user_id,))
        conn.commit()

        await context.bot.send_message(
            user_id,
            f"✅ Payment Verified!\n\nJoin here:\n{invite.invite_link}"
        )

        await query.message.edit_text("✅ Approved")

    # REJECT
    elif query.data.startswith("reject_"):
        user_id = int(query.data.split("_")[1])

        cursor.execute("UPDATE users SET status='rejected' WHERE user_id=?", (user_id,))
        conn.commit()

        await context.bot.send_message(user_id, "❌ Payment not verified.")
        await query.message.edit_text("❌ Rejected")

# ================= SCREENSHOT =================
async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if update.message.photo:
        cursor.execute("UPDATE users SET status='pending' WHERE user_id=?", (user.id,))
        conn.commit()

        photo = update.message.photo[-1].file_id

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Approve ✅", callback_data=f"approve_{user.id}"),
                InlineKeyboardButton("Reject ❌", callback_data=f"reject_{user.id}")
            ]
        ])

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo,
            caption=f"💰 Payment Screenshot\nUser ID: {user.id}",
            reply_markup=keyboard
        )

        await update.message.reply_text("✅ Sent for verification")

# ================= ADMIN PANEL =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    total = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    paid = cursor.execute("SELECT COUNT(*) FROM users WHERE status='paid'").fetchone()[0]
    pending = cursor.execute("SELECT COUNT(*) FROM users WHERE status='pending'").fetchone()[0]

    await update.message.reply_text(
        f"📊 ADMIN PANEL\n\nUsers: {total}\nPaid: {paid}\nPending: {pending}"
    )

# ================= MAIN =================
def main():
    # Start Dummy Server for Render in background
    threading.Thread(target=keep_alive, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, screenshot))

    print("BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
