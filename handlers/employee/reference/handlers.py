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
    CB_REF_BACK,
    CB_REF_HOME,
    CB_REF_SEARCH,
    CB_REF_SHELF_LIFE,
    CB_REF_CATEGORY_PREFIX,
    CB_REF_ITEM_PREFIX,
    CB_REF_PAGE_PREFIX,
    CB_REF_SEARCH_PAGE_PREFIX,
    CB_REF_BACK_TO_LIST,
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


# =========================================================
# BUILT-IN DATA
# =========================================================
_RECIPES_DATA = [
    # =====================================================
    # КОФЕ
    # =====================================================
    {
        "name": "Эспрессо",
        "category": "Кофе",
        "subcategory": "Классический",
        "volume": "0.2",
        "ingredients": [
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
        ],
        "instruction": (
            "Достаём холдер из входной группы кофемашины, протираем сито салфеткой насухо. "
            "Вставляем холдер в кронштейн кофемолки для эспрессо, смалываем в него кофе. "
            "Выравниваем кофейную таблетку, темперуем. "
            "Включаем «пустой» пролив на пару секунд для стабилизации температуры. "
            "Вставляем холдер в пазы входной группы, нажимаем пролив, подставляем питчер. "
            "Варим по рецепту: вес входа, вес выхода, время. "
            "Экстрагируем эспрессо в питчер, затем переливаем в подготовленный стакан."
        ),
        "description": "Концентрированный чёрный кофе, приготовленный под высоким давлением.",
        "shelf_life": None,
    },
    {
        "name": "Капучино 0.2",
        "category": "Кофе",
        "subcategory": "Горячий",
        "volume": "0.2",
        "ingredients": [
            {"name": "Кофе под эспрессо", "amount": "~8гр"},
            {"name": "Молоко", "amount": "150гр"},
        ],
        "instruction": (
            "Делаем эспрессо в стакан. Взбиваем молоко с расширением 30%. "
            "Вливаем молоко в стакан с эспрессо техникой латте-арт, накрываем крышкой."
        ),
        "description": "В меру крепкий напиток с добавлением взбитого горячего молока.",
        "shelf_life": None,
    },
    {
        "name": "Капучино 0.3",
        "category": "Кофе",
        "subcategory": "Горячий",
        "volume": "0.3",
        "ingredients": [
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Молоко", "amount": "220гр"},
        ],
        "instruction": (
            "Делаем эспрессо в стакан. Взбиваем молоко с расширением 30%. "
            "Вливаем молоко в стакан с эспрессо техникой латте-арт, накрываем крышкой."
        ),
        "description": "Классический капучино с более насыщенным кофейным вкусом.",
        "shelf_life": None,
    },
    {
        "name": "Латте 0.3",
        "category": "Кофе",
        "subcategory": "Горячий",
        "volume": "0.3",
        "ingredients": [
            {"name": "Кофе под эспрессо", "amount": "~8гр"},
            {"name": "Молоко", "amount": "220гр"},
        ],
        "instruction": (
            "Делаем эспрессо сразу в стакан. Взбиваем молоко. "
            "Заливаем его в стакан с эспрессо техникой латте-арт."
        ),
        "description": "Мягкий некрепкий кофе с большим количеством молока.",
        "shelf_life": None,
    },
    {
        "name": "Латте 0.4",
        "category": "Кофе",
        "subcategory": "Горячий",
        "volume": "0.4",
        "ingredients": [
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Молоко", "amount": "280гр"},
        ],
        "instruction": (
            "Делаем эспрессо сразу в стакан. Взбиваем молоко. "
            "Заливаем его в стакан с эспрессо техникой латте-арт."
        ),
        "description": "Большой латте для любителей молочных напитков.",
        "shelf_life": None,
    },
    {
        "name": "Флет 0.2",
        "category": "Кофе",
        "subcategory": "Горячий",
        "volume": "0.2",
        "ingredients": [
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Молоко", "amount": "150гр"},
        ],
        "instruction": (
            "Делаем эспрессо сразу в стакан. Взбиваем молоко с небольшим расширением (10%). "
            "Заливаем его в стакан с эспрессо техникой латте-арт."
        ),
        "description": "Крепкий кофе с молоком, отличается от капучино бóльшим количеством кофе.",
        "shelf_life": None,
    },
    {
        "name": "Ванильный раф 0.3",
        "category": "Кофе",
        "subcategory": "Горячий",
        "volume": "0.3",
        "ingredients": [
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Сливки 10%", "amount": "180гр"},
            {"name": "Ванильный сахар", "amount": "7гр"},
        ],
        "instruction": (
            "Делаем эспрессо. В питчер добавляем сливки, ванильный сахар и готовый эспрессо. "
            "Взбиваем с расширением 40%, наливаем в стакан."
        ),
        "description": "Десертный кофейный напиток на основе сливок и ванильного сахара.",
        "shelf_life": None,
    },
    {
        "name": "Гляссе 0.3",
        "category": "Кофе",
        "subcategory": "Горячий",
        "volume": "0.3",
        "ingredients": [
            {"name": "Фильтр", "amount": "200гр"},
            {"name": "Ванильное мороженое", "amount": "100гр"},
        ],
        "instruction": (
            "Стакан обдаём кипятком, кладём мороженое, затем наливаем фильтр по стенке стакана. "
            "Накрываем крышкой."
        ),
        "description": "Горячий чёрный кофе с добавлением мороженого.",
        "shelf_life": None,
    },
    {
        "name": "Американо 0.2",
        "category": "Кофе",
        "subcategory": "Горячий",
        "volume": "0.2",
        "ingredients": [
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Горячая вода", "amount": "~150гр"},
        ],
        "instruction": "В стакан наливаем горячую воду. Делаем эспрессо, переливаем его в воду.",
        "description": "Чёрный кофе на основе эспрессо, разбавленного горячей водой.",
        "shelf_life": None,
    },
    {
        "name": "Американо 0.3",
        "category": "Кофе",
        "subcategory": "Горячий",
        "volume": "0.3",
        "ingredients": [
            {"name": "Кофе под эспрессо", "amount": "~32гр"},
            {"name": "Горячая вода", "amount": "~230гр"},
        ],
        "instruction": "В стакан наливаем горячую воду. Делаем двойной эспрессо, переливаем его в воду.",
        "description": "Большой американо с двойной порцией эспрессо.",
        "shelf_life": None,
    },

    # =====================================================
    # МАТЧА И КАКАО
    # =====================================================
    {
        "name": "Матча-латте 0.3",
        "category": "Матча",
        "subcategory": "Горячий",
        "volume": "0.3",
        "ingredients": [
            {"name": "Матча", "amount": "3гр"},
            {"name": "Горячая вода", "amount": "30гр"},
            {"name": "Молоко", "amount": "220гр"},
        ],
        "instruction": (
            "Делаем матча-шот: матча + горячая вода, взбиваем капучинатором. "
            "Взбиваем молоко с небольшим расширением. "
            "Переливаем матча-шот через сито в стакан, заливаем молоком."
        ),
        "description": "Японский зелёный чай с молоком.",
        "shelf_life": None,
    },
    {
        "name": "Матча-латте 0.4",
        "category": "Матча",
        "subcategory": "Горячий",
        "volume": "0.4",
        "ingredients": [
            {"name": "Матча", "amount": "4гр"},
            {"name": "Горячая вода", "amount": "40гр"},
            {"name": "Молоко", "amount": "280гр"},
        ],
        "instruction": "Делаем матча-шот, взбиваем молоко, соединяем.",
        "description": "Большая порция матча-латте.",
        "shelf_life": None,
    },
    {
        "name": "Матча-тоник 0.3",
        "category": "Матча",
        "subcategory": "Холодный",
        "volume": "0.3",
        "ingredients": [
            {"name": "Матча", "amount": "3гр"},
            {"name": "Горячая вода", "amount": "30гр"},
            {"name": "Тоник биттер-лемон", "amount": "170гр"},
            {"name": "Сироп 'солёная карамель'", "amount": "5гр"},
            {"name": "Лимон", "amount": "долька"},
            {"name": "Лёд", "amount": "~100гр"},
        ],
        "instruction": (
            "В стакане смешиваем тоник и карамель, добавляем лимон. "
            "Делаем матча-шот, переливаем через сито сверху на тоник. Добавляем лёд."
        ),
        "description": "Освежающий цитрусовый тоник с матчей и карамелью.",
        "shelf_life": None,
    },
    {
        "name": "Какао 0.3",
        "category": "Какао",
        "subcategory": "Горячий",
        "volume": "0.3",
        "ingredients": [
            {"name": "Какао", "amount": "18гр"},
            {"name": "Ванильный сахар", "amount": "12гр"},
            {"name": "Молоко", "amount": "220гр"},
        ],
        "instruction": (
            "В питчер наливаем молоко, добавляем какао и ванильный сахар. "
            "Тщательно перемешиваем капучинатором. "
            "Взбиваем стимером с расширением как на капучино, греем до 60-65°С. Наливаем в стакан."
        ),
        "description": "Плотный, сбалансированный какао на основе натурального какао-порошка.",
        "shelf_life": None,
    },
    {
        "name": "Холодный какао 0.3",
        "category": "Какао",
        "subcategory": "Холодный",
        "volume": "0.3",
        "ingredients": [
            {"name": "Какао", "amount": "15гр"},
            {"name": "Ванильный сахар", "amount": "7гр"},
            {"name": "Горячая вода", "amount": "25гр"},
            {"name": "Молоко", "amount": "150гр"},
            {"name": "Лёд", "amount": "~100гр"},
        ],
        "instruction": (
            "Делаем какао-шот: какао + сахар + горячая вода, перемешиваем. "
            "В стакан со льдом наливаем молоко, сверху заливаем шот."
        ),
        "description": "Освежающий, плотный какао на молоке со льдом.",
        "shelf_life": None,
    },

    # =====================================================
    # ЧАИ
    # =====================================================
    {
        "name": "Дянь Хун Мао Фэн",
        "category": "Чай",
        "subcategory": "Красный",
        "volume": "0.3",
        "ingredients": [
            {"name": "Дянь Хун Мао Фэн", "amount": "6гр"},
            {"name": "Горячая вода", "amount": "~300гр"},
        ],
        "instruction": "Завариваем 3 минуты в типоде. Продуваем стакан паром, сливаем воду. Переливаем чай в стакан.",
        "description": "Красный китайский чай с мягким медовым оттенком.",
        "shelf_life": None,
    },
    {
        "name": "Эрл грей",
        "category": "Чай",
        "subcategory": "Чёрный",
        "volume": "0.3",
        "ingredients": [
            {"name": "Эрл грей", "amount": "7гр"},
            {"name": "Горячая вода", "amount": "~300гр"},
        ],
        "instruction": "Завариваем 3 минуты в типоде. Продуваем стакан паром, сливаем воду. Переливаем чай в стакан.",
        "description": "Бархатистый классический эрл грей с бергамотом.",
        "shelf_life": None,
    },
    {
        "name": "Кок чой",
        "category": "Чай",
        "subcategory": "Зелёный",
        "volume": "0.3",
        "ingredients": [
            {"name": "Кок чой", "amount": "3гр"},
            {"name": "Горячая вода", "amount": "~300гр"},
        ],
        "instruction": "Завариваем 3 минуты в типоде. Продуваем стакан паром, сливаем воду. Переливаем чай в стакан.",
        "description": "Узбекский зелёный чай с лимонной кислинкой и сладким послевкусием.",
        "shelf_life": None,
    },
    {
        "name": "Иван чай с малиной",
        "category": "Чай",
        "subcategory": "Травяной",
        "volume": "0.3",
        "ingredients": [
            {"name": "Иван чай с ферментированным листом малины", "amount": "5гр"},
            {"name": "Горячая вода", "amount": "~300гр"},
        ],
        "instruction": "Завариваем до 5 минут в типоде. Продуваем стакан паром, сливаем воду. Переливаем чай.",
        "description": "Травянистый иван-чай с ягодной нотой малинового листа.",
        "shelf_life": None,
    },
    {
        "name": "Гречишный чай (КуЦяо)",
        "category": "Чай",
        "subcategory": "Травяной",
        "volume": "0.3",
        "ingredients": [
            {"name": "Гречишный чай", "amount": "6гр"},
            {"name": "Горячая вода", "amount": "~300гр"},
        ],
        "instruction": "Завариваем до 5 минут в типоде. Продуваем стакан паром, сливаем воду. Переливаем чай.",
        "description": "Медово-карамельный тизан с послевкусием выпечки.",
        "shelf_life": None,
    },
    {
        "name": "Ананасовый пунш",
        "category": "Чай",
        "subcategory": "Авторский",
        "volume": "0.3",
        "ingredients": [
            {"name": "Дянь хун маофэн", "amount": "5гр"},
            {"name": "Пряный сироп", "amount": "3гр"},
            {"name": "Кленовый сироп", "amount": "5гр"},
            {"name": "Кордиал 'пряный ананас'", "amount": "5гр"},
            {"name": "Ананасовый сок", "amount": "70гр"},
            {"name": "Корица", "amount": "0,1гр"},
            {"name": "Апельсин", "amount": "долька"},
            {"name": "Горячая вода", "amount": "~200гр"},
        ],
        "instruction": (
            "Добавляем чай и корицу в типод, заливаем горячей водой, оставляем на 3 минуты. "
            "В питчере смешиваем сиропы, кордиал, сок и апельсин, прогреваем до 70°С. "
            "Переливаем в кружку, добавляем заваренный чай, перемешиваем."
        ),
        "description": "Ананасовый, согревающий, пряный пунш с кленовым сиропом.",
        "shelf_life": None,
    },

    # =====================================================
    # ХОЛОДНЫЙ КОФЕ
    # =====================================================
    {
        "name": "Холодный фильтр 0.3",
        "category": "Холодный кофе",
        "subcategory": "Чёрный",
        "volume": "0.3",
        "ingredients": [
            {"name": "Охлаждённый фильтр", "amount": "190гр"},
            {"name": "Лёд", "amount": "~100гр"},
        ],
        "instruction": "Аэрируем фильтр в бутылке, наливаем в стакан со льдом.",
        "description": "Холодный чёрный кофе на основе светлой обжарки.",
        "shelf_life": None,
    },
    {
        "name": "Эспрессо-тоник 0.3",
        "category": "Холодный кофе",
        "subcategory": "Чёрный",
        "volume": "0.3",
        "ingredients": [
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Тоник биттер-лемон", "amount": "170гр"},
            {"name": "Сироп 'солёная карамель'", "amount": "5гр"},
            {"name": "Лимон", "amount": "долька"},
            {"name": "Лёд", "amount": "~100гр"},
        ],
        "instruction": (
            "В стакан добавляем тоник и карамель, перемешиваем. Делаем эспрессо. "
            "Добавляем лёд и лимон в стакан, сверху заливаем эспрессо."
        ),
        "description": "Яркий кофейный тоник с цитрусовой нотой и карамелью.",
        "shelf_life": None,
    },
    {
        "name": "Холодный латте 0.3",
        "category": "Холодный кофе",
        "subcategory": "С молоком",
        "volume": "0.3",
        "ingredients": [
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Молоко", "amount": "170гр"},
            {"name": "Лёд", "amount": "~100гр"},
        ],
        "instruction": "Делаем эспрессо. В стакан наливаем молоко, добавляем лёд, затем эспрессо.",
        "description": "Классический холодный латте.",
        "shelf_life": None,
    },

    # =====================================================
    # ЛИМОНАДЫ И СМУЗИ
    # =====================================================
    {
        "name": "Дикая ягода 0.3",
        "category": "Лимонады",
        "subcategory": "С газом",
        "volume": "0.3",
        "ingredients": [
            {"name": "Настойка эрл грей", "amount": "50гр"},
            {"name": "Кизиловый соус", "amount": "3гр"},
            {"name": "Сироп 'гранат'", "amount": "5гр"},
            {"name": "Амаретто б/а", "amount": "10гр"},
            {"name": "Шиповничный концентрат", "amount": "40гр"},
            {"name": "Тоник биттер-лемон", "amount": "20гр"},
            {"name": "Содовая", "amount": "70гр"},
            {"name": "Апельсин", "amount": "долька"},
            {"name": "Барбарис", "amount": "до 2гр"},
            {"name": "Лёд", "amount": "~80гр"},
        ],
        "instruction": (
            "В питчере смешиваем настойку, шиповник, кизиловый соус, сироп и амаретто, тщательно перемешиваем. "
            "Переливаем в стакан, добавляем содовую и тоник, перемешиваем. "
            "Добавляем лёд, украшаем апельсином и барбарисом."
        ),
        "description": "Освежающий лимонад с цветочно-ягодным послевкусием.",
        "shelf_life": None,
    },
    {
        "name": "Смузи 'вместо завтрака' 0.3",
        "category": "Смузи",
        "subcategory": "Фруктово-ягодный",
        "volume": "0.3",
        "ingredients": [
            {"name": "Ежевика", "amount": "70гр"},
            {"name": "Чиа на молоке/на альте", "amount": "60гр"},
            {"name": "Греческий йогурт", "amount": "60гр"},
            {"name": "Банан", "amount": "70гр"},
            {"name": "Овсянка", "amount": "20гр"},
            {"name": "Вода", "amount": "80гр"},
        ],
        "instruction": "Смешиваем все ингредиенты в блендере, взбиваем пару минут. Переливаем в стакан.",
        "description": "Плотный йогуртовый смузи с семенами чиа, ежевикой, овсянкой и бананом.",
        "shelf_life": None,
    },

    # =====================================================
    # КОМПОТЫ
    # =====================================================
    {
        "name": "Компот на кофе 0.3",
        "category": "Компоты",
        "subcategory": "Горячий",
        "volume": "0.3",
        "ingredients": [
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Гречишная настойка", "amount": "100гр"},
            {"name": "Брусничный концентрат", "amount": "30гр"},
            {"name": "Персиковый сироп", "amount": "15гр"},
            {"name": "Мёд", "amount": "5гр"},
            {"name": "Горячая вода", "amount": "до 130гр"},
            {"name": "Апельсин", "amount": "долька"},
        ],
        "instruction": (
            "Делаем эспрессо. В питчере смешиваем гречишную настойку, апельсин, брусничный концентрат и персиковый сироп, греем до 70°С. "
            "Переливаем в стакан, доливаем горячую воду, добавляем мёд, перемешиваем. Добавляем эспрессо."
        ),
        "description": "Сладкий и плотный компот с ягодно-фруктовым профилем.",
        "shelf_life": None,
    },
    {
        "name": "Бабушкин компот 0.3",
        "category": "Компоты",
        "subcategory": "Горячий",
        "volume": "0.3",
        "ingredients": [
            {"name": "Гречишная настойка", "amount": "130гр"},
            {"name": "Персиковый сироп", "amount": "10гр"},
            {"name": "Гранатовый сироп", "amount": "10гр"},
            {"name": "Брусничный концентрат", "amount": "35гр"},
            {"name": "Мёд", "amount": "10гр"},
            {"name": "Горячая вода", "amount": "до 150гр"},
            {"name": "Апельсин", "amount": "долька"},
        ],
        "instruction": (
            "Смешиваем в питчере гречишную настойку, сиропы, апельсин и брусничный концентрат. Прогреваем до 70°С. "
            "В стакан наливаем горячую воду и мёд, добавляем заготовку, перемешиваем."
        ),
        "description": "Умеренная персиковая сладость и бруснично-вишнёвая кислотность.",
        "shelf_life": None,
    },

    # =====================================================
    # ЗАГОТОВКИ
    # =====================================================
    {
        "name": "Гречишная настойка",
        "category": "Заготовки",
        "subcategory": "Настойка",
        "volume": "400 мл",
        "ingredients": [
            {"name": "Гречишный чай", "amount": "20гр"},
            {"name": "Бадьян", "amount": "2гр"},
            {"name": "Корица молотая", "amount": "1гр"},
            {"name": "Имбирь молотый", "amount": "1гр"},
            {"name": "Горячая вода", "amount": "450гр"},
        ],
        "instruction": (
            "В кувшин добавляем гречишный чай, бадьян, корицу, имбирь, заливаем горячей водой. "
            "Настаиваем 30 минут, процеживаем через сито. Хранить в холодильнике 14 суток."
        ),
        "description": "Пряная основа для компотов и напитков.",
        "shelf_life": 14,
    },
    {
        "name": "Жасминовая настойка",
        "category": "Заготовки",
        "subcategory": "Настойка",
        "volume": "500 мл",
        "ingredients": [
            {"name": "Кок чой", "amount": "15гр"},
            {"name": "Жасмин бутоны", "amount": "7гр"},
            {"name": "Горячая вода", "amount": "500гр"},
        ],
        "instruction": (
            "В кувшин добавляем кок чой и жасминовые бутоны, заливаем горячей водой. "
            "Настаиваем 15 минут, процеживаем. Хранить в холодильнике 14 суток."
        ),
        "description": "Цветочная настойка для лимонадов и кофейных напитков.",
        "shelf_life": 14,
    },
    {
        "name": "Иванова настойка",
        "category": "Заготовки",
        "subcategory": "Настойка",
        "volume": "500 мл",
        "ingredients": [
            {"name": "Иван-чай с фермент. листом малины", "amount": "20гр"},
            {"name": "Горячая вода", "amount": "550гр"},
        ],
        "instruction": (
            "В кувшин добавляем иван-чай, заливаем горячей водой. "
            "Настаиваем 30 минут, процеживаем. Хранить в холодильнике 14 суток."
        ),
        "description": "Травянистая настойка с ягодными нотками.",
        "shelf_life": 14,
    },
]


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
    ("Киш с курицей, сыром фета и шпинатом", "Сытное", "молочное", 3),
    ("Салат с курицей", "Сытное", "молочное", 3),
    ("Драники", "Сытное", "НЕмолочное", 4),
]


