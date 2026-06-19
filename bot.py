import os
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from groq import Groq
from payment import create_payment, check_payment_status, SUBSCRIPTION_PLANS
from image_gen import generate_image

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=GROQ_API_KEY)

USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def get_user(user_id: int) -> dict:
    users = load_users()
    return users.get(str(user_id), {})

def update_user(user_id: int, data: dict):
    users = load_users()
    users[str(user_id)] = data
    save_users(users)

def is_subscribed(user_id: int) -> bool:
    user = get_user(user_id)
    if not user:
        return False
    
    subscription = user.get("subscription", {})
    if not subscription:
        return False
    
    end_date = subscription.get("end_date")
    if not end_date:
        return False
    
    return datetime.fromisoformat(end_date) > datetime.now()

STYLE_PROMPT = "You are a professional AI assistant. Answer concisely and clearly. No emojis. No casual language."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        update_user(user_id, {
            "username": update.effective_user.username,
            "first_name": update.effective_user.first_name,
            "created_at": datetime.now().isoformat(),
            "subscription": None
        })
    
    subscribed = is_subscribed(user_id)
    
    if subscribed:
        keyboard = [
            [InlineKeyboardButton("Generate Text", callback_data="text")],
            [InlineKeyboardButton("Generate Image", callback_data="image")],
            [InlineKeyboardButton("My Subscription", callback_data="subscription")],
            [InlineKeyboardButton("Help", callback_data="help")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("View Plans", callback_data="plans")],
            [InlineKeyboardButton("Free Trial", callback_data="trial")],
            [InlineKeyboardButton("Help", callback_data="help")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if subscribed:
        welcome = (
            "Welcome back to GenieAI Bot.\n\n"
            "Your subscription is active.\n\n"
            "Select an option below or simply send me a message."
        )
    else:
        welcome = (
            "Welcome to GenieAI Bot.\n\n"
            "I can help you with:\n"
            "- Text generation (articles, summaries, translations)\n"
            "- Image generation from descriptions\n\n"
            "Start with a free trial or choose a plan."
        )
    
    await update.message.reply_text(welcome, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "How to use GenieAI Bot:\n\n"
        "Text Generation:\n"
        "Send any text prompt - I will generate a response.\n"
        "Examples: 'Write a blog post about AI', 'Summarize this topic'\n\n"
        "Image Generation:\n"
        "Type /image followed by a description.\n"
        "Example: /image A futuristic city at sunset\n\n"
        "Commands:\n"
        "/start - Main menu\n"
        "/help - Show this message\n"
        "/image [description] - Generate an image\n"
        "/subscription - View subscription status"
    )
    await update.message.reply_text(help_text)

async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    plans_text = "Choose a subscription plan:\n\n"
    for plan_id, plan in SUBSCRIPTION_PLANS.items():
        plans_text += (
            f"**{plan['name']}**\n"
            f"Price: {plan['price'] // 100} {plan['currency']}/month\n"
            f"Features: {plan['features']}\n\n"
        )
    
    keyboard = [
        [InlineKeyboardButton("Basic - 500 RUB", callback_data="pay_basic")],
        [InlineKeyboardButton("Pro - 1500 RUB", callback_data="pay_pro")],
        [InlineKeyboardButton("Premium - 3000 RUB", callback_data="pay_premium")],
        [InlineKeyboardButton("Back", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(plans_text, reply_markup=reply_markup, parse_mode="Markdown")

async def start_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    plan_id = query.data.replace("pay_", "")
    user_id = query.from_user.id
    username = query.from_user.username
    
    payment = await create_payment(plan_id, user_id, username)
    
    if payment:
        keyboard = [
            [InlineKeyboardButton("Pay Now", url=payment["confirmation_url"])],
            [InlineKeyboardButton("Check Payment", callback_data=f"check_{payment['payment_id']}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Payment for {SUBSCRIPTION_PLANS[plan_id]['name']}\n\n"
            f"Amount: {SUBSCRIPTION_PLANS[plan_id]['price'] // 100} RUB\n\n"
            "Click 'Pay Now' to complete the payment.",
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text("Error creating payment. Please try again.")

async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    payment_id = query.data.replace("check_", "")
    user_id = query.from_user.id
    
    status = await check_payment_status(payment_id)
    
    if status["paid"]:
        plan_id = status["metadata"].get("plan_id")
        if plan_id:
            end_date = datetime.now() + timedelta(days=30)
            update_user(user_id, {
                **get_user(user_id),
                "subscription": {
                    "plan_id": plan_id,
                    "start_date": datetime.now().isoformat(),
                    "end_date": end_date.isoformat(),
                    "payment_id": payment_id
                }
            })
        
        await query.edit_message_text(
            "Payment successful!\n\n"
            "Your subscription is now active.\n"
            "Type /start to begin using the bot."
        )
    else:
        keyboard = [
            [InlineKeyboardButton("Check Again", callback_data=f"check_{payment_id}")],
            [InlineKeyboardButton("Back", callback_data="plans")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Payment not yet confirmed.\n\n"
            "If you have completed the payment, please wait a moment and check again.",
            reply_markup=reply_markup
        )

async def free_trial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user(user_id)
    
    if user.get("trial_used"):
        await query.edit_message_text(
            "You have already used your free trial.\n\n"
            "Choose a subscription plan to continue."
        )
        return
    
    end_date = datetime.now() + timedelta(days=3)
    update_user(user_id, {
        **user,
        "trial_used": True,
        "subscription": {
            "plan_id": "trial",
            "start_date": datetime.now().isoformat(),
            "end_date": end_date.isoformat()
        }
    })
    
    await query.edit_message_text(
        "Free trial activated!\n\n"
        "You have 3 days of full access.\n"
        "Type /start to begin using the bot."
    )

async def show_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = get_user(user_id)
    subscription = user.get("subscription")
    
    if not subscription:
        await query.edit_message_text("You don't have an active subscription.\n\nType /start to view plans.")
        return
    
    plan_id = subscription.get("plan_id")
    end_date = subscription.get("end_date")
    
    if plan_id == "trial":
        plan_name = "Free Trial"
    else:
        plan = SUBSCRIPTION_PLANS.get(plan_id, {})
        plan_name = plan.get("name", "Unknown")
    
    remaining = datetime.fromisoformat(end_date) - datetime.now()
    days_left = remaining.days
    
    await query.edit_message_text(
        f"Your Subscription:\n\n"
        f"Plan: {plan_name}\n"
        f"End date: {end_date[:10]}\n"
        f"Days remaining: {days_left}"
    )

async def generate_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    if user_message.startswith("/image") or user_message.startswith("/subscription"):
        return
    
    user_id = update.effective_user.id
    if not is_subscribed(user_id):
        keyboard = [
            [InlineKeyboardButton("View Plans", callback_data="plans")],
            [InlineKeyboardButton("Free Trial", callback_data="trial")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "You need an active subscription to use this feature.\n\n"
            "Choose a plan or start a free trial.",
            reply_markup=reply_markup
        )
        return
    
    await update.message.reply_text("Generating response...")
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": STYLE_PROMPT},
                {"role": "user", "content": user_message}
            ],
            model="llama3-8b-8192",
            temperature=0.7,
            max_tokens=1024
        )
        
        response = chat_completion.choices[0].message.content
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Text generation error: {e}")
        await update.message.reply_text("Error generating response. Please try again.")

async def generate_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_subscribed(user_id):
        keyboard = [
            [InlineKeyboardButton("View Plans", callback_data="plans")],
            [InlineKeyboardButton("Free Trial", callback_data="trial")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "You need an active subscription to use this feature.\n\n"
            "Choose a plan or start a free trial.",
            reply_markup=reply_markup
        )
        return
    
    query_text = update.message.text.replace("/image", "").strip()
    
    if not query_text:
        await update.message.reply_text("Please provide a description.\nExample: /image A sunset over mountains")
        return
    
    await update.message.reply_text("Generating image...")
    
    try:
        image_path = generate_image(query_text)
        
        with open(image_path, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=f"Generated: {query_text}")
        
        os.remove(image_path)
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        await update.message.reply_text("Error generating image. Please try again.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "text":
        await query.edit_message_text("Send me any text prompt for generation.")
    elif query.data == "image":
        await query.edit_message_text("Type /image followed by a description.\nExample: /image A futuristic city")
    elif query.data == "help":
        await query.edit_message_text(
            "Text: Send any message\n"
            "Image: /image [description]\n"
            "Commands: /start, /help, /image, /subscription"
        )
    elif query.data == "plans":
        await show_plans(update, context)
    elif query.data.startswith("pay_"):
        await start_payment(update, context)
    elif query.data.startswith("check_"):
        await check_payment(update, context)
    elif query.data == "trial":
        await free_trial(update, context)
    elif query.data == "subscription":
        await show_subscription(update, context)
    elif query.data == "back":
        await start(update, context)

def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN not set")
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("image", generate_image_command))
    app.add_handler(CommandHandler("subscription", lambda u, c: show_subscription(u, c)))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_text))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("GenieAI Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
