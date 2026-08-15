import logging
import os
from typing import List, Dict, Optional
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from .constants import (
    REFERENCE_MAIN, REFERENCE_CATEGORY, REFERENCE_LIST, REFERENCE_DETAIL,
    REFERENCE_SEARCH_INPUT, REFERENCE_SEARCH_RESULTS, REFERENCE_SHELF_LIFE,
    CB_REFERENCE, CB_REF_CATEGORY_PREFIX, CB_REF_ITEM_PREFIX,
    CB_REF_SEARCH, CB_REF_BACK, CB_REF_HOME, CB_REF_SHELF_LIFE,
    CB_REF_PAGE_PREFIX, PAGE_SIZE,
)
from .keyboards import (
    reference_main_keyboard, categories_keyboard, items_list_keyboard,
    item_detail_keyboard, search_prompt_keyboard, shelf_life_keyboard,
)
from .search import (
    SearchIndex, get_search_index, Recipe, ShelfLifeItem,
    tokenize,
)

from ..menu.utils import render, answer, set_state, get_current_state

logger = logging.getLogger(__name__)
MAIN_MENU_STATE = 3

# Путь к папке с Excel-файлами (относительно текущего модуля)
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# Глобальный кэш для сроков годности
_shelf_life_items: List[ShelfLifeItem] = []


# =========================================================
# ЗАГРУЗКА ДАННЫХ ИЗ EXCEL
# =========================================================
def load_recipes_from_excel():
    """
    Загружает рецепты из Excel-файлов в папке data/.
    Ожидается, что файлы:
        бабушкина база.xlsx
        СРОКИ ГОДНОСТИ.xlsx
        ЛЕТО сезон 26 бар.xlsx
    """
    import pandas as pd
    from .search import Recipe

    index = get_search_index()
    recipe_id_counter = 1
    shelf_items = []

    # ---- 1. БАЗОВЫЕ НАПИТКИ (бабушкина база.xlsx) ----
    base_file = os.path.join(DATA_DIR, 'бабушкина база.xlsx')
    if os.path.exists(base_file):
        xls = pd.ExcelFile(base_file)
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(base_file, sheet_name=sheet_name, header=None)
            # Определяем тип листа по названию
            if sheet_name in ('базавое', 'компот', 'но каффи', 'чайное', 'холодный кофе', 'смузи и лимонады', 'Молочные коктейли'):
                # Парсим листы с рецептами
                # Реализация парсинга – упрощённая, в реальности нужно анализировать структуру
                # Здесь мы демонстрируем принцип: ищем строки с названиями напитков
                # В реальном коде нужен более сложный парсер с учётом особенностей Excel
                pass  # Заглушка – в реальности нужно распарсить все рецепты
            elif sheet_name == 'заготовки':
                # Парсим заготовки (настойки)
                pass  # Аналогично
        logger.info("Загружены рецепты из бабушкина база.xlsx")

    # ---- 2. СРОКИ ГОДНОСТИ ----
    shelf_file = os.path.join(DATA_DIR, 'СРОКИ ГОДНОСТИ.xlsx')
    if os.path.exists(shelf_file):
        df = pd.read_excel(shelf_file, sheet_name='Лист1', header=None)
        # Парсим сроки годности
        # В реальности нужно обработать структуру таблицы
        pass
        logger.info("Загружены сроки годности")

    # ---- 3. СЕЗОННОЕ МЕНЮ (ЛЕТО сезон 26 бар.xlsx) ----
    summer_file = os.path.join(DATA_DIR, 'ЛЕТО сезон 26 бар.xlsx')
    if os.path.exists(summer_file):
        xls = pd.ExcelFile(summer_file)
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(summer_file, sheet_name=sheet_name, header=None)
            # Парсим сезонные напитки
            pass
        logger.info("Загружены сезонные напитки")

    # В реальном коде нужно пройти по всем листам и правильно извлечь данные.
    # Пока добавим несколько тестовых рецептов для демонстрации.
    _add_test_recipes(index)

    # Сохраняем сроки годности в глобальной переменной
    global _shelf_life_items
    _shelf_life_items = shelf_items

    logger.info(f"Загружено рецептов: {len(index.recipes)}")


