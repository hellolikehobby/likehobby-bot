import os
import json
import logging
import asyncio
from datetime import time

import pytz
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# --- Настройки, которые задаются через переменные окружения (не в коде!) ---
BOT_TOKEN = os.environ["BOT_TOKEN"]          # токен от @BotFather
CHANNEL_ID = os.environ["CHANNEL_ID"]        # например "@likehobby_channel" или "-1001234567890"
ADMIN_ID = os.environ.get("ADMIN_ID")        # ваш личный telegram id (для команды /post), необязательно

STATE_FILE = "state.json"
DIALOGUES_FILE = "dialogues.json"
MASCOTS_FILE = "mascots.json"

DELAY_BETWEEN_MESSAGES = 4  # пауза (сек) между репликами — эффект "живого чата"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if os.path.exists(STATE_FILE):
        return load_json(STATE_FILE)
    return {"next_index": 0}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


mascots = load_json(MASCOTS_FILE)
dialogues = load_json(DIALOGUES_FILE)


async def post_next_dialogue(bot: Bot):
    """Публикует следующую по очереди сцену в канал, реплика за репликой."""
    state = load_state()
    idx = state["next_index"] % len(dialogues)
    scene = dialogues[idx]

    for line in scene["lines"]:
        mascot = mascots[line["mascot"]]
        text = f"{mascot['emoji']} *{mascot['name']}*\n{line['text']}"
        await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="Markdown")
        await asyncio.sleep(DELAY_BETWEEN_MESSAGES)

    state["next_index"] = idx + 1
    save_state(state)
    logger.info("Опубликована сцена #%s: %s", idx, scene.get("title", ""))


async def scheduled_post(context: ContextTypes.DEFAULT_TYPE):
    await post_next_dialogue(context.bot)


async def manual_post(update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /post — публикует следующую сцену вручную (для проверки)."""
    if ADMIN_ID and str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("Эта команда доступна только админу.")
        return
    await post_next_dialogue(context.bot)
    await update.message.reply_text("Опубликовано!")


async def whoami(update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /whoami — присылает ваш telegram id, чтобы вписать его в ADMIN_ID."""
    await update.message.reply_text(f"Ваш telegram id: {update.effective_user.id}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("post", manual_post))
    app.add_handler(CommandHandler("whoami", whoami))

    # автопостинг каждый день в 12:00 по Москве — поменяйте время под себя
    moscow = pytz.timezone("Europe/Moscow")
    app.job_queue.run_daily(scheduled_post, time=time(hour=12, minute=0, tzinfo=moscow))

    logger.info("Бот запущен и слушает команды")
    app.run_polling()


if __name__ == "__main__":
    main()
