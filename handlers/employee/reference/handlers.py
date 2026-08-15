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
    tokenize, get_categories,
)

from ..menu.utils import render, answer, set_state, get_current_state

logger = logging.getLogger(__name__)
MAIN_MENU_STATE = 3

# Глобальный кэш для сроков годности
_shelf_life_items: List[ShelfLifeItem] = []


# =========================================================
# ВСТРОЕННЫЕ ДАННЫЕ РЕЦЕПТОВ
# =========================================================

def _build_recipes_list() -> List[Recipe]:
    """Возвращает список всех рецептов, встроенных в код."""
    recipes = []

    # ----- КОФЕ -----
    recipes.append(Recipe(
        name="Эспрессо",
        category="Кофе",
        subcategory="Классический",
        volume="0.2",
        ingredients=[{"name": "Кофе под эспрессо", "amount": "~16гр"}],
        instruction=(
            "Достаём холдер из входной группы кофемашины, протираем сито салфеткой насухо. "
            "Вставляем холдер в кронштейн кофемолки для эспрессо, смалываем в него кофе. "
            "Выравниваем кофейную таблетку, темперуем. "
            "Включаем «пустой» пролив на пару секунд для стабилизации температуры. "
            "Вставляем холдер в пазы входной группы, нажимаем пролив, подставляем питчер. "
            "Варим по рецепту: вес входа, вес выхода, время. "
            "Экстрагируем эспрессо в питчер, затем переливаем в подготовленный стакан."
        ),
        description="Концентрированный чёрный кофе, приготовленный под высоким давлением."
    ))

    recipes.append(Recipe(
        name="Капучино 0.2",
        category="Кофе",
        subcategory="Горячий",
        volume="0.2",
        ingredients=[
            {"name": "Кофе под эспрессо", "amount": "~8гр"},
            {"name": "Молоко", "amount": "150гр"}
        ],
        instruction="Делаем эспрессо в стакан. Взбиваем молоко с расширением 30%. Вливаем молоко в стакан с эспрессо техникой латте-арт, накрываем крышкой.",
        description="В меру крепкий напиток с добавлением взбитого горячего молока."
    ))

    recipes.append(Recipe(
        name="Капучино 0.3",
        category="Кофе",
        subcategory="Горячий",
        volume="0.3",
        ingredients=[
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Молоко", "amount": "220гр"}
        ],
        instruction="Делаем эспрессо в стакан. Взбиваем молоко с расширением 30%. Вливаем молоко в стакан с эспрессо техникой латте-арт, накрываем крышкой.",
        description="Классический капучино с более насыщенным кофейным вкусом."
    ))

    recipes.append(Recipe(
        name="Латте 0.3",
        category="Кофе",
        subcategory="Горячий",
        volume="0.3",
        ingredients=[
            {"name": "Кофе под эспрессо", "amount": "~8гр"},
            {"name": "Молоко", "amount": "220гр"}
        ],
        instruction="Делаем эспрессо сразу в стакан. Взбиваем молоко. Заливаем его в стакан с эспрессо техникой латте-арт.",
        description="Мягкий некрепкий кофе с большим количеством молока."
    ))

    recipes.append(Recipe(
        name="Латте 0.4",
        category="Кофе",
        subcategory="Горячий",
        volume="0.4",
        ingredients=[
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Молоко", "amount": "280гр"}
        ],
        instruction="Делаем эспрессо сразу в стакан. Взбиваем молоко. Заливаем его в стакан с эспрессо техникой латте-арт.",
        description="Большой латте для любителей молочных напитков."
    ))

    recipes.append(Recipe(
        name="Флет 0.2",
        category="Кофе",
        subcategory="Горячий",
        volume="0.2",
        ingredients=[
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Молоко", "amount": "150гр"}
        ],
        instruction="Делаем эспрессо сразу в стакан. Взбиваем молоко с небольшим расширением (10%). Заливаем его в стакан с эспрессо техникой латте-арт.",
        description="Крепкий кофе с молоком, отличается от капучино бóльшим количеством кофе."
    ))

    recipes.append(Recipe(
        name="Ванильный раф 0.3",
        category="Кофе",
        subcategory="Горячий",
        volume="0.3",
        ingredients=[
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Сливки 10%", "amount": "180гр"},
            {"name": "Ванильный сахар", "amount": "7гр"}
        ],
        instruction="Делаем эспрессо. В питчер добавляем сливки, ванильный сахар и готовый эспрессо. Взбиваем с расширением 40%, наливаем в стакан.",
        description="Десертный кофейный напиток на основе сливок и ванильного сахара."
    ))

    recipes.append(Recipe(
        name="Гляссе 0.3",
        category="Кофе",
        subcategory="Горячий",
        volume="0.3",
        ingredients=[
            {"name": "Фильтр", "amount": "200гр"},
            {"name": "Ванильное мороженое", "amount": "100гр"}
        ],
        instruction="Стакан обдаём кипятком, кладём мороженое, затем наливаем фильтр по стенке стакана. Накрываем крышкой.",
        description="Горячий чёрный кофе с добавлением мороженого."
    ))

    recipes.append(Recipe(
        name="Американо 0.2",
        category="Кофе",
        subcategory="Горячий",
        volume="0.2",
        ingredients=[
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Горячая вода", "amount": "~150гр"}
        ],
        instruction="В стакан наливаем горячую воду. Делаем эспрессо, переливаем его в воду.",
        description="Чёрный кофе на основе эспрессо, разбавленного горячей водой."
    ))

    recipes.append(Recipe(
        name="Американо 0.3",
        category="Кофе",
        subcategory="Горячий",
        volume="0.3",
        ingredients=[
            {"name": "Кофе под эспрессо", "amount": "~32гр"},
            {"name": "Горячая вода", "amount": "~230гр"}
        ],
        instruction="В стакан наливаем горячую воду. Делаем двойной эспрессо, переливаем его в воду.",
        description="Большой американо с двойной порцией эспрессо."
    ))

    # ----- МАТЧА И КАКАО -----
    recipes.append(Recipe(
        name="Матча-латте 0.3",
        category="Матча",
        subcategory="Горячий",
        volume="0.3",
        ingredients=[
            {"name": "Матча", "amount": "3гр"},
            {"name": "Горячая вода", "amount": "30гр"},
            {"name": "Молоко", "amount": "220гр"}
        ],
        instruction="Делаем матча-шот: матча + горячая вода, взбиваем капучинатором. Взбиваем молоко с небольшим расширением. Переливаем матча-шот через сито в стакан, заливаем молоком.",
        description="Японский зелёный чай с молоком."
    ))

    recipes.append(Recipe(
        name="Матча-латте 0.4",
        category="Матча",
        subcategory="Горячий",
        volume="0.4",
        ingredients=[
            {"name": "Матча", "amount": "4гр"},
            {"name": "Горячая вода", "amount": "40гр"},
            {"name": "Молоко", "amount": "280гр"}
        ],
        instruction="Делаем матча-шот, взбиваем молоко, соединяем.",
        description="Большая порция матча-латте."
    ))

    recipes.append(Recipe(
        name="Матча-тоник 0.3",
        category="Матча",
        subcategory="Холодный",
        volume="0.3",
        ingredients=[
            {"name": "Матча", "amount": "3гр"},
            {"name": "Горячая вода", "amount": "30гр"},
            {"name": "Тоник биттер-лемон", "amount": "170гр"},
            {"name": "Сироп 'солёная карамель'", "amount": "5гр"},
            {"name": "Лимон", "amount": "долька"},
            {"name": "Лёд", "amount": "~100гр"}
        ],
        instruction="В стакане смешиваем тоник и карамель, добавляем лимон. Делаем матча-шот, переливаем через сито сверху на тоник. Добавляем лёд.",
        description="Освежающий цитрусовый тоник с матчей и карамелью."
    ))

    recipes.append(Recipe(
        name="Какао 0.3",
        category="Какао",
        subcategory="Горячий",
        volume="0.3",
        ingredients=[
            {"name": "Какао", "amount": "18гр"},
            {"name": "Ванильный сахар", "amount": "12гр"},
            {"name": "Молоко", "amount": "220гр"}
        ],
        instruction="В питчер наливаем молоко, добавляем какао и ванильный сахар. Тщательно перемешиваем капучинатором. Взбиваем стимером с расширением как на капучино, греем до 60-65°С. Наливаем в стакан.",
        description="Плотный, сбалансированный какао на основе натурального какао-порошка."
    ))

    recipes.append(Recipe(
        name="Холодный какао 0.3",
        category="Какао",
        subcategory="Холодный",
        volume="0.3",
        ingredients=[
            {"name": "Какао", "amount": "15гр"},
            {"name": "Ванильный сахар", "amount": "7гр"},
            {"name": "Горячая вода", "amount": "25гр"},
            {"name": "Молоко", "amount": "150гр"},
            {"name": "Лёд", "amount": "~100гр"}
        ],
        instruction="Делаем какао-шот: какао + сахар + горячая вода, перемешиваем. В стакан со льдом наливаем молоко, сверху заливаем шот.",
        description="Освежающий, плотный какао на молоке со льдом."
    ))

    # ----- ЧАИ -----
    recipes.append(Recipe(
        name="Дянь Хун Мао Фэн",
        category="Чай",
        subcategory="Красный",
        volume="0.3",
        ingredients=[
            {"name": "Дянь Хун Мао Фэн", "amount": "6гр"},
            {"name": "Горячая вода", "amount": "~300гр"}
        ],
        instruction="Завариваем 3 минуты в типоде. Продуваем стакан паром, сливаем воду. Переливаем чай в стакан.",
        description="Красный китайский чай с мягким медовым оттенком."
    ))

    recipes.append(Recipe(
        name="Эрл грей",
        category="Чай",
        subcategory="Чёрный",
        volume="0.3",
        ingredients=[
            {"name": "Эрл грей", "amount": "7гр"},
            {"name": "Горячая вода", "amount": "~300гр"}
        ],
        instruction="Завариваем 3 минуты в типоде. Продуваем стакан паром, сливаем воду. Переливаем чай в стакан.",
        description="Бархатистый классический эрл грей с бергамотом."
    ))

    recipes.append(Recipe(
        name="Кок чой",
        category="Чай",
        subcategory="Зелёный",
        volume="0.3",
        ingredients=[
            {"name": "Кок чой", "amount": "3гр"},
            {"name": "Горячая вода", "amount": "~300гр"}
        ],
        instruction="Завариваем 3 минуты в типоде. Продуваем стакан паром, сливаем воду. Переливаем чай в стакан.",
        description="Узбекский зелёный чай с лимонной кислинкой и сладким послевкусием."
    ))

    recipes.append(Recipe(
        name="Иван чай с малиной",
        category="Чай",
        subcategory="Травяной",
        volume="0.3",
        ingredients=[
            {"name": "Иван чай с ферментированным листом малины", "amount": "5гр"},
            {"name": "Горячая вода", "amount": "~300гр"}
        ],
        instruction="Завариваем до 5 минут в типоде. Продуваем стакан паром, сливаем воду. Переливаем чай.",
        description="Травянистый иван-чай с ягодной нотой малинового листа."
    ))

    recipes.append(Recipe(
        name="Гречишный чай (КуЦяо)",
        category="Чай",
        subcategory="Травяной",
        volume="0.3",
        ingredients=[
            {"name": "Гречишный чай", "amount": "6гр"},
            {"name": "Горячая вода", "amount": "~300гр"}
        ],
        instruction="Завариваем до 5 минут в типоде. Продуваем стакан паром, сливаем воду. Переливаем чай.",
        description="Медово-карамельный тизан с послевкусием выпечки."
    ))

    recipes.append(Recipe(
        name="Ананасовый пунш",
        category="Чай",
        subcategory="Авторский",
        volume="0.3",
        ingredients=[
            {"name": "Дянь хун маофэн", "amount": "5гр"},
            {"name": "Пряный сироп", "amount": "3гр"},
            {"name": "Кленовый сироп", "amount": "5гр"},
            {"name": "Кордиал 'пряный ананас'", "amount": "5гр"},
            {"name": "Ананасовый сок", "amount": "70гр"},
            {"name": "Корица", "amount": "0,1гр"},
            {"name": "Апельсин", "amount": "долька"},
            {"name": "Горячая вода", "amount": "~200гр"}
        ],
        instruction="Добавляем чай и корицу в типод, заливаем горячей водой, оставляем на 3 минуты. В питчере смешиваем сиропы, кордиал, сок и апельсин, прогреваем до 70°С. Переливаем в кружку, добавляем заваренный чай, перемешиваем.",
        description="Ананасовый, согревающий, пряный пунш с кленовым сиропом."
    ))

    # ----- ХОЛОДНЫЙ КОФЕ -----
    recipes.append(Recipe(
        name="Холодный фильтр 0.3",
        category="Холодный кофе",
        subcategory="Чёрный",
        volume="0.3",
        ingredients=[
            {"name": "Охлаждённый фильтр", "amount": "190гр"},
            {"name": "Лёд", "amount": "~100гр"}
        ],
        instruction="Аэрируем фильтр в бутылке, наливаем в стакан со льдом.",
        description="Холодный чёрный кофе на основе светлой обжарки."
    ))

    recipes.append(Recipe(
        name="Эспрессо-тоник 0.3",
        category="Холодный кофе",
        subcategory="Чёрный",
        volume="0.3",
        ingredients=[
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Тоник биттер-лемон", "amount": "170гр"},
            {"name": "Сироп 'солёная карамель'", "amount": "5гр"},
            {"name": "Лимон", "amount": "долька"},
            {"name": "Лёд", "amount": "~100гр"}
        ],
        instruction="В стакан добавляем тоник и карамель, перемешиваем. Делаем эспрессо. Добавляем лёд и лимон в стакан, сверху заливаем эспрессо.",
        description="Яркий кофейный тоник с цитрусовой нотой и карамелью."
    ))

    recipes.append(Recipe(
        name="Холодный латте 0.3",
        category="Холодный кофе",
        subcategory="С молоком",
        volume="0.3",
        ingredients=[
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Молоко", "amount": "170гр"},
            {"name": "Лёд", "amount": "~100гр"}
        ],
        instruction="Делаем эспрессо. В стакан наливаем молоко, добавляем лёд, затем эспрессо.",
        description="Классический холодный латте."
    ))

    # ----- ЛИМОНАДЫ И СМУЗИ -----
    recipes.append(Recipe(
        name="Дикая ягода 0.3",
        category="Лимонады",
        subcategory="С газом",
        volume="0.3",
        ingredients=[
            {"name": "Настойка эрл грей", "amount": "50гр"},
            {"name": "Кизиловый соус", "amount": "3гр"},
            {"name": "Сироп 'гранат'", "amount": "5гр"},
            {"name": "Амаретто б/а", "amount": "10гр"},
            {"name": "Шиповничный концентрат", "amount": "40гр"},
            {"name": "Тоник биттер-лемон", "amount": "20гр"},
            {"name": "Содовая", "amount": "70гр"},
            {"name": "Апельсин", "amount": "долька"},
            {"name": "Барбарис", "amount": "до 2гр"},
            {"name": "Лёд", "amount": "~80гр"}
        ],
        instruction="В питчере смешиваем настойку, шиповник, кизиловый соус, сироп и амаретто, тщательно перемешиваем. Переливаем в стакан, добавляем содовую и тоник, перемешиваем. Добавляем лёд, украшаем апельсином и барбарисом.",
        description="Освежающий лимонад с цветочно-ягодным послевкусием."
    ))

    recipes.append(Recipe(
        name="Смузи 'вместо завтрака' 0.3",
        category="Смузи",
        subcategory="Фруктово-ягодный",
        volume="0.3",
        ingredients=[
            {"name": "Ежевика", "amount": "70гр"},
            {"name": "Чиа на молоке/на альте", "amount": "60гр"},
            {"name": "Греческий йогурт", "amount": "60гр"},
            {"name": "Банан", "amount": "70гр"},
            {"name": "Овсянка", "amount": "20гр"},
            {"name": "Вода", "amount": "80гр"}
        ],
        instruction="Смешиваем все ингредиенты в блендере, взбиваем пару минут. Переливаем в стакан.",
        description="Плотный йогуртовый смузи с семенами чиа, ежевикой, овсянкой и бананом."
    ))

    # ----- КОМПОТЫ (авторские) -----
    recipes.append(Recipe(
        name="Компот на кофе 0.3",
        category="Компоты",
        subcategory="Горячий",
        volume="0.3",
        ingredients=[
            {"name": "Кофе под эспрессо", "amount": "~16гр"},
            {"name": "Гречишная настойка", "amount": "100гр"},
            {"name": "Брусничный концентрат", "amount": "30гр"},
            {"name": "Персиковый сироп", "amount": "15гр"},
            {"name": "Мёд", "amount": "5гр"},
            {"name": "Горячая вода", "amount": "до 130гр"},
            {"name": "Апельсин", "amount": "долька"}
        ],
        instruction="Делаем эспрессо. В питчере смешиваем гречишную настойку, апельсин, брусничный концентрат и персиковый сироп, греем до 70°С. Переливаем в стакан, доливаем горячую воду, добавляем мёд, перемешиваем. Добавляем эспрессо.",
        description="Сладкий и плотный компот с ягодно-фруктовым профилем."
    ))

    recipes.append(Recipe(
        name="Бабушкин компот 0.3",
        category="Компоты",
        subcategory="Горячий",
        volume="0.3",
        ingredients=[
            {"name": "Гречишная настойка", "amount": "130гр"},
            {"name": "Персиковый сироп", "amount": "10гр"},
            {"name": "Гранатовый сироп", "amount": "10гр"},
            {"name": "Брусничный концентрат", "amount": "35гр"},
            {"name": "Мёд", "amount": "10гр"},
            {"name": "Горячая вода", "amount": "до 150гр"},
            {"name": "Апельсин", "amount": "долька"}
        ],
        instruction="Смешиваем в питчере гречишную настойку, сиропы, апельсин и брусничный концентрат. Прогреваем до 70°С. В стакан наливаем горячую воду и мёд, добавляем заготовку, перемешиваем.",
        description="Умеренная персиковая сладость и бруснично-вишнёвая кислотность."
    ))

    # ----- ЗАГОТОВКИ (настойки) -----
    recipes.append(Recipe(
        name="Гречишная настойка",
        category="Заготовки",
        subcategory="Настойка",
        volume="400 мл",
        ingredients=[
            {"name": "Гречишный чай", "amount": "20гр"},
            {"name": "Бадьян", "amount": "2гр"},
            {"name": "Корица молотая", "amount": "1гр"},
            {"name": "Имбирь молотый", "amount": "1гр"},
            {"name": "Горячая вода", "amount": "450гр"}
        ],
        instruction="В кувшин добавляем гречишный чай, бадьян, корицу, имбирь, заливаем горячей водой. Настаиваем 30 минут, процеживаем через сито. Хранить в холодильнике 14 суток.",
        description="Пряная основа для компотов и напитков.",
        shelf_life=14
    ))

    recipes.append(Recipe(
        name="Жасминовая настойка",
        category="Заготовки",
        subcategory="Настойка",
        volume="500 мл",
        ingredients=[
            {"name": "Кок чой", "amount": "15гр"},
            {"name": "Жасмин бутоны", "amount": "7гр"},
            {"name": "Горячая вода", "amount": "500гр"}
        ],
        instruction="В кувшин добавляем кок чой и жасминовые бутоны, заливаем горячей водой. Настаиваем 15 минут, процеживаем. Хранить в холодильнике 14 суток.",
        description="Цветочная настойка для лимонадов и кофейных напитков.",
        shelf_life=14
    ))

    recipes.append(Recipe(
        name="Иванова настойка",
        category="Заготовки",
        subcategory="Настойка",
        volume="500 мл",
        ingredients=[
            {"name": "Иван-чай с фермент. листом малины", "amount": "20гр"},
            {"name": "Горячая вода", "amount": "550гр"}
        ],
        instruction="В кувшин добавляем иван-чай, заливаем горячей водой. Настаиваем 30 минут, процеживаем. Хранить в холодильнике 14 суток.",
        description="Травянистая настойка с ягодными нотками.",
        shelf_life=14
    ))

    # Добавляем сроки годности для некоторых продуктов (из файла СРОКИ ГОДНОСТИ)
    shelf_items_data = [
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
    for name, cat, subcat, days in shelf_items_data:
        _shelf_life_items.append(ShelfLifeItem(
            id=len(_shelf_life_items) + 1,
            name=name,
            category=cat,
            subcategory=subcat,
            shelf_life_days=days,
            location="Витрина"
        ))

    return recipes


# =========================================================
# ЗАГРУЗКА ДАННЫХ (ВСТРОЕННЫЕ РЕЦЕПТЫ)
# =========================================================

def load_recipes_from_excel():
    """
    Загружает рецепты из встроенного списка (без внешних файлов).
    """
    index = get_search_index()
    recipes = _build_recipes_list()
    for recipe in recipes:
        index.add_recipe(recipe)
        # Добавляем в сроки годности, если есть shelf_life
        if recipe.shelf_life:
            _shelf_life_items.append(ShelfLifeItem(
                id=len(_shelf_life_items) + 1,
                name=recipe.name,
                category=recipe.category,
                subcategory=recipe.subcategory,
                shelf_life_days=recipe.shelf_life,
                location=""
            ))

    logger.info(f"Загружено рецептов: {len(index.recipes)}")
    logger.info(f"Загружено позиций сроков годности: {len(_shelf_life_items)}")


# =========================================================
# ОСНОВНЫЕ ОБРАБОТЧИКИ (без изменений, они уже используют индекс)
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

    return await search_results(update, context, query)