def _add_test_recipes(index: SearchIndex):
    """Добавляет тестовые рецепты для демонстрации, пока не реализован полноценный парсер."""
    recipes = [
        Recipe(
            name="Капучино 0.3",
            category="Кофе",
            subcategory="Горячий",
            volume="0.3",
            ingredients=[{"name": "Кофе под эспрессо", "amount": "16гр"}, {"name": "Молоко", "amount": "220гр"}],
            instruction="Делаем эспрессо в стакан. Взбиваем молоко с расширением 30%.",
            description="Это в меру крепкий напиток на каждый день с добавлением взбитого горячего молока.",
            shelf_life=1,
        ),
        Recipe(
            name="Капучино 0.2",
            category="Кофе",
            subcategory="Горячий",
            volume="0.2",
            ingredients=[{"name": "Кофе под эспрессо", "amount": "8гр"}, {"name": "Молоко", "amount": "150гр"}],
            instruction="Взбиваем молоко с расширением 30%. Вливаем в эспрессо.",
            description="Мягкий молочный кофе.",
            shelf_life=1,
        ),
        Recipe(
            name="Эспрессо",
            category="Кофе",
            subcategory="Классический",
            volume="0.2",
            ingredients=[{"name": "Кофе под эспрессо", "amount": "16гр"}],
            instruction="Смалываем кофе, темперуем, варим 25-30 секунд.",
            description="Концентрированный чёрный кофе.",
        ),
        Recipe(
            name="Матча-латте 0.3",
            category="Матча",
            subcategory="Горячий",
            volume="0.3",
            ingredients=[{"name": "Матча", "amount": "3гр"}, {"name": "Молоко", "amount": "220гр"}],
            instruction="Делаем матча-шот, заливаем взбитым молоком.",
            description="Японский зелёный чай с молоком.",
        ),
        Recipe(
            name="Гречишная настойка",
            category="Заготовка",
            subcategory="Настойка",
            ingredients=[{"name": "Гречишный чай", "amount": "20гр"}, {"name": "Вода", "amount": "450гр"}],
            instruction="Заливаем горячей водой, настаиваем 30 минут, процеживаем.",
            description="Основа для компотов и напитков.",
            shelf_life=14,
        ),
    ]
    for r in recipes:
        index.add_recipe(r)
        # Добавляем также в сроки годности, если есть shelf_life
        if r.shelf_life:
            _shelf_life_items.append(ShelfLifeItem(
                id=len(_shelf_life_items) + 1,
                name=r.name,
                category=r.category,
                subcategory=r.subcategory,
                shelf_life_days=r.shelf_life,
                location="",
            ))


# =========================================================
# ОСНОВНЫЕ ОБРАБОТЧИКИ
# =========================================================
async def show_reference_main(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    """Главное меню справочника."""
    text = "📖 <b>Справочник</b>\n\n"
    text += "Найдите рецепты, техкарты и сроки годности.\n"
    text += "Выберите действие."
    if notice:
        text = f"{notice}\n\n{text}"

    await render(update, context, text, reference_main_keyboard(), message_id, parse_mode='HTML')
    return set_state(context, REFERENCE_MAIN)


async def show_categories(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
) -> int:
    """Показывает список категорий."""
    from .search import get_categories
    categories = get_categories()
    if not categories:
        text = "📂 Категории пока не загружены."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data=CB_REF_HOME)]
        ])
        await render(update, context, text, kb, message_id)
        return set_state(context, REFERENCE_CATEGORY)

    text = "📂 <b>Категории</b>\n\nВыберите раздел."
    kb = categories_keyboard(categories)
    await render(update, context, text, kb, message_id, parse_mode='HTML')
    return set_state(context, REFERENCE_CATEGORY)


