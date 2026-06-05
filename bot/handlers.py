import os
import tempfile
import logging
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

from bot.tiktok import is_tiktok_url, download_tiktok_video
from bot.twitter import is_twitter_url, download_twitter_video
from bot.pdf_tools import pdf_to_word, word_to_pdf
from bot.remove_bg import remove_background
from bot.ocr import ocr_image
from bot.dorking import (
    get_dork_list,
    get_category_info,
    format_dork_list,
    format_categories_list,
    DORK_CATEGORIES,
)

logger = logging.getLogger(__name__)

WAITING_PDF, WAITING_DOCX, WAITING_BG, WAITING_OCR = range(4)


def register_handlers(app: Application):
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("pdftoword", start_pdf_to_word),
            CommandHandler("wordtopdf", start_word_to_pdf),
            CommandHandler("removebg", start_remove_bg),
            CommandHandler("ocr", start_ocr),
        ],
        states={
            WAITING_PDF: [MessageHandler(filters.Document.PDF, handle_pdf_document)],
            WAITING_DOCX: [
                MessageHandler(
                    filters.Document.FileExtension("docx"), handle_docx_document
                )
            ],
            WAITING_BG: [
                MessageHandler(
                    filters.PHOTO | filters.Document.IMAGE, handle_image_bg
                )
            ],
            WAITING_OCR: [
                MessageHandler(
                    filters.PHOTO | filters.Document.IMAGE, handle_image_ocr
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(menu_callback))

    for key in DORK_CATEGORIES:
        app.add_handler(CommandHandler(f"dork_{key}", make_dork_handler(key)))

    app.add_handler(CommandHandler("dork", dork_command))
    app.add_handler(CommandHandler("dorking", dork_command))

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )

    app.add_error_handler(error_handler)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "<b>za-bot-teletaks</b>\n\n"
        "Bot multi-fungsi untuk:\n"
        "  - Download video TikTok & Twitter/X\n"
        "  - Konversi PDF ↔ Word\n"
        "  - Remove background gambar\n"
        "  - OCR (ekstrak teks dari gambar)\n"
        "  - Google Dorking\n\n"
        "Kirim /menu untuk melihat semua fitur."
    )
    await update.message.reply_text(welcome, parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await menu_command(update, context)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Download TikTok", callback_data="menu_tiktok")],
        [InlineKeyboardButton("Download Twitter/X", callback_data="menu_twitter")],
        [InlineKeyboardButton("PDF to Word", callback_data="menu_pdftoword")],
        [InlineKeyboardButton("Word to PDF", callback_data="menu_wordtopdf")],
        [InlineKeyboardButton("Remove BG", callback_data="menu_removebg")],
        [InlineKeyboardButton("OCR", callback_data="menu_ocr")],
        [InlineKeyboardButton("Google Dorking", callback_data="menu_dork")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "<b>Menu Fitur:</b>\nPilih fitur di bawah ini:",
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query: CallbackQuery = update.callback_query
    await query.answer()
    action = query.data.replace("menu_", "")
    actions = {
        "tiktok": "Kirim link TikTok, nanti otomatis di-download.",
        "twitter": "Kirim link Twitter/X, nanti otomatis di-download.",
        "pdftoword": "Gunakan /pdftoword lalu kirim file PDF.",
        "wordtopdf": "Gunakan /wordtopdf lalu kirim file .docx.",
        "removebg": "Gunakan /removebg lalu kirim gambar.",
        "ocr": "Gunakan /ocr lalu kirim foto/dokumen.",
        "dork": "Gunakan /dork untuk melihat kategori dorking.",
    }
    msg = actions.get(action, "Fitur tidak ditemukan.")
    await query.edit_message_text(f"<b>{action.upper()}</b>\n\n{msg}", parse_mode="HTML")


async def start_pdf_to_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Kirim file PDF yang ingin dikonversi ke Word."
    )
    return WAITING_PDF


async def start_word_to_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Kirim file Word (.docx) yang ingin dikonversi ke PDF."
    )
    return WAITING_DOCX


async def start_remove_bg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Kirim foto/gambar yang ingin dihapus background-nya."
    )
    return WAITING_BG


async def start_ocr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Kirim foto/gambar/dokumen yang ingin diekstrak teksnya."
    )
    return WAITING_OCR


async def handle_pdf_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Memproses konversi PDF ke Word...")
    try:
        file = await update.message.document.get_file()
        pdf_bytes = await file.download_as_bytearray()
        result = await pdf_to_word(bytes(pdf_bytes))
        if result:
            await update.message.reply_document(
                document=BytesIO(result),
                filename="output.docx",
                caption="Selesai! Berikut file Word-nya.",
            )
        else:
            await msg.edit_text("Gagal mengkonversi PDF. File mungkin terlalu besar.")
    except Exception as e:
        logger.error(f"PDF to Word error: {e}")
        await msg.edit_text(f"Error: {str(e)[:200]}")
    return ConversationHandler.END


