import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from akinator.async_akinator import Akinator

# إعداد السجلات لمتابعة الأخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# تخزين جلسات اللعب لكل مستخدم
games = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"أهلاً بك يا {user_name} في لعبة أكيناتور (Akinator)! 🧞‍♂️\n\n"
        "فكر في شخصية حقيقية أو خيالية، وسأحاول تخمينها من خلال طرح الأسئلة.\n"
        "ابدأ اللعبة الآن بإرسال الأمر: /play"
    )

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    aki = Akinator()
    q = await aki.start_game(language='ar')
    games[chat_id] = aki
    await update.message.reply_text(f"سؤال رقم 1:\n{q}\n\nاختر إجابتك من: (نعم، لا، لا أعرف، ربما، تميل إلى لا)")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games:
        await update.message.reply_text("الرجاء بدء لعبة جديدة أولاً باستخدام الأمر: /play")
        return

    aki = games[chat_id]
    text = update.message.text.strip().lower()
    
    # خريطة الإجابات
    answer_mapping = {
        'نعم': 'y', 'yes': 'y', 'y': 'y',
        'لا': 'n', 'no': 'n', 'n': 'n',
        'لا أعرف': 'id', 'dont know': 'id', 'دات نو': 'id',
        'ربما': 'p', 'maybe': 'p', 'p': 'p',
        'تميل إلى لا': 'pn', 'probably not': 'pn'
    }

    if text not in answer_mapping:
        await update.message.reply_text("الرجاء الرد بإحدى الإجابات الصحيحة: (نعم، لا، لا أعرف، ربما، تميل إلى لا)")
        return

    ans = answer_mapping[text]

    try:
        if aki.step >= 80 or aki.progression >= 80:
            await aki.check_win()
            if aki.first_guess:
                guess = aki.first_guess
                await update.message.reply_text(
                    f"هل تخمين هو: **{guess.get('name')}**؟\n({guess.get('description')})\n\nهل هذا صحيح؟ (اكتب: نعم أو لا)"
                )
                return
        
        q = await aki.answer(ans)
        await update.message.reply_text(f"سؤال رقم {aki.step + 1}:\n{q}")
        
    except Exception as e:
        # في حال وصول اللعبة لنهايتها أو التخمين التلقائي
        try:
            await aki.check_win()
            guess = aki.first_guess
            if guess:
                await update.message.reply_text(f"هل شخصيتك هي: **{guess.get('name')}**؟ 🧞‍♂️")
                del games[chat_id]
            else:
                await update.message.reply_text("لقد انتهت الأسئلة ولم أستطِع الجزم بالشخصية بدقة! حاول مجدداً بـ /play")
                del games[chat_id]
        except:
            await update.message.reply_text("حدث خطأ بسيط في اللعبة، حاول مرة أخرى بـ /play")
            if chat_id in games:
                del games[chat_id]

if __name__ == '__main__':
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("Error: BOT_TOKEN environment variable not set!")
        exit(1)
        
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Bot is running...")
    app.run_polling()
