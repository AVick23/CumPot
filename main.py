import logging
from telegram.ext import Application
import config
from handlers import register_handlers
from utils.jobs import setup_jobs

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    register_handlers(app)
    setup_jobs(app)
    logger.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()