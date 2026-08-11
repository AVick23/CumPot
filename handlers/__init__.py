from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram import Update
from telegram.ext import ContextTypes

from db.users import save_user, get_user

# ===================== EMPLOYEE =====================
from .employee.handlers import (
    employee_start,
    onboarding_name_input,
    onboarding_position,
    main_menu_callback,
    category_selection,
    view_item,
    toggle_item_callback,
    progress_back,
    end_shift_decision,
    noop as employee_noop,
)

from .employee.constants import (
    ONBOARD_NAME,
    ONBOARD_POSITION,
    MAIN_MENU,
    CATEGORY_SELECT,
    CHECKLIST_VIEW,
    ITEM_DETAIL,
    PROGRESS_VIEW,
    END_SHIFT_CONFIRM,
    CB_START_SHIFT,
    CB_END_SHIFT,
    CB_CHECKLIST,
    CB_PROGRESS,
    CB_POSITION_PREFIX,
    CB_CATEGORY_PREFIX,
    CB_ITEM_PREFIX,
    CB_TOGGLE_PREFIX,
    CB_BACK_MENU,
    CB_BACK_CATEGORIES,
    CB_END_SHIFT_CONFIRM,
    CB_END_SHIFT_CANCEL,
)

# ===================== ADMIN =====================
from .admin.handlers import (
    admin_start,
    admin_callback,
    admin_text_input,
)

from .admin.constants import (
    ADMIN_MAIN,
    ADMIN_SHIFTS,
    ADMIN_EMPLOYEES,
    ADMIN_CALENDAR,
    ADMIN_DAY_PROGRESS,
    ADMIN_EDIT_LOCATION,
    ADMIN_EDIT_CATEGORY,
    ADMIN_EDIT_ITEMS,
    ADMIN_ITEM_DETAIL,
    ADMIN_DELETE_CONFIRM,
    ADMIN_ADD_DAY,
    ADMIN_AWAIT_NEW_TEXT,
    ADMIN_AWAIT_EDIT_TEXT,
    CB_HOME,
    CB_SHIFTS,
    CB_EMPLOYEES,
    CB_EDIT,
    CB_EMP_PREFIX,
    CB_PREV_MONTH,
    CB_NEXT_MONTH,
    CB_DAY_PREFIX,
    CB_TO_EMPLOYEES,
    CB_TO_CALENDAR,
    CB_TO_EDIT,
    CB_TO_CATEGORIES,
    CB_TO_ITEMS,
    CB_LOC_PREFIX,
    CB_CAT_PREFIX,
    CB_PAGE_PREFIX,
    CB_ITEM_PREFIX as CB_ADMIN_ITEM_PREFIX,
    CB_EDIT_ITEM_PREFIX,
    CB_DELETE_ITEM_PREFIX,
    CB_CONFIRM_DELETE_PREFIX,
    CB_ADD,
    CB_ADD_DAY_PREFIX,
    CB_ADD_BACK_TEXT,
    CB_CANCEL,
    CB_CANCEL_EDIT,
)