# =========================================================
# DATA BUILDERS
# =========================================================
def _build_recipes_list() -> List[Recipe]:
    """
    Возвращает список всех встроенных рецептов.
    """
    return [Recipe(**data) for data in _RECIPES_DATA]


def _build_shelf_life_items() -> List[ShelfLifeItem]:
    """
    Возвращает список сроков годности.
    """
    items = []

    for index, (name, category, subcategory, days) in enumerate(_SHELF_ITEMS_DATA, start=1):
        items.append(
            ShelfLifeItem(
                id=index,
                name=name,
                category=category,
                subcategory=subcategory,
                shelf_life_days=days,
                location="Витрина",
            )
        )

    return items


def load_recipes_from_excel() -> None:
    """
    Загружает встроенные данные справочника.
    Название сохранено для совместимости.
    """
    global _shelf_life_items

    index = reset_search_index()

    recipes = _build_recipes_list()

    for recipe in recipes:
        index.add_recipe(recipe)

    shelf_items = _build_shelf_life_items()
    existing_names = {item.name.lower() for item in shelf_items}

    next_id = len(shelf_items) + 1

    for recipe in recipes:
        if not recipe.shelf_life:
            continue

        if recipe.name.lower() in existing_names:
            continue

        shelf_items.append(
            ShelfLifeItem(
                id=next_id,
                name=recipe.name,
                category=recipe.category,
                subcategory=recipe.subcategory,
                shelf_life_days=recipe.shelf_life,
                location="",
            )
        )

        existing_names.add(recipe.name.lower())
        next_id += 1

    _shelf_life_items = sorted(
        shelf_items,
        key=lambda item: ((item.category or "").lower(), item.name.lower()),
    )

    logger.info("Загружено рецептов: %s", len(index.recipes))
    logger.info("Загружено позиций сроков годности: %s", len(_shelf_life_items))


