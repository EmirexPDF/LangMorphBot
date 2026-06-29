import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from googletrans import Translator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize translator
translator = Translator()

# Bot token from environment variable
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

# Port for webhook (Railway uses PORT env variable)
PORT = int(os.environ.get("PORT", 8080))

# Dictionary to store user language preferences
user_languages = {}

# Supported languages
LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh-cn': 'Chinese (Simplified)',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'id': 'Indonesian',
    'ms': 'Malay',
    'th': 'Thai',
    'vi': 'Vietnamese',
    'sw': 'Swahili',
    'ha': 'Hausa',
    'yo': 'Yoruba',
    'ig': 'Igbo'
}

# ============ COMMAND HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when /start is issued."""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🌐 Set Language", callback_data="set_language")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Hello {user.first_name}!\n\n"
        f"I'm a translation bot. Send me any text and I'll translate it for you!\n\n"
        f"📝 **Commands:**\n"
        f"/start - Show this menu\n"
        f"/help - Get help\n"
        f"/languages - List supported languages\n"
        f"/setlang - Set your preferred language\n"
        f"/translate <text> - Translate specific text\n"
        f"/about - About this bot\n\n"
        f"🌍 Default translation: English\n"
        f"Use the button below to set your language!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message."""
    await update.message.reply_text(
        "🤖 **How to use this bot:**\n\n"
        "1️⃣ Send me any text message\n"
        "2️⃣ I'll auto-detect and translate to your preferred language\n"
        "3️⃣ Use /setlang to change your target language\n"
        "4️⃣ Use /translate <text> for specific translations\n\n"
        "🌐 **Supported Languages:** 20+ languages\n"
        "📌 **Default:** English\n\n"
        "🔧 **Commands:**\n"
        "/start - Main menu\n"
        "/help - This help message\n"
        "/languages - List all supported languages\n"
        "/setlang - Change your translation target language\n"
        "/translate <text> - Translate specific text\n"
        "/about - About this bot",
        parse_mode='Markdown'
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send about information."""
    await update.message.reply_text(
        "🌍 **Translation Bot v2.0**\n\n"
        "Built with:\n"
        "🤖 python-telegram-bot v21.1.1\n"
        "🌐 googletrans v4.0.0\n"
        "🚀 Deployed on Railway\n\n"
        "Features:\n"
        "✅ Auto-detect source language\n"
        "✅ Translate to 20+ languages\n"
        "✅ Language preferences saved per user\n"
        "✅ Fast and reliable\n\n"
        "📌 **Note:** Free Google Translate API - may have limits",
        parse_mode='Markdown'
    )

async def show_languages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all supported languages."""
    lang_list = "\n".join([f"• {code}: {name}" for code, name in LANGUAGES.items()])
    
    # Paginate if too long (Telegram has message limits)
    if len(lang_list) > 4000:
        chunks = [lang_list[i:i+4000] for i in range(0, len(lang_list), 4000)]
        for chunk in chunks:
            await update.message.reply_text(
                f"🌐 **Supported Languages:**\n\n{chunk}",
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(
            f"🌐 **Supported Languages:**\n\n{lang_list}",
            parse_mode='Markdown'
        )

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set user's preferred target language."""
    keyboard = []
    row = []
    for code, name in list(LANGUAGES.items())[:10]:  # Show first 10 for clean display
        row.append(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Add option to see more languages
    keyboard.append([InlineKeyboardButton("📋 Show All Languages", callback_data="show_all_langs")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌍 **Choose your preferred translation language:**\n\n"
        "Your messages will be translated to this language.\n"
        "Select from the options below 👇",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Translate a specific text."""
    if not context.args:
        await update.message.reply_text(
            "❌ **Usage:** /translate <text to translate>\n\n"
            "Example: /translate Hello, how are you?",
            parse_mode='Markdown'
        )
        return
    
    text = " ".join(context.args)
    user_id = str(update.effective_user.id)
    target_lang = user_languages.get(user_id, 'en')
    
    try:
        result = translator.translate(text, dest=target_lang)
        await update.message.reply_text(
            f"🌐 **Translation to {LANGUAGES.get(target_lang, 'English')}:**\n\n"
            f"📝 {result.text}\n\n"
            f"ℹ️ Detected: {LANGUAGES.get(result.src, result.src)}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Translation error: {e}")
        await update.message.reply_text(
            "❌ Translation failed. Please try again later.",
            parse_mode='Markdown'
        )

# ============ CALLBACK HANDLERS ============

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    data = query.data
    
    if data == "set_language":
        # Show language selection
        keyboard = []
        row = []
        for code, name in list(LANGUAGES.items())[:8]:
            row.append(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("📋 Show All Languages", callback_data="show_all_langs")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🌍 **Choose your preferred translation language:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    elif data == "help":
        await query.edit_message_text(
            "🤖 **How to use this bot:**\n\n"
            "1️⃣ Send any text\n"
            "2️⃣ I'll translate it to your preferred language\n"
            "3️⃣ Use /setlang to change target language\n\n"
            "📝 **Commands:**\n"
            "/start - Main menu\n"
            "/help - Help\n"
            "/languages - Supported languages\n"
            "/setlang - Change language\n"
            "/translate <text> - Translate specific text\n"
            "/about - About",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
            ]),
            parse_mode='Markdown'
        )
        
    elif data == "back_to_menu":
        keyboard = [
            [InlineKeyboardButton("🌐 Set Language", callback_data="set_language")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "👋 **Main Menu**\n\nChoose an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    elif data == "show_all_langs":
        lang_list = "\n".join([f"• {code}: {name}" for code, name in LANGUAGES.items()])
        await query.edit_message_text(
            f"🌐 **All Supported Languages:**\n\n{lang_list}\n\n"
            f"To set a language, use /setlang or click the button below:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Set Language", callback_data="set_language")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
            ]),
            parse_mode='Markdown'
        )
        
    elif data.startswith("lang_"):
        lang_code = data.replace("lang_", "")
        if lang_code in LANGUAGES:
            user_languages[user_id] = lang_code
            await query.edit_message_text(
                f"✅ **Language set to {LANGUAGES[lang_code]}!**\n\n"
                f"All future messages will be translated to {LANGUAGES[lang_code]}.\n\n"
                f"Try sending me a message!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
                ]),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "❌ Invalid language selected. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
                ]),
                parse_mode='Markdown'
            )

# ============ MESSAGE HANDLER ============

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages and translate them."""
    if not update.message.text:
        return
    
    # Don't translate commands
    if update.message.text.startswith('/'):
        return
    
    text = update.message.text
    user_id = str(update.effective_user.id)
    target_lang = user_languages.get(user_id, 'en')  # Default to English
    
    try:
        # Try to detect and translate
        result = translator.translate(text, dest=target_lang)
        
        # Only send translation if language is different or translation is different
        if result.src != target_lang or result.text != text:
            await update.message.reply_text(
                f"🌐 **Translation ({LANGUAGES.get(result.src, result.src)} → {LANGUAGES.get(target_lang, target_lang)}):**\n\n"
                f"{result.text}",
                parse_mode='Markdown'
            )
        else:
            # If source and target are same, just show detected language
            await update.message.reply_text(
                f"ℹ️ Detected language: {LANGUAGES.get(result.src, result.src)}\n"
                f"Your target language is the same, no translation needed.",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Translation error: {e}")
        await update.message.reply_text(
            "❌ Could not translate. Please try again later.",
            parse_mode='Markdown'
        )

# ============ ERROR HANDLER ============

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and notify user."""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_user:
        try:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="❌ An error occurred. Please try again later."
            )
        except:
            pass

# ============ MAIN FUNCTION ============

def main() -> None:
    """Start the bot."""
    # Create application
    application = Application.builder().token(TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(CommandHandler("languages", show_languages))
    application.add_handler(CommandHandler("setlang", set_language))
    application.add_handler(CommandHandler("translate", translate_command))

    # Register message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register callback handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # Register error handler
    application.add_error_handler(error_handler)

    # Determine if running on Railway (webhook) or local (polling)
    is_railway = os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_SERVICE_ID")
    
    if is_railway:
        # Webhook mode for Railway
        app_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        if not app_url:
            logger.warning("RAILWAY_PUBLIC_DOMAIN not set, falling back to polling")
            application.run_polling()
        else:
            webhook_url = f"https://{app_url}/webhook"
            logger.info(f"Starting webhook on port {PORT}")
            application.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                url_path=TOKEN,
                webhook_url=webhook_url
            )
    else:
        # Polling mode for local development
        logger.info("Starting bot in polling mode...")
        application.run_polling()

if __name__ == "__main__":
    main()
