import html
import logging

from typing import List, Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from .constants import (
    REFERENCE_MAIN,
    REFERENCE_CATEGORY,
    REFERENCE_LIST,
    REFERENCE_DETAIL,
    REFERENCE_SEARCH_INPUT,
    REFERENCE_SEARCH_RESULTS,
    REFERENCE_SHELF_LIFE,
    REFERENCE_BASE,
    REFERENCE_SEASON,
    CB_REF_BACK,
    CB_REF_HOME,
    CB_REF_SEARCH,
    CB_REF_SHELF_LIFE,
    CB_REF_CATEGORY_PREFIX,
    CB_REF_ITEM_PREFIX,
    CB_REF_PAGE_PREFIX,
    CB_REF_SEARCH_PAGE_PREFIX,
    CB_REF_BACK_TO_LIST,
    CB_REF_BASE,
    CB_REF_SEASON,
    PAGE_SIZE,
    SEARCH_PAGE_SIZE,
)

from .keyboards import (
    reference_main_keyboard,
    categories_keyboard,
    items_list_keyboard,
    search_results_keyboard,
    item_detail_keyboard,
    search_prompt_keyboard,
    shelf_life_keyboard,
)

from .search import (
    Recipe,
    ShelfLifeItem,
    get_search_index,
    reset_search_index,
    get_category_counts,
    get_categories,
)

from ..menu.utils import (
    render,
    answer,
    set_state,
    get_current_state,
)


logger = logging.getLogger(__name__)

MAIN_MENU_STATE = 3

_shelf_life_items: List[ShelfLifeItem] = []


# =========================================================
# HELPERS
# =========================================================
def _esc(value) -> str:
    return html.escape(str(value or ""), quote=False)