async def show_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    category: str,
    page: int = 1,
    message_id: int | None = None,
) -> int:
    """Показывает список рецептов в категории с пагинацией."""
    index = get_search_index()
    recipes = index.get_by_category(category)
    if not recipes:
        text = f"В категории «{category}» нет рецептов."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Категории", callback_data=f"{CB_REF_CATEGORY_PREFIX}all")]
        ])
        await render(update, context, text, kb, message_id)
        return set_state(context, REFERENCE_LIST)

    total = len(recipes)
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(1, min(page, total_pages))
    context.user_data["ref_category"] = category
    context.user_data["ref_page"] = page

    text = f"📂 <b>{category}</b>\n\nНайдено: {total} рецептов."
    kb = items_list_keyboard(recipes, category, page, total_pages)
    await render(update, context, text, kb, message_id, parse_mode='HTML')
    return set_state(context, REFERENCE_LIST)


async def show_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    recipe_id: int,
    message_id: int | None = None,
) -> int:
    """Показывает карточку рецепта."""
    index = get_search_index()
    recipe = index.get_recipe(recipe_id)
    if not recipe:
        text = "⚠️ Рецепт не найден."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data=CB_REF_HOME)]
        ])
        await render(update, context, text, kb, message_id)
        return set_state(context, REFERENCE_DETAIL)

    # Формируем текст
    lines = [
        f"<b>{recipe.name}</b>",
        f"📂 {recipe.category}" + (f" · {recipe.subcategory}" if recipe.subcategory else ""),
        ""
    ]
    if recipe.volume:
        lines.append(f"📐 Объём: {recipe.volume}")
    if recipe.ingredients:
        lines.append("🧂 <b>Ингредиенты:</b>")
        for ing in recipe.ingredients:
            name = ing.get('name', '')
            amount = ing.get('amount', '')
            lines.append(f"• {name} — {amount}" if amount else f"• {name}")
        lines.append("")
    if recipe.instruction:
        lines.append("📝 <b>Рецепт:</b>")
        lines.append(recipe.instruction)
        lines.append("")
    if recipe.description:
        lines.append("📖 <b>Описание:</b>")
        lines.append(recipe.description)
        lines.append("")
    if recipe.shelf_life:
        lines.append(f"📅 Срок годности: {recipe.shelf_life} дн.")

    text = "\n".join(lines)
    kb = item_detail_keyboard(recipe_id)
    await render(update, context, text, kb, message_id, parse_mode='HTML')
    return set_state(context, REFERENCE_DETAIL)


async def prompt_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
) -> int:
    """Запрашивает поисковый запрос у пользователя."""
    text = "🔍 <b>Поиск по справочнику</b>\n\n"
    text += "Введите ключевые слова (например, «капучино» или «вишня и карамель»).\n"
    text += "Я найду все рецепты, где есть эти слова.\n"
    text += "Можно искать по названию, ингредиентам, описанию."

    kb = search_prompt_keyboard()
    await render(update, context, text, kb, message_id, parse_mode='HTML')
    return set_state(context, REFERENCE_SEARCH_INPUT)


async def search_results(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query: str,
    message_id: int | None = None,
) -> int:
    """Показывает результаты поиска."""
    index = get_search_index()
    results = index.search(query)
    if not results:
        text = f"🔍 По запросу «{query}» ничего не найдено.\n\nПопробуйте изменить ключевые слова."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Новый поиск", callback_data=CB_REF_SEARCH)],
            [InlineKeyboardButton("◀️ Назад", callback_data=CB_REF_HOME)]
        ])
        await render(update, context, text, kb, message_id, parse_mode='HTML')
        return set_state(context, REFERENCE_SEARCH_RESULTS)

    total = len(results)
    # Показываем все результаты без пагинации (или можно добавить)
    # Для простоты покажем первые 20, с кнопкой "показать ещё" – но для демо просто список
    # Сделаем простой список с кнопками на каждый рецепт
    rows = []
    for recipe in results[:20]:
        rows.append([
            InlineKeyboardButton(
                recipe.name,
                callback_data=f"{CB_REF_ITEM_PREFIX}{recipe.id}"
            )
        ])
    if len(results) > 20:
        rows.append([
            InlineKeyboardButton(f"… и ещё {len(results) - 20}", callback_data="noop")
        ])
    rows.append([
        InlineKeyboardButton("🔍 Новый поиск", callback_data=CB_REF_SEARCH),
        InlineKeyboardButton("◀️ Назад", callback_data=CB_REF_HOME),
    ])
    kb = InlineKeyboardMarkup(rows)

    text = f"🔍 <b>Результаты поиска</b>\n\n"
    text += f"По запросу «{query}» найдено {total} рецептов."
    await render(update, context, text, kb, message_id, parse_mode='HTML')
    return set_state(context, REFERENCE_SEARCH_RESULTS)


