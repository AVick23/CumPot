import json
import logging
from datetime import datetime, timedelta
from db import get_connection
from .constants import MSG_LIMIT, REPORT_TYPE_LABELS

logger = logging.getLogger(__name__)


# =========================================================
# DB OPERATIONS
# =========================================================

def save_report(date_str: str, report_type: str, author_id: int, full_text: str) -> int:
    """
    Сохраняет отчёт в БД, предварительно парсит разделы и сохраняет JSON.
    Возвращает id записи.
    """
    parsed = parse_report_sections(full_text, report_type)
    parsed_json = json.dumps(parsed, ensure_ascii=False)
    now = datetime.now().isoformat()

    with get_connection() as conn:
        # Проверяем, существует ли уже отчёт за эту дату и тип
        existing = conn.execute(
            "SELECT id FROM shift_reports WHERE date = ? AND report_type = ?",
            (date_str, report_type)
        ).fetchone()
        if existing:
            # Обновляем
            conn.execute(
                """
                UPDATE shift_reports
                SET full_text = ?, parsed_data = ?, updated_at = ?, author_id = ?
                WHERE id = ?
                """,
                (full_text, parsed_json, now, author_id, existing["id"])
            )
            report_id = existing["id"]
        else:
            # Вставляем
            cur = conn.execute(
                """
                INSERT INTO shift_reports (date, report_type, author_id, full_text, parsed_data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (date_str, report_type, author_id, full_text, parsed_json, now, now)
            )
            report_id = cur.lastrowid
        conn.commit()
    logger.info(f"Сохранён отчёт {report_type} за {date_str} (id={report_id})")
    return report_id


def get_report(date_str: str, report_type: str) -> dict | None:
    """Возвращает отчёт за указанную дату и тип, либо None."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, date, report_type, author_id, full_text, parsed_data, created_at, updated_at
            FROM shift_reports
            WHERE date = ? AND report_type = ?
            """,
            (date_str, report_type)
        ).fetchone()
    return dict(row) if row else None


def get_last_report(report_type: str, before_date: str = None) -> dict | None:
    """
    Возвращает последний отчёт указанного типа до указанной даты (включительно).
    Если before_date не указан, берёт самый свежий.
    """
    with get_connection() as conn:
        query = """
            SELECT id, date, report_type, author_id, full_text, parsed_data, created_at, updated_at
            FROM shift_reports
            WHERE report_type = ?
        """
        params = [report_type]
        if before_date:
            query += " AND date <= ?"
            params.append(before_date)
        query += " ORDER BY date DESC, id DESC LIMIT 1"
        row = conn.execute(query, params).fetchone()
    return dict(row) if row else None


def get_dates_with_reports(year: int, month: int, report_type: str = None) -> set[str]:
    """Возвращает множество дат (YYYY-MM-DD) за месяц, для которых есть отчёты указанного типа."""
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month+1:02d}-01" if month < 12 else f"{year+1:04d}-01-01"
    with get_connection() as conn:
        query = """
            SELECT DISTINCT date
            FROM shift_reports
            WHERE date >= ? AND date < ?
        """
        params = [start_date, end_date]
        if report_type:
            query += " AND report_type = ?"
            params.append(report_type)
        rows = conn.execute(query, params).fetchall()
    return {row["date"] for row in rows}


# =========================================================
# PARSING
# =========================================================

def parse_report_sections(full_text: str, report_type: str) -> dict:
    """
    Парсит текст отчёта по разделам, характерным для открытия или закрытия.
    Возвращает словарь с разделами.
    """
    sections = {}
    if report_type == "opening":
        # Разделы открытия (по примерам)
        # Маркеры: "Влажность в помещении", "В эспрессо", "Тдс", "Температура групп", "Помол", "Давление", "Рецепт", "В основе", "В молоке", "На фильтре", "Стоп-лист"
        # Парсим по ключевым словам, ищем строки после маркеров до следующего маркера или конца.
        markers = [
            "Влажность в помещении",
            "В эспрессо",
            "Тдс -",
            "Температура групп -",
            "Помол -",
            "Давление -",
            "Рецепт:",
            "В основе:",
            "В молоке:",
            "На фильтре:",
            "Стоп-лист"
        ]
        # Простой парсинг: разбиваем по строкам, ищем маркеры.
        lines = full_text.split("\n")
        current_section = None
        buffer = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            found = False
            for marker in markers:
                if line.startswith(marker):
                    # Сохраняем предыдущий раздел
                    if current_section and buffer:
                        sections[current_section] = "\n".join(buffer).strip()
                    current_section = marker
                    buffer = [line[len(marker):].strip()]
                    found = True
                    break
            if not found:
                if current_section:
                    buffer.append(line)
        # Последний раздел
        if current_section and buffer:
            sections[current_section] = "\n".join(buffer).strip()
    else:
        # Закрытие
        markers = [
            "Влажность в помещении",
            "Стопы",
            "Эспрессо, вода и заготовки по бару",
            "Рецепт по завершении:",
            "Заготовки бар:",
            "Рекомендации по фильтру:",
            "Еда",
            "Заготовки для еды:",
            "Блюда:",
            "Go - list",
            "График уборки/полив цветов",
            "Полы мылись",
            "Примечания:"
        ]
        lines = full_text.split("\n")
        current_section = None
        buffer = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            found = False
            for marker in markers:
                if line.startswith(marker) or line.startswith(marker.replace(":", "")):
                    if current_section and buffer:
                        sections[current_section] = "\n".join(buffer).strip()
                    current_section = marker
                    buffer = [line[len(marker):].strip()]
                    found = True
                    break
            if not found:
                if current_section:
                    buffer.append(line)
        if current_section and buffer:
            sections[current_section] = "\n".join(buffer).strip()
    return sections


# =========================================================
# HELPERS FOR UI
# =========================================================

def format_report_preview(full_text: str, max_len: int = 500) -> str:
    if len(full_text) <= max_len:
        return full_text
    return full_text[:max_len] + "…"


def truncate_text(text: str, limit: int = MSG_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit-1].rstrip() + "…"