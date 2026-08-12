from telegram.ext import Application
import config
from handlers import register_handlers
from utils.jobs import setup_jobs   # новый импорт


def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    register_handlers(app)
    setup_jobs(app)                  # настраиваем задачи через JobQueue
    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()