# =========================================================
# SCREENS
# =========================================================
async def show_reference_main(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    """
    Главное меню справочника.
    """
    index = get_search_index()

    total_recipes = len(index.recipes)
    total_categories = len(index.get_all_categories())
    total_shelf = len(_shelf_life_items)

    text = (
        "📖 <b>Справочник</b>\n\n"
        "Рецепты, техкарты и сроки годности.\n\n"
        f"• Рецептов: {total_recipes}\n"
        f"• Категорий: {total_categories}\n"
        f"• Позиций сроков: {total_shelf}"
    )

    if notice:
        text = f"{notice}\n\n{text}"

    await render(
        update,
        context,
        text,
        reference_main_keyboard(),
        message_id,
        parse_mode="HTML",
    )

    return set_state(context, REFERENCE_MAIN)


async def show_categories(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
) -> int:
    """
    Показывает список категорий.
    """
    category_counts = get_category_counts()

    if not category_counts:
        text = "📂 Категории пока не загружены."

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🏠 Меню справочника",
                        callback_data=CB_REF_HOME,
                    )
                ]
            ]
        )

        await render(update, context, text, keyboard, message_id)
        return set_state(context, REFERENCE_CATEGORY)

    text = (
        "📂 <b>Категории</b>\n\n"
        "Выберите раздел."
    )

    await render(
        update,
        context,
        text,
        categories_keyboard(category_counts),
        message_id,
        parse_mode="HTML",
    )

    return set_state(context, REFERENCE_CATEGORY)