async def handle_docx_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Memproses konversi Word ke PDF...")
    try:
        file = await update.message.document.get_file()
        docx_bytes = await file.download_as_bytearray()
        result = await word_to_pdf(bytes(docx_bytes))
        if result:
            await update.message.reply_document(
                document=BytesIO(result),
                filename="output.pdf",
                caption="Selesai! Berikut file PDF-nya.",
            )
        else:
            await msg.edit_text("Gagal mengkonversi Word. File mungkin terlalu besar.")
    except Exception as e:
        logger.error(f"Word to PDF error: {e}")
        await msg.edit_text(f"Error: {str(e)[:200]}")
    return ConversationHandler.END


async def handle_image_bg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Memproses hapus background...")
    try:
        photo = update.message.photo
        document = update.message.document
        if photo:
            file = await photo[-1].get_file()
        elif document:
            file = await document.get_file()
        else:
            await msg.edit_text("Tidak ada gambar yang ditemukan.")
            return ConversationHandler.END

        image_bytes = await file.download_as_bytearray()
        result = await remove_background(bytes(image_bytes))

        if result:
            await update.message.reply_document(
                document=BytesIO(result),
                filename="no_bg.png",
                caption="Background berhasil dihapus!",
            )
        else:
            await msg.edit_text(
                "Gagal menghapus background. "
                "Pastikan REMOVE_BG_API_KEY sudah diisi di .env"
            )
    except Exception as e:
        logger.error(f"Remove BG error: {e}")
        await msg.edit_text(f"Error: {str(e)[:200]}")
    return ConversationHandler.END


async def handle_image_ocr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Memproses OCR...")
    try:
        photo = update.message.photo
        document = update.message.document
        if photo:
            file = await photo[-1].get_file()
        elif document:
            file = await document.get_file()
        else:
            await msg.edit_text("Tidak ada gambar yang ditemukan.")
            return ConversationHandler.END

        image_bytes = await file.download_as_bytearray()
        text = await ocr_image(bytes(image_bytes))

        if text and text.strip():
            await update.message.reply_text(f"<b>Hasil OCR:</b>\n\n{text[:4000]}", parse_mode="HTML")
        else:
            await msg.edit_text(
                "Tidak dapat membaca teks dari gambar. "
                "Pastikan gambar jelas atau OCR_API_KEY sudah diisi."
            )
    except Exception as e:
        logger.error(f"OCR error: {e}")
        await msg.edit_text(f"Error: {str(e)[:200]}")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Dibatalkan.")
    return ConversationHandler.END


async def dork_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            format_categories_list(), parse_mode="HTML", disable_web_page_preview=True
        )
        return

    category = args[0].lower()
    if category == "all":
        dorks = get_dork_list("all")
        msg = "<b>Semua Google Dorks:</b>\n\n"
        for i, dork in enumerate(dorks, 1):
            query = dork.replace(" ", "+")
            url = f"https://www.google.com/search?q={query}"
            msg += f"{i}. <a href='{url}'>{dork}</a>\n"
        await update.message.reply_text(msg[:4096], parse_mode="HTML", disable_web_page_preview=True)
        return

    cat_info = get_category_info(category)
    if not cat_info:
        available = ", ".join(DORK_CATEGORIES.keys())
        await update.message.reply_text(
            f"Kategori '{category}' tidak ditemukan.\n\n"
            f"Kategori tersedia: {available}\n\n"
            f"Gunakan /dork untuk melihat menu."
        )
        return

    dorks = get_dork_list(category)
    msg = format_dork_list(category, dorks)
    await update.message.reply_text(msg[:4096], parse_mode="HTML", disable_web_page_preview=True)


def make_dork_handler(category: str):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        dorks = get_dork_list(category)
        if not dorks:
            await update.message.reply_text(f"Tidak ada dork untuk {category}")
            return
        msg = format_dork_list(category, dorks)
        await update.message.reply_text(msg[:4096], parse_mode="HTML", disable_web_page_preview=True)
    return handler


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if is_tiktok_url(text):
        await download_and_send(update, context, text, "tiktok")
    elif is_twitter_url(text):
        await download_and_send(update, context, text, "twitter")
    else:
        pass


async def download_and_send(
    update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, source: str
):
    msg = await update.message.reply_text(f"Mendownload dari {source}...")
    try:
        if source == "tiktok":
            video_bytes = await download_tiktok_video(url)
        else:
            video_bytes = await download_twitter_video(url)

        if video_bytes:
            await update.message.reply_video(
                video=BytesIO(video_bytes),
                caption=f"✅ Download dari {source} berhasil!",
                supports_streaming=True,
            )
        else:
            await msg.edit_text(
                f"Gagal mendownload video dari {source}. "
                "Mungkin URL tidak valid atau video bersifat private."
            )
    except Exception as e:
        logger.error(f"Download error ({source}): {e}")
        await msg.edit_text(f"Error: {str(e)[:200]}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
