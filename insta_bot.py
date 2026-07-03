import os
import re
import glob
import shutil
import logging
import tempfile

import yt_dlp
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# توکن رو از متغیر محیطی می‌خونه (توی Railway باید BOT_TOKEN رو ست کنی)
TOKEN = os.environ["BOT_TOKEN"]

INSTAGRAM_URL_RE = re.compile(r"(https?://(www\.)?instagram\.com/\S+)")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 سلام! لینک پست، ریلز یا IGTV اینستاگرام رو بفرست تا با بالاترین کیفیت برات دانلودش کنم.\n\n"
        "⚠️ فقط محتوای پابلیک (غیرخصوصی) قابل دانلوده."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    match = INSTAGRAM_URL_RE.search(text)

    if not match:
        await update.message.reply_text("❌ لینک معتبر اینستاگرام پیدا نشد. یه لینک درست بفرست.")
        return

    url = match.group(1)
    status_msg = await update.message.reply_text("⏳ در حال دانلود با بالاترین کیفیت...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_VIDEO)

    tmp_dir = tempfile.mkdtemp()
    try:
        outtmpl = os.path.join(tmp_dir, "%(id)s.%(ext)s")

        ydl_opts = {
            "outtmpl": outtmpl,
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = glob.glob(os.path.join(tmp_dir, "*"))
        if not files:
            await status_msg.edit_text("❌ چیزی برای دانلود پیدا نشد. ممکنه پست خصوصی یا حذف‌شده باشه.")
            return

        for f in files:
            ext = f.lower().split(".")[-1]
            if ext in ("mp4", "mov", "mkv"):
                with open(f, "rb") as media:
                    await update.message.reply_video(
                        media, supports_streaming=True, caption="✅ دانلود شد"
                    )
            elif ext in ("jpg", "jpeg", "png", "webp"):
                with open(f, "rb") as media:
                    await update.message.reply_photo(media, caption="✅ دانلود شد")
            else:
                with open(f, "rb") as media:
                    await update.message.reply_document(media)

        await status_msg.delete()

    except yt_dlp.utils.DownloadError as e:
        logger.error("Download error: %s", e)
        await status_msg.edit_text(
            "❌ دانلود ناموفق بود. ممکنه لینک اشتباه باشه، پست خصوصی باشه، یا اینستاگرام موقتاً محدودش کرده باشه."
        )
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        await status_msg.edit_text("❌ خطای غیرمنتظره‌ای رخ داد.")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling update: %s", context.error, exc_info=context.error)


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    print("🚀 بات دانلودر اینستاگرام اجرا شد!")
    app.run_polling()


if __name__ == "__main__":
    main()