async def start_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Единая точка входа.
    Админ уходит в админку.
    Сотрудник уходит в новый онбординг/меню.
    """
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    # Имя из Telegram НЕ используем как основной профиль сотрудника.
    # Передаём только username, first_name/last_name можно не сохранять.
    save_user(user.id, user.username, None, None)

    user_data = get_user(user.id)

    if user_data and user_data.get("is_admin"):
        return await admin_start(update, context)

    return await employee_start(update, context)


def employee_state(handler, pattern: str):
    return [
        CallbackQueryHandler(handler, pattern=pattern),
        CallbackQueryHandler(employee_noop, pattern="^noop$"),
    ]


def admin_state(pattern: str):
    return [
        CallbackQueryHandler(admin_callback, pattern=pattern),
        CallbackQueryHandler(admin_callback, pattern="^noop$"),
    ]


def register_handlers(app: Application):
    admin_text_cb_pattern = (
        f"^(?:{CB_CANCEL}|{CB_CANCEL_EDIT}|{CB_ADD_BACK_TEXT}|{CB_HOME}|noop)$"
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_router)],
        states={
            # ================= EMPLOYEE =================
            ONBOARD_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_name_input),
            ],

            ONBOARD_POSITION: employee_state(
                onboarding_position,
                f"^{CB_POSITION_PREFIX}.*"
            ),

            MAIN_MENU: employee_state(
                main_menu_callback,
                f"^{CB_START_SHIFT}$|^{CB_END_SHIFT}$|^{CB_CHECKLIST}$|^{CB_PROGRESS}$|^{CB_BACK_MENU}$"
            ),

            CATEGORY_SELECT: employee_state(
                category_selection,
                f"^{CB_CATEGORY_PREFIX}.*|^{CB_BACK_MENU}$"
            ),

            CHECKLIST_VIEW: employee_state(
                view_item,
                f"^{CB_ITEM_PREFIX}.*|^{CB_BACK_CATEGORIES}$|^{CB_BACK_MENU}$"
            ),

            ITEM_DETAIL: employee_state(
                toggle_item_callback,
                f"^{CB_TOGGLE_PREFIX}.*|^{CB_BACK_CATEGORIES}$|^{CB_BACK_MENU}$"
            ),

            PROGRESS_VIEW: employee_state(
                progress_back,
                f"^{CB_BACK_MENU}$"
            ),

            END_SHIFT_CONFIRM: employee_state(
                end_shift_decision,
                f"^{CB_END_SHIFT_CONFIRM}$|^{CB_END_SHIFT_CANCEL}$"
            ),

            # ================= ADMIN =================
            ADMIN_MAIN: admin_state(
                f"^{CB_SHIFTS}$|^{CB_EMPLOYEES}$|^{CB_EDIT}$|^{CB_HOME}$"
            ),

            ADMIN_SHIFTS: admin_state(
                f"^{CB_HOME}$"
            ),

            ADMIN_EMPLOYEES: admin_state(
                f"^{CB_EMP_PREFIX}.*|^{CB_HOME}$"
            ),

            ADMIN_CALENDAR: admin_state(
                f"^{CB_PREV_MONTH}$|^{CB_NEXT_MONTH}$|^{CB_DAY_PREFIX}.*|^{CB_TO_EMPLOYEES}$|^{CB_HOME}$"
            ),

            ADMIN_DAY_PROGRESS: admin_state(
                f"^{CB_TO_CALENDAR}$|^{CB_TO_EMPLOYEES}$|^{CB_HOME}$"
            ),

            ADMIN_EDIT_LOCATION: admin_state(
                f"^{CB_LOC_PREFIX}.*|^{CB_HOME}$"
            ),

            ADMIN_EDIT_CATEGORY: admin_state(
                f"^{CB_CAT_PREFIX}.*|^{CB_TO_EDIT}$|^{CB_HOME}$"
            ),

            ADMIN_EDIT_ITEMS: admin_state(
                f"^{CB_ADMIN_ITEM_PREFIX}.*|^{CB_PAGE_PREFIX}.*|^{CB_ADD}$|^{CB_TO_CATEGORIES}$|^{CB_HOME}$"
            ),

            ADMIN_ITEM_DETAIL: admin_state(
                f"^{CB_EDIT_ITEM_PREFIX}.*|^{CB_DELETE_ITEM_PREFIX}.*|^{CB_TO_ITEMS}$"
            ),

            ADMIN_DELETE_CONFIRM: admin_state(
                f"^{CB_CONFIRM_DELETE_PREFIX}.*|^{CB_ADMIN_ITEM_PREFIX}.*"
            ),

            ADMIN_ADD_DAY: admin_state(
                f"^{CB_ADD_DAY_PREFIX}.*|^{CB_TO_ITEMS}$|^{CB_CANCEL}$"
            ),

            ADMIN_AWAIT_NEW_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_input),
                CallbackQueryHandler(admin_callback, pattern=admin_text_cb_pattern),
            ],

            ADMIN_AWAIT_EDIT_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_input),
                CallbackQueryHandler(admin_callback, pattern=admin_text_cb_pattern),
            ],
        },
        fallbacks=[CommandHandler("start", start_router)],
        per_user=True,
        per_chat=False,
        allow_reentry=True,
    )

    app.add_handler(conv_handler)