async def show_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    category: str,
    page: int = 1,
    message_id: int | None = None,
) -> int:
    """
    Показывает список рецептов в категории.
    """
    index = get_search_index()
    recipes = index.get_by_category(category)

    if not recipes:
        text = f"В категории «{category}» нет рецептов."

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📂 Категории",
                        callback_data=f"{CB_REF_CATEGORY_PREFIX}all",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 Меню справочника",
                        callback_data=CB_REF_HOME,
                    )
                ],
            ]
        )

        await render(update, context, text, keyboard, message_id)
        return set_state(context, REFERENCE_LIST)

    total = len(recipes)
    total_pages = _pages(total, PAGE_SIZE)

    page = max(1, min(page, total_pages))

    context.user_data["ref_category"] = category
    context.user_data["ref_page"] = page
    context.user_data["ref_last_view"] = ("category", category, page)

    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE

    page_items = recipes[start:end]

    text = (
        f"📂 <b>{_esc(category)}</b>\n\n"
        f"Найдено: {total} рецептов."
    )

    if total_pages > 1:
        text += f"\nСтраница {page}/{total_pages}."

    await render(
        update,
        context,
        text,
        items_list_keyboard(
            items=page_items,
            category=category,
            page=page,
            total_pages=total_pages,
        ),
        message_id,
        parse_mode="HTML",
    )

    return set_state(context, REFERENCE_LIST)


