from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import os, subprocess, urllib.request, urllib.parse, json

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_KEY = os.environ.get("YOUTUBE_API_KEY")

MAIN_KB = ReplyKeyboardMarkup([
    ["🎵 موسیقی از یوتیوب", "🎬 لینک ویدیو"],
    ["🎙️ متن به ویس", "ℹ️ راهنما"]
], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! 👋\nاز منو انتخاب کن:", reply_markup=MAIN_KB)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 موسیقی: اسم آهنگ\n🎬 لینک: لینک یوتیوب\n🎙️ ویس: متن\nℹ️ راهنما",
        reply_markup=MAIN_KB
    )

async def search_yt(query):
    q = urllib.parse.quote(query)
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={q}&maxResults=1&type=video&key={API_KEY}"
    data = json.loads(urllib.request.urlopen(url).read())
    return data["items"][0]["id"]["videoId"]

async def dl_audio(link, output):
    subprocess.run(["yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0", "-o", output, link], check=True)

async def make_video(audio, video):
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "color=c=black:s=1280x720",
        "-i", audio, "-shortest",
        "-c:v", "libx264", "-c:a", "aac",
        "-pix_fmt", "yuv420p", video
    ], check=True)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "ℹ️ راهنما":
        await help_cmd(update, context)
        return
    if text == "🎵 موسیقی از یوتیوب":
        context.user_data["mode"] = "music"
        await update.message.reply_text("اسم آهنگ رو بنویس:")
        return
    if text == "🎬 لینک ویدیو":
        context.user_data["mode"] = "link"
        await update.message.reply_text("لینک یوتیوب رو بفرست:")
        return
    if text == "🎙️ متن به ویس":
        context.user_data["mode"] = "tts"
        await update.message.reply_text("متنت رو بنویس:")
        return
    mode = context.user_data.get("mode", "")
    msg = await update.message.reply_text("⏳ در حال پردازش...")
    try:
        if mode == "music":
            vid = await search_yt(text)
            await dl_audio(f"https://youtu.be/{vid}", "s.mp3")
            await make_video("s.mp3", "out.mp4")
            await update.message.reply_video(video=open("out.mp4", "rb"))
            os.remove("s.mp3")
            os.remove("out.mp4")
        elif mode == "link":
            await dl_audio(text, "s.mp3")
            await make_video("s.mp3", "out.mp4")
            await update.message.reply_video(video=open("out.mp4", "rb"))
            os.remove("s.mp3")
            os.remove("out.mp4")
        elif mode == "tts":
            with open("t.txt", "w", encoding="utf-8") as f:
                f.write(text)
            subprocess.run([
                "edge-tts", "--voice", "fa-IR-FaridNeural",
                "-f", "t.txt", "--write-media", "voice.mp3"
            ], check=True)
            await update.message.reply_voice(voice=open("voice.mp3", "rb"))
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("📥 دانلودر", callback_data="dl_tts")
            ]])
            await update.message.reply_text("می‌خوای ویدیوش هم بسازم؟", reply_markup=kb)
            os.remove("t.txt")
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ خطا: {e}")
    context.user_data["mode"] = ""

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "dl_tts":
        await query.edit_message_text("⏳ در حال ساخت ویدیو...")
        try:
            await make_video("voice.mp3", "out.mp4")
            await query.message.reply_video(video=open("out.mp4", "rb"))
            os.remove("out.mp4")
            os.remove("voice.mp3")
        except Exception as e:
            await query.message.reply_text(f"❌ خطا: {e}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
app.run_polling()
