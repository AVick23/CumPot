import logging
import re
from typing import Dict, List, Tuple

from db.shifts import get_last_closing_report

logger = logging.getLogger(__name__)

# Разделы, которые мы хотим извлечь из отчёта закрытия
# Ключ - название раздела (как он хранится в parsed_data),
# значение - (локация: 'bar', 'kitchen' или 'common', иконка, заголовок для вывода)
SECTION_MAPPING = {
    "Заготовки бар": ("bar", "🧊", "Заготовки бара"),
    "Еда": ("kitchen", "🍳", "Еда (общее)"),
    "Заготовки для еды": ("kitchen", "🥗", "Заготовки для еды"),
    "Блюда": ("kitchen", "🍽", "Блюда (остатки/план)"),
    "Go-list": ("common", "📋", "Задачи на день (Go-list)"),
    "График уборки / полив цветов": ("common", "🧽", "Уборка/полив"),
    "Полы мылись": ("common", "🧹", "Мытьё полов"),
    "Примечания": ("common", "📝", "Примечания"),
    "Стопы": ("common", "🚫", "Стоп-лист"),
    "Стоп-лист": ("common", "🚫", "Стоп-лист"),
}

# Дополнительные разделы, которые могут быть полезны, но не обязательны
EXTRA_SECTIONS = {
    "Рекомендации по фильтру": ("bar", "☕", "Рекомендации по фильтру"),
    "Эспрессо, вода и заготовки по бару": ("bar", "☕", "Эспрессо и вода"),
    "Рецепт по завершении": ("bar", "⚙️", "Рецепт на конец смены"),
}


def extract_sections_from_report(report_text: str, report_type: str = "closing") -> Dict[str, str]:
    """
    Парсит текст отчёта и возвращает словарь разделов.
    Использует тот же парсер, что и в employee.reports.utils, если он доступен,
    иначе — упрощённую версию.
    """
    try:
        # Попытка использовать существующий парсер (он должен быть импортирован)
        from employee.reports.utils import parse_report_sections
        parsed = parse_report_sections(report_text, report_type)
        # Удаляем служебный ключ _header
        parsed.pop("_header", None)
        return parsed
    except ImportError:
        # Упрощённый парсер на случай, если модуль недоступен
        logger.warning("employee.reports.utils не найден, использую встроенный парсер")
        return _simple_parse(report_text, report_type)


def _simple_parse(text: str, report_type: str) -> Dict[str, str]:
    """Простой парсер для извлечения разделов по маркерам."""
    # Собираем все возможные маркеры для closing (из констант или вручную)
    markers = {
        "Стопы": ["Стопы:", "Стопы"],
        "Эспрессо, вода и заготовки по бару": ["Эспрессо, вода и заготовки по бару:", "Эспрессо, вода и заготовки по бару"],
        "Рецепт по завершении": ["Рецепт по завершении:", "Рецепт по завершении"],
        "Заготовки бар": ["Заготовки бар:", "Заготовки бар"],
        "Рекомендации по фильтру": ["Рекомендации по фильтру:", "Рекомендации по фильтру"],
        "Еда": ["Еда:", "Еда"],
        "Заготовки для еды": ["Заготовки для еды:", "Заготовки для еды"],
        "Блюда": ["Блюда:", "Блюда"],
        "Go-list": ["Go-list:", "Go-list", "Go - list:", "Go - list"],
        "График уборки / полив цветов": ["График уборки/полив цветов:", "График уборки/полив цветов", "График уборки / полив цветов:"],
        "Полы мылись": ["Полы мылись:", "Полы мылись"],
        "Примечания": ["Примечания:", "Примечания"],
        "Стоп-лист": ["Стоп-лист:", "Стоп-лист"],
    }
    # Построим список кортежей (маркер, раздел)
    marker_list = []
    for section, variants in markers.items():
        for var in variants:
            marker_list.append((var.lower(), section))
    # Сортируем по длине, чтобы более длинные маркеры обрабатывались раньше
    marker_list.sort(key=lambda x: len(x[0]), reverse=True)

    lines = text.split('\n')
    result = {}
    current_section = None
    buffer = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Проверяем, начинается ли строка с какого-либо маркера
        matched = False
        lower_line = stripped.lower()
        for marker, section in marker_list:
            if lower_line.startswith(marker):
                # Если уже был активный раздел, сохраняем его
                if current_section and buffer:
                    result[current_section] = '\n'.join(buffer).strip()
                current_section = section
                buffer = []
                # Остаток строки после маркера добавляем в буфер
                remainder = stripped[len(marker):].lstrip(':;-– ').strip()
                if remainder:
                    buffer.append(remainder)
                matched = True
                break
        if not matched:
            if current_section:
                buffer.append(stripped)
            else:
                # до первого маркера игнорируем
                pass

    # Сохраняем последний раздел
    if current_section and buffer:
        result[current_section] = '\n'.join(buffer).strip()

    return result


def build_opening_reminder(report_text: str) -> str:
    """
    Принимает полный текст отчёта закрытия и возвращает текст напоминания для утренней смены.
    """
    parsed = extract_sections_from_report(report_text, "closing")

    # Структурируем задачи по локациям
    bar_tasks = []
    kitchen_tasks = []
    common_tasks = []

    for section, content in parsed.items():
        if not content:
            continue
        # Определяем локацию
        if section in SECTION_MAPPING:
            loc, icon, title = SECTION_MAPPING[section]
        elif section in EXTRA_SECTIONS:
            loc, icon, title = EXTRA_SECTIONS[section]
        else:
            # Неизвестный раздел – считаем общим
            loc = "common"
            icon = "📌"
            title = section

        # Формируем строку с содержимым
        # Если это список (маркеры "-" или "•"), то оставляем как есть
        # Иначе просто добавляем текст
        lines = content.split('\n')
        if any(l.strip().startswith(('-', '•', '*')) for l in lines):
            task_text = content
        else:
            # Если это одна строка или несколько строк без маркеров, превращаем в список
            task_text = content

        task_entry = f"{icon} **{title}**\n{task_text}"

        if loc == "bar":
            bar_tasks.append(task_entry)
        elif loc == "kitchen":
            kitchen_tasks.append(task_entry)
        else:
            common_tasks.append(task_entry)

    # Формируем итоговый текст
    lines = []
    lines.append("🌅 **Доброе утро!** Вот что нужно учесть сегодня, основываясь на вчерашнем закрытии:")
    lines.append("")

    if common_tasks:
        lines.append("📌 **Общее**")
        lines.extend(common_tasks)
        lines.append("")

    if bar_tasks:
        lines.append("🍸 **Бар**")
        lines.extend(bar_tasks)
        lines.append("")

    if kitchen_tasks:
        lines.append("🍳 **Кухня**")
        lines.extend(kitchen_tasks)
        lines.append("")

    if not (bar_tasks or kitchen_tasks or common_tasks):
        lines.append("✅ Вчерашний отчёт не содержал задач для сегодняшней смены.")

    return "\n".join(lines)


# Для обратной совместимости и удобства вызова
def get_last_closing_report_text() -> str | None:
    """
    Возвращает текст последнего отчёта закрытия.
    Использует функцию из db.shifts.
    """
    return get_last_closing_report()