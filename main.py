from telegram.ext import Application

import config

from admin import register_admin

# Если ваш employee-модуль называется employee:
try:
    from employee import register_handlers as register_employee
except Exception:
    # Если он у вас лежит в handlers/, поправьте импорт под вашу структуру
    from handlers import register_handlers as register_employee


def main() -> None:
    app = Application.builder().token(config.BOT_TOKEN).build()

    # Сначала админ, потом сотрудник
    register_admin(app)
    register_employee(app)

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()