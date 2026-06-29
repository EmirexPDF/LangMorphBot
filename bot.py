import os
import io
import logging
import asyncio
from aiohttp import web
from googletrans import Translator
import speech_recognition as sr
from pydub import AudioSegment
from telegram import Update, InlineQueryResultArticle, InputMessageContent
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    InlineQueryHandler,
    ContextTypes,
    filters,
)

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.getenv("PORT", "10000"))

# Initialize Engines
translator = Translator()
recognizer = sr.Recognizer()

# --- CORE TRANSLATION ENGINE ---

def quick_translate(text: str, target_lang: str = 'en'):
    try:
        result = translator.translate(text, dest=target_lang)
        return result.origin, result.src, result.text
    except Exception as e:
        logger.error(f"Translation crash: {e}")
        return text, "unknown", "Error processing translation thread pipeline."

# --- TELEGRAM BOT LOGIC ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ **Welcome to @LangMorphBot!** ✨\n\n"
        "Send me your media assets or text strings for instant translation:\n"
        "• **Text:** Send any message to auto-detect and translate.\n"
        "• **Voice notes:** Convert audio speech to translated text strings.\n"
        "• **Documents (.txt):** Upload clean text files to translate them.\n"
        "• **Inline Mode:** Type `@LangMorphBot <text>` in any chat window!\n\n"
        "Default target is English (`en`). Change it using: `/lang <target_code>`"
    )

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        target = context.args[0].lower()
        context.user_data['target_lang'] = target
        await update.message.reply_text(f"🎯 Target language set to: `{target}`")
    else:
        await update.message.reply_text("Please provide a language code. Example: `/lang es` or `/lang fr`")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = context.user_data.get('target_lang', 'en')
    _, src, translated = quick_translate(update.message.text, target)
    await update.message.reply_text(
        f"🌐 *Detected:* `{src.upper()}` ➡️ `{target.upper()}`\n\n{translated}",
        parse_mode="Markdown"
    )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = context.user_data.get('target_lang', 'en')
    await update.message.reply_text("🎙️ Processing vocal frequencies... decoding audio stream.")
    
    voice_file = await context.bot.get_file(update.message.voice.file_id)
    ogg_buffer = io.BytesIO()
    await voice_file.download_to_memory(out=ogg_buffer)
    ogg_buffer.seek(0)
    
    try:
        sound = AudioSegment.from_file(ogg_buffer, codec="opus")
        wav_io = io.BytesIO()
        sound.export(wav_io, format="wav")
        wav_io.seek(0)
        
        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source)
            recognized_text = recognizer.recognize_google(audio_data)
            
        _, src, translated = quick_translate(recognized_text, target)
        await update.message.reply_text(
            f"🗣️ *Transcribed:* \"{recognized_text}\"\n\n"
            f"🔀 *Translated:* ({src.upper()} ➡️ {target.upper()})\n\n{translated}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Audio processing crashed: {e}")
        await update.message.reply_text("❌ Could not transcribe audio layers. Verify microphone clarity.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = context.user_data.get('target_lang', 'en')
    doc = update.message.document
    
    if not doc.file_name.endswith('.txt'):
        await update.message.reply_text("⚠️ Please send standard `.txt` files for document parsing routines.")
        return

    await update.message.reply_text("📄 Analyzing file layout matrices...")
    doc_file = await context.bot.get_file(doc.file_id)
    text_io = io.BytesIO()
    await doc_file.download_to_memory(out=text_io)
    
    try:
        raw_text = text_io.getvalue().decode('utf-8')
        paragraphs = raw_text.split('\n')
        translated_paragraphs = []
        
        for para in paragraphs:
            if para.strip():
                _, _, trans_para = quick_translate(para, target)
                translated_paragraphs.append(trans_para)
            else:
                translated_paragraphs.append("")
                
        output_text = "\n".join(translated_paragraphs)
        output_io = io.BytesIO(output_text.encode('utf-8'))
        output_io.name = f"translated_{target}_{doc.file_name}"
        
        await update.message.reply_document(document=output_io, caption=f"✅ File fully translated to: `{target}`")
    except Exception as e:
        logger.error(f"Doc parser failure: {e}")
        await update.message.reply_text("❌ An error corrupted the text stream processing system.")

async def handle_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return

    _, src, translated = quick_translate(query, 'en')
    results = [
        InlineQueryResultArticle(
            id=str(hash(query)),
            title=f"Morph to EN ({src.upper()} ➡️ EN)",
            description=translated,
            input_message_content=InputMessageContent(
                message_text=f"🌐 *LangMorph Engine Result:* \n\n{translated}",
                parse_mode="Markdown"
            )
        )
    ]
    await update.inline_query.answer(results)

# --- ALIVE KEEPER FOR RENDER COMPATIBILITY ---

async def health_check(request):
    return web.Response(text="LangMorphBot is awake and routing.")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

# --- INITIALIZATION ENGINE ---

def main():
    if not TOKEN:
        logger.error("Missing critical assignment value environment variable: TELEGRAM_BOT_TOKEN")
        return

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("lang", change_language))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(InlineQueryHandler(handle_inline))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_web_server())

    logger.info("Polling channels active for @LangMorphBot...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