def _pages(total: int, page_size: int) -> int:
    return max(1, (total + page_size - 1) // page_size)


def _source_label(source: str) -> str:
    return "База" if source == "base" else "Сезон"


# =========================================================
# BUILT-IN DATA (из трёх Excel-файлов)
# =========================================================
# БАЗОВЫЕ РЕЦЕПТЫ (бабушкина база.xlsx)
_BASE_RECIPES = [
    # Кофе
    {"name": "Эспрессо", "category": "Кофе", "subcategory": "Классический", "volume": "0.2", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}], "instruction": "Смалываем кофе, темперуем, варим 25-30 секунд.", "description": "Концентрированный чёрный кофе.", "shelf_life": None},
    {"name": "Капучино 0.2", "category": "Кофе", "subcategory": "Горячий", "volume": "0.2", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~8гр"}, {"name": "Молоко", "amount": "150гр"}], "instruction": "Эспрессо в стакан, взбить молоко 30%, влить.", "description": "Крепкий напиток с молоком.", "shelf_life": None},
    {"name": "Капучино 0.3", "category": "Кофе", "subcategory": "Горячий", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Молоко", "amount": "220гр"}], "instruction": "Двойная порция кофе.", "description": "Насыщенный капучино.", "shelf_life": None},
    {"name": "Латте 0.3", "category": "Кофе", "subcategory": "Горячий", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~8гр"}, {"name": "Молоко", "amount": "220гр"}], "instruction": "Эспрессо, взбить молоко, залить.", "description": "Мягкий кофе с молоком.", "shelf_life": None},
    {"name": "Латте 0.4", "category": "Кофе", "subcategory": "Горячий", "volume": "0.4", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Молоко", "amount": "280гр"}], "instruction": "Большой латте.", "description": "Для больших объёмов.", "shelf_life": None},
    {"name": "Флет 0.2", "category": "Кофе", "subcategory": "Горячий", "volume": "0.2", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Молоко", "amount": "150гр"}], "instruction": "Минимальное расширение молока (10%).", "description": "Крепкий кофе.", "shelf_life": None},
    {"name": "Ванильный раф 0.3", "category": "Кофе", "subcategory": "Горячий", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Сливки 10%", "amount": "180гр"}, {"name": "Ванильный сахар", "amount": "7гр"}], "instruction": "Смешать, взбить 40%.", "description": "Десертный напиток на сливках.", "shelf_life": None},
    {"name": "Гляссе 0.3", "category": "Кофе", "subcategory": "Горячий", "volume": "0.3", "ingredients": [{"name": "Фильтр", "amount": "200гр"}, {"name": "Мороженое", "amount": "100гр"}], "instruction": "Стакан обдать кипятком, положить мороженое, залить фильтром.", "description": "Чёрный кофе с мороженым.", "shelf_life": None},
    {"name": "Американо 0.2", "category": "Кофе", "subcategory": "Горячий", "volume": "0.2", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Горячая вода", "amount": "~150гр"}], "instruction": "Вода, затем эспрессо.", "description": "Чёрный кофе с водой.", "shelf_life": None},
    {"name": "Американо 0.3", "category": "Кофе", "subcategory": "Горячий", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~32гр"}, {"name": "Горячая вода", "amount": "~230гр"}], "instruction": "Двойной эспрессо в воде.", "description": "Большой американо.", "shelf_life": None},
    # Фирменные кофейные
    {"name": "Вишнёвая косточка (горячая)", "category": "Кофе", "subcategory": "Фирменный", "volume": "0.3", "ingredients": [{"name": "Фильтр", "amount": "160гр"}, {"name": "Вишнёвый сок", "amount": "120гр"}, {"name": "Фисташковый сироп", "amount": "5гр"}, {"name": "Гранатовый сироп", "amount": "10гр"}], "instruction": "Прогреть сок с сиропами, смешать с фильтром.", "description": "Согревающий с вишней и фисташкой.", "shelf_life": None},
    {"name": "Космея по-кофейному 0.3", "category": "Кофе", "subcategory": "Фирменный", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Молоко", "amount": "180гр"}, {"name": "Сироп 'гранат'", "amount": "10гр"}, {"name": "Сироп 'фисташка'", "amount": "6гр"}, {"name": "Жасминовая настойка", "amount": "60гр"}], "instruction": "Эспрессо, смешать с остальным, взбить как раф.", "description": "Цветочно-ореховый напиток.", "shelf_life": None},
    {"name": "Бархатный кисс 0.3", "category": "Кофе", "subcategory": "Фирменный", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~8гр"}, {"name": "Молоко", "amount": "180гр"}, {"name": "Настойка эрл грей", "amount": "40гр"}, {"name": "Сироп 'бобы тонка'", "amount": "7гр"}, {"name": "Сироп 'гранат'", "amount": "3гр"}, {"name": "Б/а амаретто", "amount": "15гр"}], "instruction": "Эспрессо, гранатовый сироп, амаретто, взбить молоко с настойкой.", "description": "Пряный ягодный напиток.", "shelf_life": None},
    {"name": "Горячий бамбл 0.3", "category": "Кофе", "subcategory": "Фирменный", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Сок (апельсин/ананас/вишня)", "amount": "240гр"}, {"name": "Сироп (кленовый/лесной орех)", "amount": "5гр"}], "instruction": "Прогреть сок с сиропом, залить эспрессо.", "description": "Согревающий напиток с соком.", "shelf_life": None},
    # Компоты
    {"name": "Компот на кофе 0.3", "category": "Компоты", "subcategory": "Горячий", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Гречишная настойка", "amount": "100гр"}, {"name": "Брусничный концентрат", "amount": "30гр"}, {"name": "Персиковый сироп", "amount": "15гр"}, {"name": "Мёд", "amount": "5гр"}, {"name": "Вода", "amount": "до130гр"}, {"name": "Апельсин", "amount": "долька"}], "instruction": "Смешать настойку, концентрат, сироп, прогреть. Добавить мёд, воду, эспрессо.", "description": "Фирменный компот с кофе.", "shelf_life": None},
    {"name": "Бабушкин компот 0.3", "category": "Компоты", "subcategory": "Горячий", "volume": "0.3", "ingredients": [{"name": "Гречишная настойка", "amount": "130гр"}, {"name": "Персиковый сироп", "amount": "10гр"}, {"name": "Гранатовый сироп", "amount": "10гр"}, {"name": "Брусничный концентрат", "amount": "35гр"}, {"name": "Мёд", "amount": "10гр"}, {"name": "Вода", "amount": "до150гр"}, {"name": "Апельсин", "amount": "долька"}], "instruction": "Смешать, прогреть, добавить мёд и воду.", "description": "Классический компот.", "shelf_life": None},
    {"name": "Чайный компот 0.3", "category": "Компоты", "subcategory": "Горячий", "volume": "0.3", "ingredients": [{"name": "Эрл грей", "amount": "4гр"}, {"name": "Гречишная настойка", "amount": "80гр"}, {"name": "Шиповник концентрат", "amount": "50гр"}, {"name": "Мёд", "amount": "10гр"}, {"name": "Апельсин", "amount": "долька"}, {"name": "Вода", "amount": "до150гр"}], "instruction": "Заварить чай, смешать с настойкой, шиповником, прогреть.", "description": "Компот на эрл грее.", "shelf_life": None},
    # Какао, матча
    {"name": "Какао 0.3", "category": "Какао", "subcategory": "Горячий", "volume": "0.3", "ingredients": [{"name": "Какао", "amount": "18гр"}, {"name": "Ванильный сахар", "amount": "12гр"}, {"name": "Молоко", "amount": "220гр"}], "instruction": "Смешать, взбить стимером до 65°C.", "description": "Плотный какао.", "shelf_life": None},
    {"name": "Холодный какао 0.3", "category": "Какао", "subcategory": "Холодный", "volume": "0.3", "ingredients": [{"name": "Какао", "amount": "15гр"}, {"name": "Ванильный сахар", "amount": "7гр"}, {"name": "Вода", "amount": "25гр"}, {"name": "Молоко", "amount": "150гр"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Какао-шот, залить на молоко со льдом.", "description": "Освежающий какао.", "shelf_life": None},
    {"name": "Матча-латте 0.3", "category": "Матча", "subcategory": "Горячий", "volume": "0.3", "ingredients": [{"name": "Матча", "amount": "3гр"}, {"name": "Вода", "amount": "30гр"}, {"name": "Молоко", "amount": "220гр"}], "instruction": "Матча-шот, залить молоком.", "description": "Зелёный чай с молоком.", "shelf_life": None},
    {"name": "Матча-латте 0.4", "category": "Матча", "subcategory": "Горячий", "volume": "0.4", "ingredients": [{"name": "Матча", "amount": "4гр"}, {"name": "Вода", "amount": "40гр"}, {"name": "Молоко", "amount": "280гр"}], "instruction": "Большая порция.", "description": "Большой матча-латте.", "shelf_life": None},
    {"name": "Матча-тоник 0.3", "category": "Матча", "subcategory": "Холодный", "volume": "0.3", "ingredients": [{"name": "Матча", "amount": "3гр"}, {"name": "Вода", "amount": "30гр"}, {"name": "Тоник", "amount": "170гр"}, {"name": "Сироп 'карамель'", "amount": "5гр"}, {"name": "Лимон", "amount": "долька"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Тоник с карамелью, лимон, залить матча-шотом.", "description": "Освежающий тоник с матчей.", "shelf_life": None},
    # Чай
    {"name": "Дянь Хун Мао Фэн", "category": "Чай", "subcategory": "Красный", "volume": "0.3", "ingredients": [{"name": "Дянь Хун Мао Фэн", "amount": "6гр"}, {"name": "Вода", "amount": "~300гр"}], "instruction": "Заварить 3 мин.", "description": "Красный китайский чай.", "shelf_life": None},
    {"name": "Эрл грей", "category": "Чай", "subcategory": "Чёрный", "volume": "0.3", "ingredients": [{"name": "Эрл грей", "amount": "7гр"}, {"name": "Вода", "amount": "~300гр"}], "instruction": "Заварить 3 мин.", "description": "Классический бергамотный чай.", "shelf_life": None},
    {"name": "Кок чой", "category": "Чай", "subcategory": "Зелёный", "volume": "0.3", "ingredients": [{"name": "Кок чой", "amount": "3гр"}, {"name": "Вода", "amount": "~300гр"}], "instruction": "Заварить 3 мин.", "description": "Узбекский зелёный чай.", "shelf_life": None},
    {"name": "Иван чай с малиной", "category": "Чай", "subcategory": "Травяной", "volume": "0.3", "ingredients": [{"name": "Иван-чай", "amount": "5гр"}, {"name": "Вода", "amount": "~300гр"}], "instruction": "Заварить 5 мин.", "description": "Травяной чай с ягодной нотой.", "shelf_life": None},
    {"name": "Гречишный чай", "category": "Чай", "subcategory": "Травяной", "volume": "0.3", "ingredients": [{"name": "Гречишный чай", "amount": "6гр"}, {"name": "Вода", "amount": "~300гр"}], "instruction": "Заварить 5 мин.", "description": "Медово-карамельный тизан.", "shelf_life": None},
    # Авторские чаи
    {"name": "Ананасовый пунш 0.3", "category": "Чай", "subcategory": "Авторский", "volume": "0.3", "ingredients": [{"name": "Дянь хун маофэн", "amount": "5гр"}, {"name": "Пряный сироп", "amount": "3гр"}, {"name": "Кленовый сироп", "amount": "5гр"}, {"name": "Кордиал 'пряный ананас'", "amount": "5гр"}, {"name": "Ананасовый сок", "amount": "70гр"}, {"name": "Корица", "amount": "0,1гр"}, {"name": "Апельсин", "amount": "долька"}, {"name": "Вода", "amount": "~200гр"}], "instruction": "Заварить чай с корицей, смешать с прогретым соком и сиропами.", "description": "Ананасово-пряный пунш.", "shelf_life": None},
    {"name": "Вишнёвый на иван-чае 0.3", "category": "Чай", "subcategory": "Авторский", "volume": "0.3", "ingredients": [{"name": "Настойка на иван-чае", "amount": "100гр"}, {"name": "Апельсиновый сок", "amount": "50гр"}, {"name": "Кордиал 'пряный ананас'", "amount": "5гр"}, {"name": "Вишнёвое конфи", "amount": "50гр"}, {"name": "Кизиловый соус", "amount": "3гр"}, {"name": "Вода", "amount": "до100гр"}, {"name": "Лимон", "amount": "долька"}], "instruction": "Смешать, прогреть, добавить конфи и воду.", "description": "Вишнёвый чай на иван-чае.", "shelf_life": None},
    {"name": "Лимонный чай с барбарисом 0.3", "category": "Чай", "subcategory": "Авторский", "volume": "0.3", "ingredients": [{"name": "Настойка на улуне", "amount": "80гр"}, {"name": "Вишнёвый сок", "amount": "60гр"}, {"name": "Лимонный концентрат", "amount": "25гр"}, {"name": "Б/а амаретто", "amount": "7гр"}, {"name": "Кордиал 'пряный ананас'", "amount": "7гр"}, {"name": "Сироп 'бобы тонка'", "amount": "10гр"}, {"name": "Вода", "amount": "~100гр"}, {"name": "Барбарис", "amount": "до2гр"}], "instruction": "Смешать, прогреть, залить водой, добавить барбарис.", "description": "Цитрусовый чай с барбарисом.", "shelf_life": None},
    {"name": "Отчайный сбор от бабушки 0.3", "category": "Чай", "subcategory": "Авторский", "volume": "0.3", "ingredients": [{"name": "Дянь хун мао фэн", "amount": "6гр"}, {"name": "Шиповник", "amount": "4гр"}, {"name": "Чабрец", "amount": "2гр"}, {"name": "Мёд", "amount": "10гр"}, {"name": "Вода", "amount": "~320гр"}], "instruction": "Заварить чай с чабрецом, добавить шиповник, мёд.", "description": "Терпкий чай с мёдом.", "shelf_life": None},
    # Холодный кофе
    {"name": "Холодный фильтр 0.3", "category": "Холодный кофе", "subcategory": "Чёрный", "volume": "0.3", "ingredients": [{"name": "Охлаждённый фильтр", "amount": "190гр"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Аэрировать, налить на лёд.", "description": "Холодный чёрный кофе.", "shelf_life": None},
    {"name": "Холодный фильтр 0.45", "category": "Холодный кофе", "subcategory": "Чёрный", "volume": "0.45", "ingredients": [{"name": "Охлаждённый фильтр", "amount": "250гр"}, {"name": "Лёд", "amount": "~150гр"}], "instruction": "Большая порция.", "description": "Большой холодный фильтр.", "shelf_life": None},
    {"name": "Вишнёвая косточка (холодная)", "category": "Холодный кофе", "subcategory": "Авторский", "volume": "0.3", "ingredients": [{"name": "Охлаждённый фильтр", "amount": "120гр"}, {"name": "Вишнёвый сок", "amount": "90гр"}, {"name": "Фисташковый сироп", "amount": "5гр"}, {"name": "Гранатовый сироп", "amount": "10гр"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Смешать на льду.", "description": "Холодный кофе с вишней.", "shelf_life": None},
    {"name": "Фильтр-тоник 0.3", "category": "Холодный кофе", "subcategory": "Чёрный", "volume": "0.3", "ingredients": [{"name": "Охлаждённый фильтр", "amount": "110гр"}, {"name": "Тоник", "amount": "110гр"}, {"name": "Лимон", "amount": "долька"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Тоник, фильтр, лимон на лёд.", "description": "Фильтр-тоник.", "shelf_life": None},
    {"name": "Бамбл на фильтре 0.3", "category": "Холодный кофе", "subcategory": "Чёрный", "volume": "0.3", "ingredients": [{"name": "Охлаждённый фильтр", "amount": "110гр"}, {"name": "Сок (апельсин/ананас/вишня)", "amount": "110гр"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Сок + фильтр на лёд.", "description": "Холодный кофе с соком.", "shelf_life": None},
    {"name": "Холодный компот на кофе 0.3", "category": "Холодный кофе", "subcategory": "Авторский", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Гречишная настойка", "amount": "70гр"}, {"name": "Брусничный концентрат", "amount": "25гр"}, {"name": "Персиковый сироп", "amount": "10гр"}, {"name": "Мёд", "amount": "5гр"}, {"name": "Вода", "amount": "80гр"}, {"name": "Апельсин", "amount": "долька"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Смешать, залить эспрессо на лёд.", "description": "Холодный компот.", "shelf_life": None},
    {"name": "Бамбл (на эспрессо) 0.3", "category": "Холодный кофе", "subcategory": "С молоком", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Сок", "amount": "170гр"}, {"name": "Сироп", "amount": "5гр"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Сок с сиропом, лёд, эспрессо.", "description": "Классический бамбл.", "shelf_life": None},
    {"name": "Эспрессо-тоник 0.3", "category": "Холодный кофе", "subcategory": "Чёрный", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Тоник", "amount": "170гр"}, {"name": "Сироп 'карамель'", "amount": "5гр"}, {"name": "Лимон", "amount": "долька"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Тоник с карамелью, лимон, лёд, эспрессо.", "description": "Кофейный тоник.", "shelf_life": None},
    {"name": "Холодный латте 0.3", "category": "Холодный кофе", "subcategory": "С молоком", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Молоко", "amount": "170гр"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Молоко, лёд, эспрессо.", "description": "Классический холодный латте.", "shelf_life": None},
    {"name": "Холодный шоколадный 0.3", "category": "Холодный кофе", "subcategory": "С молоком", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Нутелла", "amount": "30гр"}, {"name": "Молоко", "amount": "150гр"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Нутелла с эспрессо, залить на молоко со льдом.", "description": "Шоколадный латте.", "shelf_life": None},
    {"name": "Холодный ореховый 0.3", "category": "Холодный кофе", "subcategory": "С молоком", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Арахисовая паста", "amount": "20гр"}, {"name": "Сироп 'карамель'", "amount": "3гр"}, {"name": "Молоко", "amount": "130гр"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Паста с сиропом и эспрессо, залить молоком со льдом.", "description": "Ореховый латте.", "shelf_life": None},
    {"name": "Холодный ягодный 0.3", "category": "Холодный кофе", "subcategory": "С молоком", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Настойка на иван-чае", "amount": "30гр"}, {"name": "Шиповник", "amount": "10гр"}, {"name": "Сироп 'малина'", "amount": "5гр"}, {"name": "Молоко", "amount": "120гр"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Молоко, настойка, шиповник, сироп, лёд, эспрессо.", "description": "Ягодный латте.", "shelf_life": None},
    # Лимонады и смузи
    {"name": "Холодный бабушкин компот (лимонад)", "category": "Лимонады", "subcategory": "Безалкогольный", "volume": "0.3", "ingredients": [{"name": "Гречишная настойка", "amount": "50гр"}, {"name": "Иванова настойка", "amount": "50гр"}, {"name": "Персиковый сироп", "amount": "10гр"}, {"name": "Гранатовый сироп", "amount": "10гр"}, {"name": "Брусничный концентрат", "amount": "35гр"}, {"name": "Апельсин", "amount": "долька"}, {"name": "Вода", "amount": "50гр"}, {"name": "Лёд", "amount": "100гр"}], "instruction": "Смешать всё на льду.", "description": "Холодный компот.", "shelf_life": None},
    {"name": "Дикая ягода 0.3", "category": "Лимонады", "subcategory": "С газом", "volume": "0.3", "ingredients": [{"name": "Настойка эрл грей", "amount": "50гр"}, {"name": "Кизиловый соус", "amount": "3гр"}, {"name": "Сироп 'гранат'", "amount": "5гр"}, {"name": "Амаретто б/а", "amount": "10гр"}, {"name": "Шиповник", "amount": "40гр"}, {"name": "Тоник", "amount": "20гр"}, {"name": "Содовая", "amount": "70гр"}, {"name": "Апельсин", "amount": "долька"}, {"name": "Барбарис", "amount": "до2гр"}, {"name": "Лёд", "amount": "~80гр"}], "instruction": "Смешать, добавить тоник и содовую.", "description": "Ягодный лимонад.", "shelf_life": None},
    {"name": "Бабушкин сад 0.3", "category": "Лимонады", "subcategory": "Безалкогольный", "volume": "0.3", "ingredients": [{"name": "Жасминовая настойка", "amount": "30гр"}, {"name": "Иванова настойка", "amount": "30гр"}, {"name": "Малиновый сироп", "amount": "3гр"}, {"name": "Сливовый сироп", "amount": "7гр"}, {"name": "Лимонный концентрат", "amount": "20гр"}, {"name": "Лаймовый сок", "amount": "3гр"}, {"name": "Вода", "amount": "80гр"}, {"name": "Базилик", "amount": "веточка"}, {"name": "Лёд", "amount": "100гр"}], "instruction": "Смешать на льду, украсить базиликом.", "description": "Цитрусово-малиновый лимонад.", "shelf_life": None},
    # Смузи
    {"name": "Смузи 'вместо завтрака' 0.3", "category": "Смузи", "subcategory": "Фруктово-ягодный", "volume": "0.3", "ingredients": [{"name": "Ежевика", "amount": "70гр"}, {"name": "Чиа", "amount": "60гр"}, {"name": "Йогурт", "amount": "60гр"}, {"name": "Банан", "amount": "70гр"}, {"name": "Овсянка", "amount": "20гр"}, {"name": "Вода", "amount": "80гр"}], "instruction": "Всё в блендер, взбить.", "description": "Плотный йогуртовый смузи.", "shelf_life": None},
    {"name": "Смузи 'вместо грусти' 0.3", "category": "Смузи", "subcategory": "Фруктовый", "volume": "0.3", "ingredients": [{"name": "Шпинат", "amount": "50гр"}, {"name": "Арахисовая паста", "amount": "30гр"}, {"name": "Банан", "amount": "50гр"}, {"name": "Груша", "amount": "60гр"}, {"name": "Миндальное молоко", "amount": "120гр"}, {"name": "Вода", "amount": "60гр"}], "instruction": "Всё в блендер.", "description": "Тонизирующий смузи.", "shelf_life": None},
    {"name": "Смузи 'вместо несквик' 0.3", "category": "Смузи", "subcategory": "Шоколадный", "volume": "0.3", "ingredients": [{"name": "Финики", "amount": "40гр"}, {"name": "Молоко", "amount": "170гр"}, {"name": "Какао", "amount": "15гр"}, {"name": "Банан", "amount": "60гр"}, {"name": "Овсянка", "amount": "20гр"}, {"name": "Вода", "amount": "50гр"}], "instruction": "Всё в блендер.", "description": "Сладкий смузи с какао.", "shelf_life": None},
    {"name": "Смузи 'вместо плохого самочувствия' 0.3", "category": "Смузи", "subcategory": "Оздоровительный", "volume": "0.3", "ingredients": [{"name": "Вишня", "amount": "70гр"}, {"name": "Банан", "amount": "60гр"}, {"name": "Арахисовая паста", "amount": "20гр"}, {"name": "Мёд", "amount": "10гр"}, {"name": "Шиповник", "amount": "60гр"}, {"name": "Вода", "amount": "80гр"}, {"name": "Овсяное молоко", "amount": "80гр"}], "instruction": "Всё в блендер.", "description": "Витаминный смузи.", "shelf_life": None},
    # Молочные коктейли
    {"name": "Классический молочный коктейль 0.3", "category": "Молочные коктейли", "subcategory": "Классический", "volume": "0.3", "ingredients": [{"name": "Молоко", "amount": "150гр"}, {"name": "Банан", "amount": "65гр"}, {"name": "Мороженое", "amount": "65гр"}], "instruction": "Смешать в блендере 1-1,5 мин.", "description": "Классический коктейль.", "shelf_life": None},
    {"name": "Ягодный молочный коктейль 0.3", "category": "Молочные коктейли", "subcategory": "Ягодный", "volume": "0.3", "ingredients": [{"name": "Молоко", "amount": "150гр"}, {"name": "Банан", "amount": "65гр"}, {"name": "Мороженое", "amount": "65гр"}, {"name": "Вишня/Ежевика", "amount": "30гр"}], "instruction": "Смешать в блендере.", "description": "Коктейль с ягодами.", "shelf_life": None},
    {"name": "Молочный коктейль с пастой 0.3", "category": "Молочные коктейли", "subcategory": "С пастой", "volume": "0.3", "ingredients": [{"name": "Молоко", "amount": "150гр"}, {"name": "Банан", "amount": "65гр"}, {"name": "Мороженое", "amount": "65гр"}, {"name": "Арахисовая паста", "amount": "25гр"}], "instruction": "Пасту на дно, остальное взбить.", "description": "Коктейль с ореховой пастой.", "shelf_life": None},
    # Заготовки
    {"name": "Гречишная настойка", "category": "Заготовки", "subcategory": "Настойка", "volume": "400мл", "ingredients": [{"name": "Гречишный чай", "amount": "20гр"}, {"name": "Бадьян", "amount": "2гр"}, {"name": "Корица", "amount": "1гр"}, {"name": "Имбирь", "amount": "1гр"}, {"name": "Вода", "amount": "450гр"}], "instruction": "Залить водой, настаивать 30 мин, процедить. Хранить до 14 суток.", "description": "Пряная настойка.", "shelf_life": 14},
    {"name": "Жасминовая настойка", "category": "Заготовки", "subcategory": "Настойка", "volume": "500мл", "ingredients": [{"name": "Кок чой", "amount": "15гр"}, {"name": "Жасмин", "amount": "7гр"}, {"name": "Вода", "amount": "500гр"}], "instruction": "Залить водой, настаивать 15 мин, процедить. Хранить до 14 суток.", "description": "Цветочная настойка.", "shelf_life": 14},
    {"name": "Иванова настойка", "category": "Заготовки", "subcategory": "Настойка", "volume": "500мл", "ingredients": [{"name": "Иван-чай", "amount": "20гр"}, {"name": "Вода", "amount": "550гр"}], "instruction": "Залить водой, настаивать 30 мин, процедить. Хранить до 14 суток.", "description": "Травянистая настойка.", "shelf_life": 14},
    {"name": "Эрл грей настойка", "category": "Заготовки", "subcategory": "Настойка", "volume": "400мл", "ingredients": [{"name": "Эрл грей", "amount": "20гр"}, {"name": "Корица", "amount": "1гр"}, {"name": "Вода", "amount": "450гр"}], "instruction": "Залить водой, настаивать 30 мин, процедить. Хранить до 14 суток.", "description": "Чайная настойка.", "shelf_life": 14},
    {"name": "Улуновая настойка", "category": "Заготовки", "subcategory": "Настойка", "volume": "450мл", "ingredients": [{"name": "Улун", "amount": "15гр"}, {"name": "Вода", "amount": "500гр"}], "instruction": "Залить водой, настаивать 15 мин, процедить. Хранить до 14 суток.", "description": "Настойка на улуне.", "shelf_life": 14},
]

# СЕЗОННЫЕ РЕЦЕПТЫ (ЛЕТО сезон 26 бар.xlsx)
_SEASON_RECIPES = [
    {"name": "Изотоник на клюковке (эспрессо) 0.3", "category": "Тоники", "subcategory": "Кофеиносодержащее", "volume": "0.3", "ingredients": [{"name": "Кофе под эспрессо", "amount": "~16гр"}, {"name": "Тоник", "amount": "110гр"}, {"name": "Клюковка б/а", "amount": "15гр"}, {"name": "Сироп 'Бобы тонка'", "amount": "3гр"}, {"name": "Сироп 'Гранат'", "amount": "3гр"}, {"name": "Соль", "amount": "0,3гр"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Смешать тоник, клюковку, сиропы, лёд, эспрессо, соль.", "description": "Ягодно-гранатовый тоник.", "shelf_life": None},
    {"name": "Изотоник на клюковке (ходзича) 0.3", "category": "Тоники", "subcategory": "Кофеиносодержащее", "volume": "0.3", "ingredients": [{"name": "Ходзича основа", "amount": "25гр"}, {"name": "Тоник", "amount": "110гр"}, {"name": "Клюковка б/а", "amount": "15гр"}, {"name": "Сироп 'Бобы тонка'", "amount": "3гр"}, {"name": "Сироп 'Гранат'", "amount": "3гр"}, {"name": "Соль", "amount": "0,3гр"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Аналогично, но с ходзичей.", "description": "Тоник с ходзичей.", "shelf_life": None},
    {"name": "Ещё один компот на кофе 0.3", "category": "Компоты", "subcategory": "Сезонный", "volume": "0.3", "ingredients": [{"name": "Чабрецовый фильтр", "amount": "180гр"}, {"name": "Шиповник", "amount": "30гр"}, {"name": "Лимонный сок", "amount": "3гр"}, {"name": "Лимон", "amount": "долька"}, {"name": "Тимьян", "amount": "веточка"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Смешать всё на льду.", "description": "Компот с чабрецом.", "shelf_life": None},
    {"name": "Молочный шаг 0.3", "category": "С молоком", "subcategory": "Кофеиносодержащее", "volume": "0.3", "ingredients": [{"name": "Ликёрный ходзича", "amount": "70гр"}, {"name": "Шиповник", "amount": "20гр"}, {"name": "Гречишная настойка", "amount": "60гр"}, {"name": "Барбарис", "amount": "украшение"}, {"name": "Лёд", "amount": "100гр"}], "instruction": "В шейкере смешать, взбить со льдом.", "description": "Напиток с ходзичей.", "shelf_life": None},
    {"name": "Бетта 0.3", "category": "Освежающее", "subcategory": "Безалкогольный", "volume": "0.3", "ingredients": [{"name": "Инжировый конфитюр", "amount": "50гр"}, {"name": "Иванов настой", "amount": "50гр"}, {"name": "Вода", "amount": "50гр"}, {"name": "Клюковка б/а", "amount": "10гр"}, {"name": "Пенка", "amount": "30гр"}, {"name": "Соль", "amount": "0,3гр"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Смешать, процедить, подавать с пенкой и солью.", "description": "Напиток с инжиром.", "shelf_life": None},
    {"name": "НеБуратино 0.4", "category": "Освежающее", "subcategory": "Безалкогольный", "volume": "0.4", "ingredients": [{"name": "Кордиал груша-вино-сирень", "amount": "70гр"}, {"name": "Жасминовая настойка", "amount": "70гр"}, {"name": "Тоник", "amount": "55гр"}, {"name": "Содовая", "amount": "100гр"}, {"name": "Сироп 'табак-ваниль'", "amount": "7гр"}, {"name": "Тимьян", "amount": "веточка"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Смешать всё, добавить лёд и тимьян.", "description": "Грушевый лимонад.", "shelf_life": None},
    {"name": "Домашний колокольчик 0.4", "category": "Освежающее", "subcategory": "Лимонад", "volume": "0.4", "ingredients": [{"name": "Лимонный сок", "amount": "35гр"}, {"name": "Сливовый сироп", "amount": "15гр"}, {"name": "Карамель", "amount": "10гр"}, {"name": "Мёд", "amount": "15гр"}, {"name": "Вода", "amount": "15гр"}, {"name": "Содовая", "amount": "160гр"}, {"name": "Лимон", "amount": "долька"}, {"name": "Апельсин", "amount": "долька"}, {"name": "Лёд", "amount": "~100гр"}], "instruction": "Растворить мёд, смешать, добавить лёд и цитрусы.", "description": "Лимонад со сливой.", "shelf_life": None},
    {"name": "Малинкин 0.3", "category": "Горячее", "subcategory": "Чай", "volume": "0.3", "ingredients": [{"name": "Настойка на улуне", "amount": "100гр"}, {"name": "Гречишная настойка", "amount": "40гр"}, {"name": "Вишнёвый сок", "amount": "40гр"}, {"name": "Ежевичное варенье", "amount": "50гр"}, {"name": "Сахар", "amount": "7гр"}, {"name": "Вода", "amount": "до100гр"}], "instruction": "В стакан варенье, остальное прогреть, залить.", "description": "Горячий чай с ежевикой.", "shelf_life": None},
    # Заготовки из летнего меню
    {"name": "Ходзича основа", "category": "Заготовки", "subcategory": "Чайная основа", "volume": "300мл", "ingredients": [{"name": "Ходзича порошок", "amount": "12гр"}, {"name": "Вода", "amount": "300гр"}], "instruction": "Отсеять, залить водой, перемешать, процедить. Хранить до суток.", "description": "Основа для напитков.", "shelf_life": 1},
    {"name": "Ряженковый крем", "category": "Заготовки", "subcategory": "Крем", "volume": "500мл", "ingredients": [{"name": "Ряженка 4%", "amount": "460гр"}, {"name": "Сироп 'бобы тонка'", "amount": "40гр"}, {"name": "Ксантановая камедь", "amount": "1гр"}, {"name": "N2O", "amount": "1 баллон"}], "instruction": "Смешать, перелить в сифон, зарядить баллоном. Хранить до 4 суток.", "description": "Крем для пенки.", "shelf_life": 4},
    {"name": "Чабрецовый фильтр", "category": "Заготовки", "subcategory": "Фильтр", "volume": "1300мл", "ingredients": [{"name": "Фильтр холодный", "amount": "1100гр"}, {"name": "Чабрец", "amount": "17гр"}, {"name": "Тростниковый сахар", "amount": "170гр"}, {"name": "Вода", "amount": "90гр"}], "instruction": "Растворить сахар, смешать с чабрецом и фильтром, настаивать 12-14 ч, процедить. Хранить до 14 суток.", "description": "Фильтр с чабрецом.", "shelf_life": 14},
    {"name": "Ликёрный ходзича", "category": "Заготовки", "subcategory": "Ликёр", "volume": "450мл", "ingredients": [{"name": "Ходзича", "amount": "10гр"}, {"name": "Вода", "amount": "50гр"}, {"name": "Амаретто б/а", "amount": "250гр"}, {"name": "Сгущенка", "amount": "150гр"}], "instruction": "Смешать ходзичу с водой, процедить. Смешать с амаретто и сгущенкой. Настаивать 5 суток, процедить. Хранить до 30 суток.", "description": "Ликёрная основа.", "shelf_life": 30},
]

# СРОКИ ГОДНОСТИ
_SHELF_ITEMS_DATA = [
    ("лимончелло", "Сладкое", "молочное", 3),
    ("торт груша и рикотта", "Сладкое", "молочное", 3),
    ("трубочки маскарпоне", "Сладкое", "молочное", 10),
    ("трубочки со сгущенкой", "Сладкое", "молочное", 10),
    ("чиа пудинг еж ягода", "Сладкое", "молочное", 3),
    ("чиа пудинг бабушкин", "Сладкое", "молочное", 2),
    ("Тирамису", "Сладкое", "молочное", 3),
    ("сырники", "Сладкое", "молочное", 4),
    ("Маковый рулет", "Сладкое", "НЕмолочное", 2),
    ("Морковный кекс", "Сладкое", "НЕмолочное", 2),
    ("Банановый кекс", "Сладкое", "НЕмолочное", 2),
    ("Круассаны", "Сладкое", "НЕмолочное", 1),
    ("Киш с курицей", "Сытное", "молочное", 3),
    ("Салат с курицей", "Сытное", "молочное", 3),
    ("Драники", "Сытное", "НЕмолочное", 4),
]


# =========================================================
# DATA BUILDERS
# =========================================================
def _build_recipes_list() -> List[Recipe]:
    recipes = []
    for data in _BASE_RECIPES:
        recipes.append(Recipe(**data, source="base"))
    for data in _SEASON_RECIPES:
        recipes.append(Recipe(**data, source="season"))
    return recipes


def _build_shelf_life_items() -> List[ShelfLifeItem]:
    items = []
    for i, (name, cat, sub, days) in enumerate(_SHELF_ITEMS_DATA, start=1):
        items.append(ShelfLifeItem(
            id=i, name=name, category=cat, subcategory=sub,
            shelf_life_days=days, location="Витрина"
        ))
    return items


def load_recipes_from_excel() -> None:
    global _shelf_life_items

    index = reset_search_index()
    for recipe in _build_recipes_list():
        index.add_recipe(recipe)

    shelf_items = _build_shelf_life_items()
    existing_names = {item.name.lower() for item in shelf_items}
    next_id = len(shelf_items) + 1

    for recipe in index.recipes.values():
        if recipe.shelf_life and recipe.name.lower() not in existing_names:
            shelf_items.append(ShelfLifeItem(
                id=next_id, name=recipe.name, category=recipe.category,
                subcategory=recipe.subcategory, shelf_life_days=recipe.shelf_life, location=""
            ))
            existing_names.add(recipe.name.lower())
            next_id += 1

    _shelf_life_items = sorted(shelf_items, key=lambda item: ((item.category or "").lower(), item.name.lower()))

    logger.info("Загружено рецептов: %d (база: %d, сезон: %d)",
                len(index.recipes),
                len([r for r in index.recipes.values() if r.source == "base"]),
                len([r for r in index.recipes.values() if r.source == "season"]))
    logger.info("Загружено позиций сроков годности: %d", len(_shelf_life_items))


# =========================================================
# SCREENS
# =========================================================
async def show_reference_main(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    index = get_search_index()
    base_count = len([r for r in index.recipes.values() if r.source == "base"])
    season_count = len([r for r in index.recipes.values() if r.source == "season"])

    text = (
        "📖 <b>Справочник</b>\n\n"
        "Все рецепты и техкарты в одном месте.\n\n"
        f"• 📖 База рецептов: {base_count}\n"
        f"• ☀️ Сезонное меню: {season_count}\n"
        f"• 📅 Сроки годности: {len(_shelf_life_items)}"
    )
    if notice:
        text = f"{notice}\n\n{text}"

    await render(update, context, text, reference_main_keyboard(), message_id, parse_mode="HTML")
    return set_state(context, REFERENCE_MAIN)


async def show_base(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int | None = None) -> int:
    return await show_source_screen(update, context, "base", message_id, "📖 База рецептов")


async def show_season(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int | None = None) -> int:
    return await show_source_screen(update, context, "season", message_id, "☀️ Сезонное меню")


async def show_source_screen(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    source: str,
    message_id: int | None = None,
    title: str = "Рецепты"
) -> int:
    category_counts = get_category_counts(source)
    if not category_counts:
        text = f"{title}\n\nКатегории не загружены."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Меню", callback_data=CB_REF_HOME)]])
        await render(update, context, text, kb, message_id)
        return set_state(context, REFERENCE_BASE if source == "base" else REFERENCE_SEASON)

    text = f"{title}\n\nВыберите категорию:"
    await render(update, context, text, categories_keyboard(category_counts, source), message_id, parse_mode="HTML")
    return set_state(context, REFERENCE_BASE if source == "base" else REFERENCE_SEASON)


async def show_categories(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
) -> int:
    return await show_reference_main(update, context, message_id)


async def show_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    category: str,
    source: str,
    page: int = 1,
    message_id: int | None = None,
) -> int:
    index = get_search_index()
    recipes = index.get_by_category(category, source)

    if not recipes:
        text = f"В категории «{category}» нет рецептов."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=CB_REF_HOME)]])
        await render(update, context, text, kb, message_id)
        return set_state(context, REFERENCE_LIST)

    total = len(recipes)
    total_pages = _pages(total, PAGE_SIZE)
    page = max(1, min(page, total_pages))

    context.user_data["ref_category"] = category
    context.user_data["ref_source"] = source
    context.user_data["ref_page"] = page
    context.user_data["ref_last_view"] = ("category", source, category, page)

    start = (page - 1) * PAGE_SIZE
    page_items = recipes[start:start + PAGE_SIZE]

    text = f"📂 <b>{category}</b>  ·  {_source_label(source)}\n\nНайдено: {total} рецептов." + (f"\nСтраница {page}/{total_pages}." if total_pages > 1 else "")

    await render(update, context, text, items_list_keyboard(page_items, category, page, total_pages), message_id, parse_mode="HTML")
    return set_state(context, REFERENCE_LIST)


async def show_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    recipe_id: int,
    message_id: int | None = None,
) -> int:
    index = get_search_index()
    recipe = index.get_recipe(recipe_id)

    if not recipe:
        text = "⚠️ Рецепт не найден."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Меню", callback_data=CB_REF_HOME)]])
        await render(update, context, text, kb, message_id)
        return set_state(context, REFERENCE_DETAIL)

    lines = [f"🍹 <b>{_esc(recipe.name)}</b>", f"📂 {_esc(recipe.category)} · {_source_label(recipe.source)}"]
    if recipe.subcategory:
        lines[-1] += f" · {_esc(recipe.subcategory)}"
    lines.append("")
    if recipe.volume:
        lines.append(f"📐 Объём: {_esc(recipe.volume)}")
    if recipe.shelf_life:
        lines.append(f"📅 Срок годности: {recipe.shelf_life} дн.")

    if recipe.ingredients:
        lines.append("")
        lines.append("🧂 <b>Ингредиенты</b>")
        for ing in recipe.ingredients:
            amount = ing.get("amount", "")
            lines.append(f"• {_esc(ing.get('name', ''))}" + (f" — <code>{_esc(amount)}</code>" if amount else ""))

    if recipe.instruction:
        lines.append("")
        lines.append("👨‍🍳 <b>Приготовление</b>")
        lines.append(_esc(recipe.instruction))

    if recipe.description:
        lines.append("")
        lines.append("📖 <b>Описание</b>")
        lines.append(_esc(recipe.description))

    await render(update, context, "\n".join(lines), item_detail_keyboard(recipe), message_id, parse_mode="HTML")
    return set_state(context, REFERENCE_DETAIL)


# =========================================================
# SEARCH, SHELF LIFE, CALLBACK, TEXT INPUT
# =========================================================
async def prompt_search(update, context, message_id=None):
    text = "🔍 <b>Поиск</b>\n\nВведите название, ингредиент или ключевое слово."
    await render(update, context, text, search_prompt_keyboard(), message_id, parse_mode="HTML")
    return set_state(context, REFERENCE_SEARCH_INPUT)


async def search_results(update, context, query: str, page: int = 1, message_id=None):
    index = get_search_index()
    results = index.search(query, limit=100)

    if not results:
        text = f"🔍 По запросу «{_esc(query)}» ничего не найдено.\n\nПопробуйте изменить ключевые слова."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Новый поиск", callback_data=CB_REF_SEARCH)],
            [InlineKeyboardButton("🏠 Меню", callback_data=CB_REF_HOME)]
        ])
        await render(update, context, text, kb, message_id, parse_mode="HTML")
        return set_state(context, REFERENCE_SEARCH_RESULTS)

    total = len(results)
    total_pages = _pages(total, SEARCH_PAGE_SIZE)
    page = max(1, min(page, total_pages))

    context.user_data["ref_search_query"] = query
    context.user_data["ref_last_view"] = ("search", query, page)

    start = (page - 1) * SEARCH_PAGE_SIZE
    page_items = results[start:start + SEARCH_PAGE_SIZE]

    text = f"🔍 <b>Результаты поиска</b>\n\nЗапрос: <code>{_esc(query)}</code>\nНайдено: {total}." + (f"\nСтраница {page}/{total_pages}." if total_pages > 1 else "")

    await render(update, context, text, search_results_keyboard(page_items, page, total_pages), message_id, parse_mode="HTML")
    return set_state(context, REFERENCE_SEARCH_RESULTS)


async def shelf_life_view(update, context, message_id=None):
    if not _shelf_life_items:
        await render(update, context, "📋 Сроки годности не загружены.", shelf_life_keyboard(), message_id)
        return set_state(context, REFERENCE_SHELF_LIFE)

    groups = {}
    for item in _shelf_life_items:
        groups.setdefault(item.category or "Прочее", []).append(item)

    lines = ["📅 <b>Сроки годности</b>", "", f"Всего позиций: {len(_shelf_life_items)}", ""]
    for cat in sorted(groups.keys()):
        lines.append(f"<b>{_esc(cat)}</b>")
        for item in sorted(groups[cat], key=lambda i: i.name.lower()):
            location = f" · {_esc(item.location)}" if item.location else ""
            lines.append(f"• {_esc(item.name)} — {item.shelf_life_days} дн.{location}")
        lines.append("")

    text = "\n".join(lines)
    if len(text) > 3900:
        text = text[:3900] + "\n…"

    await render(update, context, text, shelf_life_keyboard(), message_id, parse_mode="HTML")
    return set_state(context, REFERENCE_SHELF_LIFE)


# =========================================================
# CALLBACK ROUTER
# =========================================================
async def reference_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""
    message_id = query.message.message_id if query.message else None

    await answer(query)

    if data == "noop":
        return get_current_state(context)

    if data == CB_REF_BACK:
        try:
            from ..menu.handlers import show_main_menu
            return await show_main_menu(update, context, message_id)
        except Exception:
            return await show_reference_main(update, context, message_id)

    if data == CB_REF_HOME:
        return await show_reference_main(update, context, message_id)

    if data == CB_REF_BASE:
        return await show_base(update, context, message_id)

    if data == CB_REF_SEASON:
        return await show_season(update, context, message_id)

    if data == CB_REF_SEARCH:
        return await prompt_search(update, context, message_id)

    if data == CB_REF_SHELF_LIFE:
        return await shelf_life_view(update, context, message_id)

    if data == CB_REF_BACK_TO_LIST:
        last_view = context.user_data.get("ref_last_view")
        if last_view and last_view[0] == "category":
            _, source, category, page = last_view
            return await show_list(update, context, category, source, page, message_id)
        if last_view and last_view[0] == "search":
            _, query, page = last_view
            return await search_results(update, context, query, page, message_id)
        return await show_reference_main(update, context, message_id)

    if data.startswith(CB_REF_CATEGORY_PREFIX):
        parts = data.split(":", 1)[1]
        if ":" in parts:
            source, category = parts.split(":", 1)
        else:
            source, category = "base", parts
        if category == "all":
            return await show_base(update, context, message_id) if source == "base" else await show_season(update, context, message_id)
        return await show_list(update, context, category, source, 1, message_id)

    if data.startswith(CB_REF_ITEM_PREFIX):
        try:
            recipe_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            return await show_reference_main(update, context, message_id)
        return await show_detail(update, context, recipe_id, message_id)

    if data.startswith(CB_REF_PAGE_PREFIX):
        try:
            page = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            page = 1
        category = context.user_data.get("ref_category", "")
        source = context.user_data.get("ref_source", "base")
        if not category:
            return await show_base(update, context, message_id) if source == "base" else await show_season(update, context, message_id)
        return await show_list(update, context, category, source, page, message_id)

    if data.startswith(CB_REF_SEARCH_PAGE_PREFIX):
        try:
            page = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            page = 1
        query = context.user_data.get("ref_search_query", "")
        if not query:
            return await prompt_search(update, context, message_id)
        return await search_results(update, context, query, page, message_id)

    return await show_reference_main(update, context, message_id)


# =========================================================
# TEXT INPUT
# =========================================================
async def reference_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU_STATE

    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("⚠️ Введите ключевые слова для поиска.")
        return get_current_state(context)

    if text.lower() in {"-", "отмена", "✖️"}:
        return await show_reference_main(update, context, notice="Поиск отменён.")

    return await search_results(update, context, text)