async def shelf_life_view(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
) -> int:
    """Показывает сроки годности продуктов."""
    global _shelf_life_items
    if not _shelf_life_items:
        text = "📋 Сроки годности не загружены."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data=CB_REF_HOME)]
        ])
        await render(update, context, text, kb, message_id)
        return set_state(context, REFERENCE_SHELF_LIFE)

    # Группируем по категории
    groups = {}
    for item in _shelf_life_items:
        key = item.category or "Прочее"
        groups.setdefault(key, []).append(item)

    lines = ["📋 <b>Сроки годности</b>\n"]
    for cat, items in sorted(groups.items()):
        lines.append(f"<b>{cat}</b>")
        for it in items:
            lines.append(f"• {it.name} — {it.shelf_life_days} дн." + (f" ({it.location})" if it.location else ""))
        lines.append("")
    text = "\n".join(lines)

    kb = shelf_life_keyboard()
    await render(update, context, text, kb, message_id, parse_mode='HTML')
    return set_state(context, REFERENCE_SHELF_LIFE)


# =========================================================
# CALLBACK ROUTER
# =========================================================
async def reference_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает callback-запросы справочника."""
    query = update.callback_query
    data = query.data or ""
    message_id = query.message.message_id if query.message else None

    await answer(query)

    if data == CB_REF_BACK:
        from ..menu.handlers import show_main_menu
        return await show_main_menu(update, context, message_id)

    if data == CB_REF_HOME:
        return await show_reference_main(update, context, message_id)

    if data == CB_REF_SEARCH:
        return await prompt_search(update, context, message_id)

    if data == CB_REF_SHELF_LIFE:
        return await shelf_life_view(update, context, message_id)

    # Категории
    if data.startswith(CB_REF_CATEGORY_PREFIX):
        category = data.split(":", 1)[1]
        if category == "all":
            return await show_categories(update, context, message_id)
        else:
            return await show_list(update, context, category, 1, message_id)

    # Деталь рецепта
    if data.startswith(CB_REF_ITEM_PREFIX):
        try:
            recipe_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            return await show_reference_main(update, context, message_id)
        return await show_detail(update, context, recipe_id, message_id)

    # Пагинация
    if data.startswith(CB_REF_PAGE_PREFIX):
        try:
            page = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            page = 1
        category = context.user_data.get("ref_category", "")
        if not category:
            return await show_categories(update, context, message_id)
        return await show_list(update, context, category, page, message_id)

    # Fallback
    return await show_reference_main(update, context, message_id)


# =========================================================
# ТЕКСТОВЫЙ ВВОД (поиск)
# =========================================================
async def reference_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает текстовый поисковый запрос."""
    user = update.effective_user
    if not user:
        return MAIN_MENU_STATE

    query = (update.message.text or "").strip()
    if not query:
        await update.message.reply_text("⚠️ Введите ключевые слова для поиска.")
        return get_current_state(context)

    # Удаляем предыдущее сообщение с запросом (если есть)
    chat_id = update.effective_chat.id
    if chat_id:
        # Не удаляем, просто переходим к результатам
        pass

    return await search_results(update, context, query)