import logging
import pandas as pd
import io
import os
import json
import html
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
    WebAppInfo
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# Import our database module
import db

# Load environment variables
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Retrieve token from environment variable
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Retrieve Mini App URL from environment or fallback
MINI_APP_URL = os.environ.get("TELEGRAM_MINI_APP_URL", "https://ayanadamtew.github.io/Exit_Exam_bot/mini_app/")

def get_main_menu_keyboard():
    """Returns the persistent main menu reply keyboard."""
    keyboard = [
        ["🚀 Start New Quiz", "📊 My Stats"],
        [KeyboardButton("📱 Open Mini App", web_app=WebAppInfo(url=MINI_APP_URL))],
        ["ℹ️ Help"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_progress_bar(percentage):
    """Generates a premium visual progress bar."""
    filled = int(percentage / 10)
    empty = 10 - filled
    return "█" * filled + "░" * empty

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user
    db.save_user(user.id, user.username, user.first_name)
    
    first_name_esc = html.escape(str(user.first_name))
    await update.message.reply_text(
        f"👋 <b>Welcome to the Quiz Bot, {first_name_esc}!</b>\n\n"
        "Let's boost your productivity. To begin, upload a CSV file with your questions, "
        "or press <b>🚀 Start New Quiz</b> for directions.",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /help command and help menu option."""
    await update.message.reply_text(
        "ℹ️ <b>HOW TO USE THE QUIZ BOT</b>\n"
        "────────────────────────\n"
        "1️⃣ Prepare a CSV file containing your quiz questions.\n"
        "2️⃣ Make sure the CSV file has these exact headers:\n"
        "    <code>question, option_a, option_b, option_c, option_d, answer</code>\n"
        "3️⃣ The <code>answer</code> column must be <b>A</b>, <b>B</b>, <b>C</b>, or <b>D</b>.\n"
        "4️⃣ Upload the CSV file directly into this chat.\n"
        "5️⃣ Answer each question using the interactive inline buttons!\n\n"
        "💡 <b>Tip:</b> Check your persistent performance records with <b>📊 My Stats</b>.",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the stats display."""
    user = update.effective_user
    db.save_user(user.id, user.username, user.first_name)
    stats = db.get_user_stats(user.id)
    
    first_name_esc = html.escape(str(user.first_name))
    if not stats:
        await update.message.reply_text(
            "📊 <b>YOUR PERFORMANCE SUMMARY</b>\n"
            "────────────────────────\n"
            "You haven't completed any quizzes yet!\n\n"
            "Upload a questions CSV file to start learning.",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
        return
        
    rating = "📚 Keep studying!"
    if stats["average_score_pct"] >= 90:
        rating = "🏆 Academic Master!"
    elif stats["average_score_pct"] >= 75:
        rating = "🌟 High Achiever!"
    elif stats["average_score_pct"] >= 50:
        rating = "👍 Steady Progress!"
        
    await update.message.reply_text(
        f"📊 <b>YOUR PERFORMANCE SUMMARY</b>\n"
        f"────────────────────────\n"
        f"👤 <b>User:</b> {first_name_esc}\n"
        f"📝 <b>Quizzes Completed:</b> {stats['total_quizzes']}\n"
        f"🎯 <b>Average Accuracy:</b> {stats['average_score_pct']}%\n"
        f"🏆 <b>Highest Score:</b> {stats['high_score']} correct answers\n"
        f"🏅 <b>Rank:</b> {rating}\n"
        f"────────────────────────",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )

async def start_quiz_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt directions to start a new quiz."""
    await update.message.reply_text(
        "🚀 <b>Ready to start a new quiz?</b>\n\n"
        "Simply drag and drop or upload your questions CSV file here!\n\n"
        "If you don't have one ready, download or inspect <b>sample_quiz.csv</b> in the workspace for reference.",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )

async def handle_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes incoming CSV files and starts a quiz session."""
    user = update.effective_user
    db.save_user(user.id, user.username, user.first_name)
    doc = update.message.document

    # Validate file type
    if not doc or not doc.file_name or not doc.file_name.endswith(".csv"):
        await update.message.reply_text("❌ Please upload a valid `.csv` file.")
        return

    status_msg = await update.message.reply_text("⏳ <b>Processing questions database...</b>", parse_mode="HTML")

    try:
        # Download and parse file
        file = await doc.get_file()
        file_bytes = await file.download_as_bytearray()
        
        df = pd.read_csv(io.BytesIO(file_bytes))
        df.columns = df.columns.str.strip().str.lower()

        required_cols = {"question", "option_a", "option_b", "option_c", "option_d", "answer"}
        if not required_cols.issubset(df.columns):
            cols_req = html.escape(', '.join(required_cols))
            cols_found = html.escape(', '.join(df.columns))
            await status_msg.edit_text(
                f"❌ <b>Missing columns!</b>\n\n"
                f"Required: <code>{cols_req}</code>\n"
                f"Found: <code>{cols_found}</code>",
                parse_mode="HTML"
            )
            return

        # Drop rows missing critical columns
        df = df.dropna(subset=list(required_cols))
        df["answer"] = df["answer"].astype(str).str.strip().str.upper()

        # Filter out invalid answers
        df = df[df["answer"].isin({"A", "B", "C", "D"})]

        if df.empty:
            await status_msg.edit_text("❌ No valid questions with options and answers (A, B, C, or D) were found.")
            return

        # Prepare questions dictionary
        questions_list = []
        for _, row in df.iterrows():
            questions_list.append({
                "question": str(row["question"]),
                "option_a": str(row["option_a"]),
                "option_b": str(row["option_b"]),
                "option_c": str(row["option_c"]),
                "option_d": str(row["option_d"]),
                "answer": str(row["answer"])
            })

        # Save to database
        db.start_quiz(user.id, questions_list)
        
        await status_msg.delete()
        await update.message.reply_text(
            f"✅ <b>Quiz loaded successfully!</b>\n"
            f"Found <b>{len(questions_list)}</b> valid questions. Let's begin!",
            parse_mode="HTML"
        )
        
        await send_current_question(update, context, user.id)

    except Exception as e:
        logger.error(f"Error handling CSV: {e}", exc_info=True)
        err_esc = html.escape(str(e))
        await status_msg.edit_text(f"❌ <b>Error parsing CSV:</b> {err_esc}", parse_mode="HTML")

async def send_current_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, message_to_edit=None):
    """Sends the current question in the user's active quiz session."""
    session = db.get_active_quiz(user_id)
    if not session:
        return

    idx = session["current_index"]
    questions = session["questions"]
    
    if idx >= len(questions):
        # We finished the quiz
        await finish_quiz(update, context, user_id, session, message_to_edit)
        return

    q = questions[idx]
    
    # HTML escape user values to prevent parsing crashes
    q_question = html.escape(str(q['question']))
    q_opt_a = html.escape(str(q['option_a']))
    q_opt_b = html.escape(str(q['option_b']))
    q_opt_c = html.escape(str(q['option_c']))
    q_opt_d = html.escape(str(q['option_d']))

    # Format message text beautifully with standard letters
    text = (
        f"📖 <b>Question {idx + 1} of {len(questions)}</b>\n"
        f"────────────────────────\n"
        f"🔹 <b>{q_question}</b>\n\n"
        f"<b>A:</b> {q_opt_a}\n"
        f"<b>B:</b> {q_opt_b}\n"
        f"<b>C:</b> {q_opt_c}\n"
        f"<b>D:</b> {q_opt_d}\n"
        f"────────────────────────"
    )

    # Inline options keyboard
    keyboard = [
        [
            InlineKeyboardButton("A", callback_data="quiz_ans_A"),
            InlineKeyboardButton("B", callback_data="quiz_ans_B"),
        ],
        [
            InlineKeyboardButton("C", callback_data="quiz_ans_C"),
            InlineKeyboardButton("D", callback_data="quiz_ans_D"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if message_to_edit:
        await message_to_edit.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        if update.message:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=user_id, text=text, parse_mode="HTML", reply_markup=reply_markup)

async def handle_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles selected answers from the inline keyboard."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    session = db.get_active_quiz(user_id)
    
    if not session:
        await query.edit_message_text("❌ Session not found. Please upload a new CSV file to start a quiz.")
        return

    idx = session["current_index"]
    questions = session["questions"]
    
    if idx >= len(questions):
        return

    q = questions[idx]
    user_choice = query.data.replace("quiz_ans_", "")
    correct_choice = q["answer"]
    
    is_correct = (user_choice == correct_choice)
    new_score = session["score"] + (1 if is_correct else 0)
    new_index = idx + 1

    # Update state in database
    db.update_quiz_progress(user_id, new_index, new_score)

    # Text display elements
    opt_map = {"A": q["option_a"], "B": q["option_b"], "C": q["option_c"], "D": q["option_d"]}
    user_opt_text = opt_map.get(user_choice, user_choice)
    correct_opt_text = opt_map.get(correct_choice, correct_choice)

    # HTML escape user values to prevent parsing crashes
    q_question = html.escape(str(q['question']))
    q_opt_a = html.escape(str(q['option_a']))
    q_opt_b = html.escape(str(q['option_b']))
    q_opt_c = html.escape(str(q['option_c']))
    q_opt_d = html.escape(str(q['option_d']))
    user_opt_text_esc = html.escape(str(user_opt_text))
    correct_opt_text_esc = html.escape(str(correct_opt_text))

    feedback_emoji = "✅" if is_correct else "❌"
    status_text = (
        f"🎉 <b>Correct!</b> You nailed it." if is_correct 
        else f"⚠️ <b>Incorrect!</b>\n<b>Correct Choice:</b> {correct_choice} ({correct_opt_text_esc})"
    )

    feedback_msg = (
        f"📖 <b>Question {idx + 1} of {len(questions)}</b>\n"
        f"────────────────────────\n"
        f"🔹 <b>{q_question}</b>\n\n"
        f"<b>A:</b> {q_opt_a}\n"
        f"<b>B:</b> {q_opt_b}\n"
        f"<b>C:</b> {q_opt_c}\n"
        f"<b>D:</b> {q_opt_d}\n"
        f"────────────────────────\n"
        f"{feedback_emoji} <b>Your Answer:</b> {user_choice} ({user_opt_text_esc})\n"
        f"{status_text}\n"
        f"────────────────────────"
    )

    # Change inline buttons to a single "Next Question" or "Finish Quiz" button
    button_text = "➡️ Next Question" if new_index < len(questions) else "🎉 View Results"
    keyboard = [[InlineKeyboardButton(button_text, callback_data="quiz_next")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(feedback_msg, parse_mode="HTML", reply_markup=reply_markup)

async def handle_next_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Advances the quiz session to the next question."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    await send_current_question(update, context, user_id, message_to_edit=query.message)

async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, session, message_to_edit=None):
    """Saves quiz results to history and renders a premium performance summary report."""
    score = session["score"]
    total = session["total_questions"]
    pct = round((score / total) * 100) if total > 0 else 0
    
    # Save statistics
    db.record_quiz_history(user_id, score, total)
    db.delete_active_quiz(user_id)
    
    progress = get_progress_bar(pct)
    
    rating_text = "📚 Keep Studying!"
    rating_emoji = "✍️"
    if pct == 100:
        rating_text = "Flawless Performance!"
        rating_emoji = "🏆"
    elif pct >= 80:
        rating_text = "Excellent Work!"
        rating_emoji = "🌟"
    elif pct >= 50:
        rating_text = "Good Effort!"
        rating_emoji = "👍"

    user_name = update.effective_user.first_name if update.effective_user else "Student"
    user_name_esc = html.escape(str(user_name))
    
    summary = (
        f"🎉 <b>QUIZ COMPLETED!</b> 🎉\n"
        f"────────────────────────\n"
        f"👤 <b>Student:</b> {user_name_esc}\n"
        f"🎯 <b>Final Score:</b> {score} / {total}\n"
        f"📈 <b>Accuracy:</b> {pct}%\n\n"
        f"<b>{progress}</b>\n\n"
        f"{rating_emoji} <b>Feedback:</b> {rating_text}\n"
        f"────────────────────────\n"
        f"Your results are saved to your statistics dashboard.\n"
        f"Select an option below to start a new quiz!"
    )

    if message_to_edit:
        await message_to_edit.edit_text(summary, parse_mode="HTML")
        # Send a fresh message with persistent main menu so user is guided
        await context.bot.send_message(
            chat_id=user_id,
            text="Menu refreshed. Upload a new CSV or choose an action:",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        chat_id = update.effective_chat.id
        await context.bot.send_message(
            chat_id=chat_id,
            text=summary,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes questions JSON sent from the Telegram Mini App."""
    user = update.effective_user
    db.save_user(user.id, user.username, user.first_name)
    
    try:
        data_str = update.effective_message.web_app_data.data
        questions_list = json.loads(data_str)
        
        if not questions_list or not isinstance(questions_list, list):
            await update.message.reply_text("❌ Received invalid questions database from Mini App.")
            return
            
        # Save to database and start quiz session
        db.start_quiz(user.id, questions_list)
        
        await update.message.reply_text(
            f"✅ <b>Quiz loaded from Mini App!</b>\n"
            f"Found <b>{len(questions_list)}</b> questions. Let's begin!",
            parse_mode="HTML"
        )
        await send_current_question(update, context, user.id)
        
    except Exception as e:
        logger.error(f"Error handling WebApp data: {e}", exc_info=True)
        err_esc = html.escape(str(e))
        await update.message.reply_text(f"❌ <b>Error parsing WebApp questions:</b> {err_esc}", parse_mode="HTML")

async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dispatches reply keyboard clicks to their respective commands."""
    text = update.message.text
    if text == "🚀 Start New Quiz":
        await start_quiz_instructions(update, context)
    elif text == "📊 My Stats":
        await stats_command(update, context)
    elif text == "ℹ️ Help":
        await help_command(update, context)
    else:
        await update.message.reply_text(
            "❓ <b>Command not recognized.</b>\n\n"
            "Please use the menu buttons below or upload a questions CSV file.",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )

def main():
    # Setup database
    db.init_db()

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

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))

    # CSV Uploads
    app.add_handler(MessageHandler(filters.Document.ALL, handle_csv))
    
    # WebApp data submission
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

    # Keyboard click routing
    app.add_handler(CallbackQueryHandler(handle_answer_callback, pattern="^quiz_ans_"))
    app.add_handler(CallbackQueryHandler(handle_next_callback, pattern="^quiz_next$"))

    # Persistent reply menu options routing
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_menu))

    print("Bot starting up...")
    app.run_polling()

if __name__ == "__main__":
    main()