async def show_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    recipe_id: int,
    message_id: int | None = None,
) -> int:
    """
    Показывает карточку рецепта.
    """
    index = get_search_index()
    recipe = index.get_recipe(recipe_id)

    if not recipe:
        text = "⚠️ Рецепт не найден."

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🏠 Меню справочника",
                        callback_data=CB_REF_HOME,
                    )
                ]
            ]
        )

        await render(update, context, text, keyboard, message_id)
        return set_state(context, REFERENCE_DETAIL)

    lines = [
        f"🍹 <b>{_esc(recipe.name)}</b>",
    ]

    category_line = f"📂 {_esc(recipe.category)}"

    if recipe.subcategory:
        category_line += f" · {_esc(recipe.subcategory)}"

    lines.append(category_line)
    lines.append("")

    if recipe.volume:
        lines.append(f"📐 Объём: {_esc(recipe.volume)}")

    if recipe.shelf_life:
        lines.append(f"📅 Срок годности: {recipe.shelf_life} дн.")

    if recipe.ingredients:
        lines.append("")
        lines.append("🧂 <b>Ингредиенты</b>")

        for ingredient in recipe.ingredients:
            name = ingredient.get("name", "")
            amount = ingredient.get("amount", "")

            if amount:
                lines.append(
                    f"• {_esc(name)} — <code>{_esc(amount)}</code>"
                )
            else:
                lines.append(f"• {_esc(name)}")

    if recipe.instruction:
        lines.append("")
        lines.append("👨‍🍳 <b>Приготовление</b>")
        lines.append(_esc(recipe.instruction))

    if recipe.description:
        lines.append("")
        lines.append("📖 <b>Описание</b>")
        lines.append(_esc(recipe.description))

    text = "\n".join(lines)

    await render(
        update,
        context,
        text,
        item_detail_keyboard(recipe),
        message_id,
        parse_mode="HTML",
    )

    return set_state(context, REFERENCE_DETAIL)


