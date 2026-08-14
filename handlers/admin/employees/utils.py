import io
import json
import logging
from datetime import datetime, timedelta

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from db import get_connection
from db.users import get_user
from db.profile import (
    get_employee_full_info,
    get_taxi_summary,
    get_salary_history,
)

from utils.time_utils import today_msk_str

logger = logging.getLogger(__name__)


# =========================================================
# DESIGN SYSTEM (Apple-like)
# =========================================================

COLOR_DARK = "1D1D1F"       # почти чёрный — заголовки
COLOR_LIGHT = "F5F5F7"      # светло-серый — зебра
COLOR_BLUE = "0071E3"       # акцент Apple
COLOR_GREEN = "34C759"
COLOR_ORANGE = "FF9500"
COLOR_WHITE = "FFFFFF"

FONT_NAME = "Arial"

THIN_BORDER = Border(
    left=Side(style="thin", color="D2D2D7"),
    right=Side(style="thin", color="D2D2D7"),
    top=Side(style="thin", color="D2D2D7"),
    bottom=Side(style="thin", color="D2D2D7"),
)


def _safe(value) -> str:
    if value is None:
        return "—"
    return str(value)


def _style_title(ws, row: int, col: int, text: str):
    cell = ws.cell(row=row, column=col, value=text)
    cell.font = Font(name=FONT_NAME, size=16, bold=True, color=COLOR_DARK)
    cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[row].height = 28
    return cell


def _style_subtitle(ws, row: int, col: int, text: str):
    cell = ws.cell(row=row, column=col, value=text)
    cell.font = Font(name=FONT_NAME, size=11, color="6E6E73")
    cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[row].height = 18
    return cell


def _style_header_row(ws, row: int, headers: list[str]):
    for idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=idx, value=header)
        cell.font = Font(name=FONT_NAME, size=11, bold=True, color=COLOR_WHITE)
        cell.fill = PatternFill("solid", fgColor=COLOR_DARK)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER
    ws.row_dimensions[row].height = 24


def _style_data_row(ws, row: int, values: list, zebra: bool):
    fill = PatternFill("solid", fgColor=COLOR_LIGHT) if zebra else None

    for idx, value in enumerate(values, start=1):
        cell = ws.cell(row=row, column=idx, value=value)
        cell.font = Font(name=FONT_NAME, size=10, color=COLOR_DARK)
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
        if fill:
            cell.fill = fill
    ws.row_dimensions[row].height = 20


def _auto_width(ws, min_width: int = 12, max_width: int = 40):
    for column_cells in ws.columns:
        max_length = 0
        column_letter = get_column_letter(column_cells[0].column)

        for cell in column_cells:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except Exception:
                pass

        adjusted = min(max(max_length + 2, min_width), max_width)
        ws.column_dimensions[column_letter].width = adjusted


# =========================================================
# DATA HELPERS
# =========================================================

def _period_range(period_days: int = 30) -> tuple[str, str]:
    date_to = today_msk_str()
    date_from = (datetime.now() - timedelta(days=period_days)).strftime("%Y-%m-%d")
    return date_from, date_to


def get_employee_shifts(user_id: int, date_from: str, date_to: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT s.date, s.start_time, s.active,
                   st.name AS shift_name, st.location, st.duration
            FROM shifts s
            LEFT JOIN shift_types st ON s.shift_type_id = st.id
            WHERE s.user_id = ? AND s.date >= ? AND s.date <= ?
            ORDER BY s.date DESC, s.start_time DESC
            """,
            (user_id, date_from, date_to),
        ).fetchall()

    return [dict(row) for row in rows]


def get_employee_reports(user_id: int, date_from: str, date_to: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT date, report_type, full_text, created_at, updated_at
            FROM shift_reports
            WHERE author_id = ? AND date >= ? AND date <= ?
            ORDER BY date DESC
            """,
            (user_id, date_from, date_to),
        ).fetchall()

    return [dict(row) for row in rows]


