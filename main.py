from telegram.ext import Application
import config
from handlers import register_handlers

def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    register_handlers(app)
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()