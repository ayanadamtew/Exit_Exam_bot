import logging
import pandas as pd
import io
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# Load environment variables from .env file if present
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Retrieve token from environment variable
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")


# Conversation state
QUIZ_RUNNING = 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Quiz Bot!\n\n"
        "Send me a CSV file with columns:\n"
        "`question, option_a, option_b, option_c, option_d, answer`\n\n"
        "Answer column should be A, B, C, or D.",
        parse_mode="Markdown"
    )

async def handle_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document

    # Validate file type
    if not doc or not doc.file_name or not doc.file_name.endswith(".csv"):
        await update.message.reply_text("❌ Please upload a valid .csv file.")
        return

    await update.message.reply_text("⏳ Processing your CSV...")

    # Download and parse the file
    file = await doc.get_file()
    file_bytes = await file.download_as_bytearray()
    
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
        df.columns = df.columns.str.strip().str.lower()

        required_cols = {"question", "option_a", "option_b", "option_c", "option_d", "answer"}
        if not required_cols.issubset(df.columns):
            await update.message.reply_text(
                f"❌ Missing columns. Required: {required_cols}\n"
                f"Found: {set(df.columns)}"
            )
            return

        # Clean data
        df = df.dropna(subset=list(required_cols))
        df["answer"] = df["answer"].str.strip().str.upper()

        if df.empty:
            await update.message.reply_text("❌ No valid questions found in the CSV.")
            return

        await update.message.reply_text(
            f"✅ Found *{len(df)} questions*. Starting quiz...",
            parse_mode="Markdown"
        )

        # Send each question as a Telegram quiz poll
        answer_map = {"A": 0, "B": 1, "C": 2, "D": 3}
        sent = 0

        for _, row in df.iterrows():
            correct_index = answer_map.get(row["answer"])
            if correct_index is None:
                continue  # Skip invalid answer values

            await update.message.reply_poll(
                question=str(row["question"]),
                options=[
                    str(row["option_a"]),
                    str(row["option_b"]),
                    str(row["option_c"]),
                    str(row["option_d"]),
                ],
                type="quiz",
                correct_option_id=correct_index,
                is_anonymous=False,
            )
            sent += 1

        await update.message.reply_text(f"🎉 Quiz complete! Sent *{sent}* questions.", parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error parsing CSV: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *How to use:*\n"
        "1. Prepare a CSV with columns: `question, option_a, option_b, option_c, option_d, answer`\n"
        "2. Upload the CSV file to this chat\n"
        "3. The bot will send each row as a Telegram quiz poll\n\n"
        "✅ `answer` must be A, B, C, or D",
        parse_mode="Markdown"
    )

def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n❌ Error: TELEGRAM_BOT_TOKEN environment variable is not set!")
        print("=============================================================")
        print("To run the Telegram Quiz Bot, you need a Bot Token:")
        print("1. Message @BotFather on Telegram to create a new bot.")
        print("2. Copy the HTTP API token.")
        print("3. Create a file named '.env' in this directory with content:")
        print("   TELEGRAM_BOT_TOKEN=your_token_here")
        print("=============================================================\n")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_csv))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()