def get_employee_checklist_activity(user_id: int, date_from: str, date_to: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.date, p.completed, p.completed_at,
                   i.text AS item_text, i.location, i.category
            FROM checklist_shared_progress p
            LEFT JOIN checklist_items i ON p.item_id = i.id
            WHERE p.completed_by = ? AND p.date >= ? AND p.date <= ?
            ORDER BY p.date DESC
            """,
            (user_id, date_from, date_to),
        ).fetchall()

    return [dict(row) for row in rows]


def get_taxi_expenses_full(user_id: int, date_from: str, date_to: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT date, amount, photo_file_ids
            FROM taxi_expenses
            WHERE user_id = ? AND date >= ? AND date <= ?
            ORDER BY date DESC
            """,
            (user_id, date_from, date_to),
        ).fetchall()

    result = []

    for row in rows:
        item = dict(row)

        photos = []
        raw = item.get("photo_file_ids")

        if raw:
            try:
                parsed = json.loads(raw)

                if isinstance(parsed, list):
                    for entry in parsed:
                        if isinstance(entry, str):
                            photos.append(entry)
                        elif isinstance(entry, dict) and entry.get("file_id"):
                            photos.append(entry["file_id"])
            except Exception:
                pass

        item["photos"] = photos
        result.append(item)

    return result


# =========================================================
# XLSX: ОБЩИЙ ОТЧЁТ ПО ВСЕМ СОТРУДНИКАМ
# =========================================================

def generate_all_employees_report(users: list[dict], period_days: int = 30) -> bytes:
    wb = Workbook()

    date_from, date_to = _period_range(period_days)

    # ---------- ЛИСТ 1: ОБЗОР ----------
    ws = wb.active
    ws.title = "Обзор"

    _style_title(ws, 1, 1, "Команда")
    _style_subtitle(ws, 2, 1, f"Период: {date_from} — {date_to}")

    headers = [
        "ФИО",
        "Позиция",
        "Статус",
        "Ставка ₽/час",
        "Смен",
        "Часов",
        "Такси ₽",
        "Отчётов",
        "Задач выполнено",
    ]
    _style_header_row(ws, 4, headers)

    row_index = 5

    for user in users:
        tg_id = user["tg_id"]
        info = get_employee_full_info(tg_id) or {}

        shifts = get_employee_shifts(tg_id, date_from, date_to)
        total_hours = sum((s.get("duration") or 0) / 60 for s in shifts)

        taxi = get_taxi_summary(tg_id, date_from, date_to)
        reports = get_employee_reports(tg_id, date_from, date_to)
        checklist = get_employee_checklist_activity(tg_id, date_from, date_to)

        values = [
            _safe(info.get("full_name")),
            _safe(info.get("position")),
            _safe(info.get("status")),
            info.get("current_rate") or 0,
            len(shifts),
            round(total_hours, 1),
            taxi.get("total") or 0,
            len(reports),
            len(checklist),
        ]

        _style_data_row(ws, row_index, values, zebra=(row_index % 2 == 0))
        row_index += 1

    _auto_width(ws)

    # ---------- ЛИСТ 2: СМЕНЫ ----------
    ws_shifts = wb.create_sheet("Смены")

    _style_title(ws_shifts, 1, 1, "Смены сотрудников")
    _style_subtitle(ws_shifts, 2, 1, f"Период: {date_from} — {date_to}")

    headers = ["Дата", "ФИО", "Смена", "Локация", "Начало", "Часов"]
    _style_header_row(ws_shifts, 4, headers)

    row_index = 5

    for user in users:
        tg_id = user["tg_id"]
        name = user.get("full_name") or user.get("first_name") or str(tg_id)
        shifts = get_employee_shifts(tg_id, date_from, date_to)

        for shift in shifts:
            values = [
                _safe(shift.get("date")),
                name,
                _safe(shift.get("shift_name")),
                _safe(shift.get("location")),
                _safe(shift.get("start_time")),
                round((shift.get("duration") or 0) / 60, 1),
            ]

            _style_data_row(ws_shifts, row_index, values, zebra=(row_index % 2 == 0))
            row_index += 1

    _auto_width(ws_shifts)

    # ---------- ЛИСТ 3: ТАКСИ ----------
    ws_taxi = wb.create_sheet("Такси")

    _style_title(ws_taxi, 1, 1, "Расходы на такси")
    _style_subtitle(ws_taxi, 2, 1, f"Период: {date_from} — {date_to}")

    headers = ["Дата", "ФИО", "Сумма ₽", "Фото"]
    _style_header_row(ws_taxi, 4, headers)

    row_index = 5

    for user in users:
        tg_id = user["tg_id"]
        name = user.get("full_name") or user.get("first_name") or str(tg_id)
        expenses = get_taxi_expenses_full(tg_id, date_from, date_to)

        for expense in expenses:
            values = [
                _safe(expense.get("date")),
                name,
                expense.get("amount") or 0,
                "📷 Есть" if expense.get("photos") else "—",
            ]

            _style_data_row(ws_taxi, row_index, values, zebra=(row_index % 2 == 0))
            row_index += 1

    _auto_width(ws_taxi)

    # ---------- ЛИСТ 4: ОТЧЁТЫ ----------
    ws_reports = wb.create_sheet("Отчёты")

    _style_title(ws_reports, 1, 1, "Отчёты открытия / закрытия")
    _style_subtitle(ws_reports, 2, 1, f"Период: {date_from} — {date_to}")

    headers = ["Дата", "ФИО", "Тип", "Текст"]
    _style_header_row(ws_reports, 4, headers)

    row_index = 5

    for user in users:
        tg_id = user["tg_id"]
        name = user.get("full_name") or user.get("first_name") or str(tg_id)
        reports = get_employee_reports(tg_id, date_from, date_to)

        for report in reports:
            report_type = "Открытие" if report.get("report_type") == "opening" else "Закрытие"

            values = [
                _safe(report.get("date")),
                name,
                report_type,
                _safe(report.get("full_text"))[:500],
            ]

            _style_data_row(ws_reports, row_index, values, zebra=(row_index % 2 == 0))
            row_index += 1

    _auto_width(ws_reports)

    # ---------- ЛИСТ 5: ЧЕК-ЛИСТЫ ----------
    ws_check = wb.create_sheet("Чек-листы")

    _style_title(ws_check, 1, 1, "Выполнение чек-листов")
    _style_subtitle(ws_check, 2, 1, f"Период: {date_from} — {date_to}")

    headers = ["Дата", "ФИО", "Задача", "Локация", "Категория", "Время"]
    _style_header_row(ws_check, 4, headers)

    row_index = 5

    for user in users:
        tg_id = user["tg_id"]
        name = user.get("full_name") or user.get("first_name") or str(tg_id)
        activity = get_employee_checklist_activity(tg_id, date_from, date_to)

        for act in activity:
            values = [
                _safe(act.get("date")),
                name,
                _safe(act.get("item_text")),
                _safe(act.get("location")),
                _safe(act.get("category")),
                _safe(act.get("completed_at")),
            ]

            _style_data_row(ws_check, row_index, values, zebra=(row_index % 2 == 0))
            row_index += 1

    _auto_width(ws_check)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return buffer.getvalue()