async def prompt_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
) -> int:
    """
    Запрашивает поисковый запрос у пользователя.
    """
    text = (
        "🔍 <b>Поиск</b>\n\n"
        "Введите название, ингредиент или ключевое слово.\n"
        "Например: капучино, молоко, лимон."
    )

    await render(
        update,
        context,
        text,
        search_prompt_keyboard(),
        message_id,
        parse_mode="HTML",
    )

    return set_state(context, REFERENCE_SEARCH_INPUT)


async def search_results(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query: str,
    page: int = 1,
    message_id: int | None = None,
) -> int:
    """
    Показывает результаты поиска.
    """
    index = get_search_index()

    results = index.search(query, limit=100)

    if not results:
        text = (
            f"🔍 По запросу «{_esc(query)}» ничего не найдено.\n\n"
            "Попробуйте изменить ключевые слова."
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔍 Новый поиск",
                        callback_data=CB_REF_SEARCH,
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 Меню справочника",
                        callback_data=CB_REF_HOME,
                    )
                ],
            ]
        )

        await render(update, context, text, keyboard, message_id, parse_mode="HTML")
        return set_state(context, REFERENCE_SEARCH_RESULTS)

    total = len(results)
    total_pages = _pages(total, SEARCH_PAGE_SIZE)

    page = max(1, min(page, total_pages))

    context.user_data["ref_search_query"] = query
    context.user_data["ref_last_view"] = ("search", query, page)

    start = (page - 1) * SEARCH_PAGE_SIZE
    end = start + SEARCH_PAGE_SIZE

    page_items = results[start:end]

    text = (
        "🔍 <b>Результаты поиска</b>\n\n"
        f"Запрос: <code>{_esc(query)}</code>\n"
        f"Найдено: {total}."
    )

    if total_pages > 1:
        text += f"\nСтраница {page}/{total_pages}."

    await render(
        update,
        context,
        text,
        search_results_keyboard(
            items=page_items,
            page=page,
            total_pages=total_pages,
        ),
        message_id,
        parse_mode="HTML",
    )

    return set_state(context, REFERENCE_SEARCH_RESULTS)


async def shelf_life_view(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
) -> int:
    """
    Показывает сроки годности продуктов.
    """
    if not _shelf_life_items:
        text = "📋 Сроки годности не загружены."

        await render(
            update,
            context,
            text,
            shelf_life_keyboard(),
            message_id,
        )

        return set_state(context, REFERENCE_SHELF_LIFE)

    groups = {}

    for item in _shelf_life_items:
        category = item.category or "Прочее"
        groups.setdefault(category, []).append(item)

    lines = [
        "📅 <b>Сроки годности</b>",
        "",
        f"Всего позиций: {len(_shelf_life_items)}",
        "",
    ]

    for category in sorted(groups.keys()):
        items = sorted(
            groups[category],
            key=lambda item: item.name.lower(),
        )

        lines.append(f"<b>{_esc(category)}</b>")

        for item in items:
            location = f" · {_esc(item.location)}" if item.location else ""
            lines.append(
                f"• {_esc(item.name)} — {item.shelf_life_days} дн.{location}"
            )

        lines.append("")

    text = "\n".join(lines)

    if len(text) > 3900:
        text = text[:3900] + "\n…"

    await render(
        update,
        context,
        text,
        shelf_life_keyboard(),
        message_id,
        parse_mode="HTML",
    )

    return set_state(context, REFERENCE_SHELF_LIFE)