# =========================================================
# XLSX: ОТЧЁТ ПО ОДНОМУ СОТРУДНИКУ
# =========================================================

def generate_employee_report(user_id: int, period_days: int = 30) -> bytes:
    wb = Workbook()

    user = get_user(user_id) or {}
    info = get_employee_full_info(user_id) or {}

    date_from, date_to = _period_range(period_days)

    name = user.get("full_name") or user.get("first_name") or str(user_id)

    # ---------- ЛИСТ 1: ПРОФИЛЬ ----------
    ws = wb.active
    ws.title = "Профиль"

    _style_title(ws, 1, 1, name)
    _style_subtitle(ws, 2, 1, f"Отчёт за период {date_from} — {date_to}")

    profile_rows = [
        ("ФИО", _safe(info.get("full_name"))),
        ("Позиция", _safe(info.get("position"))),
        ("Статус", _safe(info.get("status"))),
        ("Телефон", _safe(info.get("phone"))),
        ("Дата рождения", _safe(info.get("birthday"))),
        ("Адрес", _safe(info.get("address"))),
        ("Обязанности", _safe(info.get("responsibilities"))),
        ("Комментарий админа", _safe(info.get("admin_comment"))),
        ("Текущая ставка ₽/час", info.get("current_rate") or 0),
    ]

    row_index = 4

    for label, value in profile_rows:
        label_cell = ws.cell(row=row_index, column=1, value=label)
        label_cell.font = Font(name=FONT_NAME, size=10, bold=True, color="6E6E73")

        value_cell = ws.cell(row=row_index, column=2, value=value)
        value_cell.font = Font(name=FONT_NAME, size=10, color=COLOR_DARK)

        row_index += 1

    _auto_width(ws, max_width=60)

    # ---------- ЛИСТ 2: СМЕНЫ ----------
    ws_shifts = wb.create_sheet("Смены")

    shifts = get_employee_shifts(user_id, date_from, date_to)
    total_hours = sum((s.get("duration") or 0) / 60 for s in shifts)

    _style_title(ws_shifts, 1, 1, "Смены")
    _style_subtitle(ws_shifts, 2, 1, f"Всего: {len(shifts)} смен · {round(total_hours, 1)} часов")

    headers = ["Дата", "Смена", "Локация", "Начало", "Часов", "Активна"]
    _style_header_row(ws_shifts, 4, headers)

    row_index = 5

    for shift in shifts:
        values = [
            _safe(shift.get("date")),
            _safe(shift.get("shift_name")),
            _safe(shift.get("location")),
            _safe(shift.get("start_time")),
            round((shift.get("duration") or 0) / 60, 1),
            "Да" if shift.get("active") else "Закрыта",
        ]

        _style_data_row(ws_shifts, row_index, values, zebra=(row_index % 2 == 0))
        row_index += 1

    _auto_width(ws_shifts)

    # ---------- ЛИСТ 3: ТАКСИ ----------
    ws_taxi = wb.create_sheet("Такси")

    expenses = get_taxi_expenses_full(user_id, date_from, date_to)
    total_taxi = sum(e.get("amount") or 0 for e in expenses)

    _style_title(ws_taxi, 1, 1, "Такси")
    _style_subtitle(ws_taxi, 2, 1, f"Всего: {len(expenses)} поездок · {total_taxi} ₽")

    headers = ["Дата", "Сумма ₽", "Фото"]
    _style_header_row(ws_taxi, 4, headers)

    row_index = 5

    for expense in expenses:
        values = [
            _safe(expense.get("date")),
            expense.get("amount") or 0,
            "📷 Есть" if expense.get("photos") else "—",
        ]

        _style_data_row(ws_taxi, row_index, values, zebra=(row_index % 2 == 0))
        row_index += 1

    _auto_width(ws_taxi)

    # ---------- ЛИСТ 4: ОТЧЁТЫ ----------
    ws_reports = wb.create_sheet("Отчёты")

    reports = get_employee_reports(user_id, date_from, date_to)

    _style_title(ws_reports, 1, 1, "Отчёты открытия / закрытия")
    _style_subtitle(ws_reports, 2, 1, f"Всего: {len(reports)} отчётов")

    headers = ["Дата", "Тип", "Текст"]
    _style_header_row(ws_reports, 4, headers)

    row_index = 5

    for report in reports:
        report_type = "Открытие" if report.get("report_type") == "opening" else "Закрытие"

        values = [
            _safe(report.get("date")),
            report_type,
            _safe(report.get("full_text"))[:700],
        ]

        _style_data_row(ws_reports, row_index, values, zebra=(row_index % 2 == 0))
        row_index += 1

    _auto_width(ws_reports, max_width=80)

    # ---------- ЛИСТ 5: ЧЕК-ЛИСТЫ ----------
    ws_check = wb.create_sheet("Чек-листы")

    activity = get_employee_checklist_activity(user_id, date_from, date_to)

    _style_title(ws_check, 1, 1, "Выполнение чек-листов")
    _style_subtitle(ws_check, 2, 1, f"Всего выполнено задач: {len(activity)}")

    headers = ["Дата", "Задача", "Локация", "Категория", "Время"]
    _style_header_row(ws_check, 4, headers)

    row_index = 5

    for act in activity:
        values = [
            _safe(act.get("date")),
            _safe(act.get("item_text")),
            _safe(act.get("location")),
            _safe(act.get("category")),
            _safe(act.get("completed_at")),
        ]

        _style_data_row(ws_check, row_index, values, zebra=(row_index % 2 == 0))
        row_index += 1

    _auto_width(ws_check)

    # ---------- ЛИСТ 6: ИСТОРИЯ СТАВОК ----------
    ws_rates = wb.create_sheet("Ставки")

    rates = get_salary_history(user_id)

    _style_title(ws_rates, 1, 1, "История ставок")
    _style_subtitle(ws_rates, 2, 1, "Все изменения ставки")

    headers = ["Дата от", "Дата до", "Ставка ₽/час"]
    _style_header_row(ws_rates, 4, headers)

    row_index = 5

    for rate in rates:
        values = [
            _safe(rate.get("date_from")),
            _safe(rate.get("date_to")) or "Активна",
            rate.get("rate") or 0,
        ]

        _style_data_row(ws_rates, row_index, values, zebra=(row_index % 2 == 0))
        row_index += 1

    _auto_width(ws_rates)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return buffer.getvalue()


# =========================================================
# TAXI PHOTOS COLLECTOR
# =========================================================

def collect_taxi_photo_ids(user_id: int, period_days: int = 30, limit: int = 30) -> list[str]:
    date_from, date_to = _period_range(period_days)
    expenses = get_taxi_expenses_full(user_id, date_from, date_to)

    photo_ids: list[str] = []

    for expense in expenses:
        for photo_id in expense.get("photos", []):
            photo_ids.append(photo_id)

            if len(photo_ids) >= limit:
                return photo_ids

    return photo_ids