# =========================================================
# CALLBACK ROUTER
# =========================================================
async def reference_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает callback-запросы справочника.
    """
    query = update.callback_query
    data = query.data or ""
    message_id = query.message.message_id if query.message else None

    await answer(query)

    if data == "noop":
        return get_current_state(context)

    # Выход в главное меню бота
    if data == CB_REF_BACK:
        try:
            from ..menu.handlers import show_main_menu

            return await show_main_menu(update, context, message_id)
        except Exception:
            return await show_reference_main(update, context, message_id)

    # Домой в справочник
    if data == CB_REF_HOME:
        return await show_reference_main(update, context, message_id)

    # Поиск
    if data == CB_REF_SEARCH:
        return await prompt_search(update, context, message_id)

    # Сроки годности
    if data == CB_REF_SHELF_LIFE:
        return await shelf_life_view(update, context, message_id)

    # Назад: категория или поиск
    if data == CB_REF_BACK_TO_LIST:
        last_view = context.user_data.get("ref_last_view")

        if last_view and last_view[0] == "category":
            category = last_view[1]
            page = last_view[2]

            return await show_list(update, context, category, page, message_id)

        if last_view and last_view[0] == "search":
            query = last_view[1]
            page = last_view[2]

            return await search_results(update, context, query, page, message_id)

        return await show_reference_main(update, context, message_id)

    # Категории
    if data.startswith(CB_REF_CATEGORY_PREFIX):
        category = data.split(":", 1)[1]

        if category == "all":
            return await show_categories(update, context, message_id)

        return await show_list(update, context, category, 1, message_id)

    # Деталь рецепта
    if data.startswith(CB_REF_ITEM_PREFIX):
        try:
            recipe_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            return await show_reference_main(update, context, message_id)

        return await show_detail(update, context, recipe_id, message_id)

    # Пагинация категории
    if data.startswith(CB_REF_PAGE_PREFIX):
        try:
            page = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            page = 1

        category = context.user_data.get("ref_category", "")

        if not category:
            return await show_categories(update, context, message_id)

        return await show_list(update, context, category, page, message_id)

    # Пагинация поиска
    if data.startswith(CB_REF_SEARCH_PAGE_PREFIX):
        try:
            page = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            page = 1

        query = context.user_data.get("ref_search_query", "")

        if not query:
            return await prompt_search(update, context, message_id)

        return await search_results(update, context, query, page, message_id)

    # Fallback
    return await show_reference_main(update, context, message_id)


# =========================================================
# TEXT INPUT
# =========================================================
async def reference_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает текстовый поисковый запрос.
    """
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