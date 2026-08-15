import io
import json
import logging
from datetime import datetime, timedelta

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from db import get_connection
from db.users import get_user
from db.profile import get_employee_full_info
from utils.time_utils import today_msk_str

logger = logging.getLogger(__name__)


# =========================================================
# DESIGN SYSTEM
# =========================================================
COLOR_DARK = "1D1D1F"
COLOR_LIGHT = "F5F5F7"
COLOR_BLUE = "0071E3"
COLOR_GREEN = "34C759"
COLOR_ORANGE = "FF9500"
COLOR_WHITE = "FFFFFF"
COLOR_GRAY = "6E6E73"

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


def _num(value, digits: int = 1) -> float:
    try:
        return round(float(value or 0), digits)
    except Exception:
        return 0.0


def _safe_percent(value) -> str:
    if value is None:
        return "—"
    try:
        return f"{round(float(value), 1)}%"
    except Exception:
        return "—"


def _truncate(value, limit: int) -> str:
    text = _safe(value)
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def _style_title(ws, row: int, col: int, text: str):
    cell = ws.cell(row=row, column=col, value=text)
    cell.font = Font(name=FONT_NAME, size=16, bold=True, color=COLOR_DARK)
    cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[row].height = 28
    return cell


def _style_subtitle(ws, row: int, col: int, text: str):
    cell = ws.cell(row=row, column=col, value=text)
    cell.font = Font(name=FONT_NAME, size=11, color=COLOR_GRAY)
    cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[row].height = 18
    return cell


def _style_section(ws, row: int, col: int, text: str):
    cell = ws.cell(row=row, column=col, value=text)
    cell.font = Font(name=FONT_NAME, size=12, bold=True, color=COLOR_BLUE)
    cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[row].height = 22
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


def _style_metric_row(ws, row: int, label: str, value, zebra: bool = False):
    fill = PatternFill("solid", fgColor=COLOR_LIGHT) if zebra else None

    label_cell = ws.cell(row=row, column=1, value=label)
    label_cell.font = Font(name=FONT_NAME, size=10, bold=True, color=COLOR_GRAY)
    label_cell.alignment = Alignment(vertical="center")
    label_cell.border = THIN_BORDER

    value_cell = ws.cell(row=row, column=2, value=value)
    value_cell.font = Font(name=FONT_NAME, size=10, color=COLOR_DARK)
    value_cell.alignment = Alignment(vertical="center", wrap_text=True)
    value_cell.border = THIN_BORDER

    if fill:
        label_cell.fill = fill
        value_cell.fill = fill

    ws.row_dimensions[row].height = 20


def _auto_width(ws, min_width: int = 12, max_width: int = 40):
    for column_cells in ws.columns:
        if not column_cells:
            continue

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


def _write_sections_sheet(ws, title: str, subtitle: str, sections: list[tuple[str, list[tuple]]]):
    _style_title(ws, 1, 1, title)
    _style_subtitle(ws, 2, 1, subtitle)

    row = 4

    for section_title, items in sections:
        _style_section(ws, row, 1, section_title)
        row += 1

        for label, value in items:
            _style_metric_row(ws, row, label, value, zebra=(row % 2 == 0))
            row += 1

        row += 1

    _auto_width(ws, max_width=80)


# =========================================================
# BASE DATA HELPERS
# =========================================================
def _period_range(period_days: int = 30) -> tuple[str, str]:
    date_to = today_msk_str()
    date_from = (datetime.now() - timedelta(days=period_days)).strftime("%Y-%m-%d")
    return date_from, date_to


def _normalize_location(value) -> str:
    if not value:
        return "Не указано"

    val = str(value).strip().lower()

    if val in {"bar", "бар"} or "бар" in val:
        return "Бар"

    if val in {"kitchen", "кухня"} or "кух" in val:
        return "Кухня"

    return str(value).strip().capitalize() or "Не указано"


def _has_photo_progress(row: dict) -> bool:
    if row.get("photo_file_id"):
        return True

    raw = row.get("photo_file_ids")

    if not raw:
        return False

    try:
        parsed = json.loads(raw)
    except Exception:
        return bool(str(raw).strip())

    if isinstance(parsed, list):
        for entry in parsed:
            if isinstance(entry, str) and entry.strip():
                return True
            if isinstance(entry, dict) and entry.get("file_id"):
                return True
        return False

    if isinstance(parsed, dict):
        return bool(parsed.get("file_id"))

    return bool(parsed)


def get_employee_shifts(user_id: int, date_from: str, date_to: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                s.date,
                s.start_time,
                s.active,
                st.name AS shift_name,
                st.location,
                st.duration
            FROM shifts s
            LEFT JOIN shift_types st ON s.shift_type_id = st.id
            WHERE s.user_id = ?
              AND s.date >= ?
              AND s.date <= ?
            ORDER BY s.date DESC, s.start_time DESC
            """,
            (user_id, date_from, date_to),
        ).fetchall()

    return [dict(row) for row in rows]


def get_employee_reports(user_id: int, date_from: str, date_to: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                date,
                report_type,
                full_text,
                created_at,
                updated_at
            FROM shift_reports
            WHERE author_id = ?
              AND date >= ?
              AND date <= ?
            ORDER BY date DESC
            """,
            (user_id, date_from, date_to),
        ).fetchall()

    return [dict(row) for row in rows]


def get_employee_checklist_activity(user_id: int, date_from: str, date_to: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                p.date,
                p.completed,
                p.completed_at,
                p.item_id,
                p.photo_file_id,
                p.photo_file_ids,
                i.text AS item_text,
                i.location,
                i.category,
                i.requires_photo
            FROM checklist_shared_progress p
            LEFT JOIN checklist_items i ON p.item_id = i.id
            WHERE p.completed_by = ?
              AND p.date >= ?
              AND p.date <= ?
              AND COALESCE(p.completed, 0) = 1
            ORDER BY p.date DESC
            """,
            (user_id, date_from, date_to),
        ).fetchall()

    result = []

    for row in rows:
        item = dict(row)
        item["has_photo"] = _has_photo_progress(item)
        result.append(item)

    return result


# =========================================================
# XLSX: ОБЩИЙ ОТЧЁТ ПО ВСЕМ СОТРУДНИКАМ
# =========================================================
def generate_all_employees_report(users: list[dict], period_days: int = 30) -> bytes:
    wb = Workbook()
    date_from, date_to = _period_range(period_days)

    # Собираем данные по каждому сотруднику
    metrics = []

    for user in users:
        tg_id = user["tg_id"]
        info = get_employee_full_info(tg_id) or {}

        shifts = get_employee_shifts(tg_id, date_from, date_to)
        total_hours = sum((s.get("duration") or 0) / 60 for s in shifts)

        reports = get_employee_reports(tg_id, date_from, date_to)
        checklist = get_employee_checklist_activity(tg_id, date_from, date_to)

        shift_dates = {s["date"] for s in shifts if s.get("date")}
        report_dates = {r["date"] for r in reports if r.get("date")}
        covered = shift_dates & report_dates

        report_coverage = _num(len(covered) / len(shift_dates) * 100, 1) if shift_dates else None

        metrics.append({
            "name": user.get("full_name") or user.get("first_name") or str(tg_id),
            "position": info.get("position") or user.get("position"),
            "status": info.get("status") or user.get("status") or "—",
            "is_active": bool(user.get("is_active", 1)),
            "shift_count": len(shifts),
            "total_hours": _num(total_hours, 1),
            "reports_count": len(reports),
            "report_coverage": _safe_percent(report_coverage),
            "tasks_completed": len(checklist),
            "tasks_with_photo": sum(1 for a in checklist if a.get("has_photo")),
            "shifts": shifts,
            "reports": reports,
            "checklist": checklist,
        })

    metrics.sort(key=lambda x: (x["name"] or "").lower())

    # ---------- ЛИСТ 1: ОБЗОР ----------
    ws = wb.active
    ws.title = "Обзор"

    _style_title(ws, 1, 1, "Команда")
    _style_subtitle(ws, 2, 1, f"Период: {date_from} — {date_to}")

    headers = [
        "ФИО",
        "Позиция",
        "Статус",
        "Активен",
        "Смен",
        "Часов",
        "Отчётов",
        "% отчётов",
        "Задач",
        "Задач с фото",
    ]

    _style_header_row(ws, 4, headers)

    row_index = 5

    for m in metrics:
        values = [
            m["name"],
            _safe(m["position"]),
            _safe(m["status"]),
            "Да" if m["is_active"] else "Нет",
            m["shift_count"],
            m["total_hours"],
            m["reports_count"],
            m["report_coverage"],
            m["tasks_completed"],
            m["tasks_with_photo"],
        ]

        _style_data_row(ws, row_index, values, zebra=(row_index % 2 == 0))
        row_index += 1

    _auto_width(ws)

    # ---------- ЛИСТ 2: АНАЛИТИКА ----------
    ws_analytics = wb.create_sheet("Аналитика")

    total_shifts = sum(m["shift_count"] for m in metrics)
    total_hours = sum(m["total_hours"] for m in metrics)
    total_reports = sum(m["reports_count"] for m in metrics)
    total_tasks = sum(m["tasks_completed"] for m in metrics)

    avg_hours_per_employee = _num(total_hours / len(metrics), 1) if metrics else 0
    avg_reports_per_employee = _num(total_reports / len(metrics), 1) if metrics else 0
    avg_tasks_per_employee = _num(total_tasks / len(metrics), 1) if metrics else 0

    status_counts = {}
    position_counts = {}

    for m in metrics:
        status = m["status"] or "—"
        status_counts[status] = status_counts.get(status, 0) + 1

        position = _normalize_location(m["position"])
        position_counts[position] = position_counts.get(position, 0) + 1

    status_line = ", ".join(f"{k}: {v}" for k, v in sorted(status_counts.items())) or "—"
    position_line = ", ".join(f"{k}: {v}" for k, v in sorted(position_counts.items())) or "—"

    sections = [
        (
            "Период",
            [
                ("Дата начала", date_from),
                ("Дата конца", date_to),
                ("Дней", period_days),
            ],
        ),
        (
            "Команда",
            [
                ("Всего в отчёте", len(metrics)),
                ("Активных сотрудников", sum(1 for m in metrics if m["is_active"])),
                ("Сотрудников со сменами", sum(1 for m in metrics if m["shift_count"] > 0)),
                ("Распределение по статусам", status_line),
                ("Распределение по позициям", position_line),
            ],
        ),
        (
            "Работа",
            [
                ("Всего смен", total_shifts),
                ("Всего часов", _num(total_hours, 1)),
                ("Средняя смена, ч", _num(total_hours / total_shifts, 1) if total_shifts else 0),
                ("Средняя загрузка на сотрудника, ч", avg_hours_per_employee),
            ],
        ),
        (
            "Процессы",
            [
                ("Всего отчётов", total_reports),
                ("Среднее отчётов на сотрудника", avg_reports_per_employee),
                ("Всего выполненных задач", total_tasks),
                ("Среднее задач на сотрудника", avg_tasks_per_employee),
            ],
        ),
    ]

    _write_sections_sheet(ws_analytics, "Аналитика", f"Период: {date_from} — {date_to}", sections)

    # ---------- ЛИСТ 3: СМЕНЫ ----------
    ws_shifts = wb.create_sheet("Смены")

    _style_title(ws_shifts, 1, 1, "Смены")
    _style_subtitle(ws_shifts, 2, 1, f"Период: {date_from} — {date_to}")

    headers = ["Дата", "ФИО", "Смена", "Локация", "Начало", "Часов", "Активна"]
    _style_header_row(ws_shifts, 4, headers)

    row_index = 5

    for m in metrics:
        for shift in m["shifts"]:
            values = [
                _safe(shift.get("date")),
                m["name"],
                _safe(shift.get("shift_name")),
                _normalize_location(shift.get("location")),
                _safe(shift.get("start_time")),
                _num((shift.get("duration") or 0) / 60, 1),
                "Да" if shift.get("active") else "Закрыта",
            ]

            _style_data_row(ws_shifts, row_index, values, zebra=(row_index % 2 == 0))
            row_index += 1

    _auto_width(ws_shifts)

    # ---------- ЛИСТ 4: ОТЧЁТЫ ----------
    ws_reports = wb.create_sheet("Отчёты")

    _style_title(ws_reports, 1, 1, "Отчёты")
    _style_subtitle(ws_reports, 2, 1, f"Период: {date_from} — {date_to}")

    headers = ["Дата", "ФИО", "Тип", "Длина текста", "Текст"]
    _style_header_row(ws_reports, 4, headers)

    row_index = 5

    for m in metrics:
        for report in m["reports"]:
            report_type = "Открытие" if report.get("report_type") == "opening" else "Закрытие"
            full_text = _safe(report.get("full_text"))

            values = [
                _safe(report.get("date")),
                m["name"],
                report_type,
                len(full_text),
                _truncate(full_text, 500),
            ]

            _style_data_row(ws_reports, row_index, values, zebra=(row_index % 2 == 0))
            row_index += 1

    _auto_width(ws_reports, max_width=80)

    # ---------- ЛИСТ 5: ЧЕК-ЛИСТЫ ----------
    ws_check = wb.create_sheet("Чек-листы")

    _style_title(ws_check, 1, 1, "Чек-листы")
    _style_subtitle(ws_check, 2, 1, f"Период: {date_from} — {date_to}")

    headers = ["Дата", "ФИО", "Задача", "Локация", "Категория", "Время", "Фото"]
    _style_header_row(ws_check, 4, headers)

    row_index = 5

    for m in metrics:
        for act in m["checklist"]:
            values = [
                _safe(act.get("date")),
                m["name"],
                _safe(act.get("item_text")),
                _normalize_location(act.get("location")),
                _safe(act.get("category")),
                _safe(act.get("completed_at")),
                "📷 Есть" if act.get("has_photo") else "—",
            ]

            _style_data_row(ws_check, row_index, values, zebra=(row_index % 2 == 0))
            row_index += 1

    _auto_width(ws_check, max_width=60)

    # ---------- ЛИСТ 6: ДИНАМИКА ----------
    ws_dynamics = wb.create_sheet("Динамика")

    _style_title(ws_dynamics, 1, 1, "Динамика")
    _style_subtitle(ws_dynamics, 2, 1, f"Период: {date_from} — {date_to}")

    # Агрегируем по дням
    daily = {}

    for m in metrics:
        for shift in m["shifts"]:
            d = shift.get("date")
            if not d:
                continue

            if d not in daily:
                daily[d] = {"shifts": 0, "hours": 0.0, "reports": 0, "tasks": 0}

            daily[d]["shifts"] += 1
            daily[d]["hours"] += (shift.get("duration") or 0) / 60

        for report in m["reports"]:
            d = report.get("date")
            if d and d in daily:
                daily[d]["reports"] += 1

        for act in m["checklist"]:
            d = act.get("date")
            if d and d in daily:
                daily[d]["tasks"] += 1

    headers = ["Дата", "Смен", "Часов", "Отчётов", "Задач"]
    _style_header_row(ws_dynamics, 4, headers)

    row_index = 5

    for d in sorted(daily.keys()):
        item = daily[d]
        values = [
            d,
            item["shifts"],
            _num(item["hours"], 1),
            item["reports"],
            item["tasks"],
        ]

        _style_data_row(ws_dynamics, row_index, values, zebra=(row_index % 2 == 0))
        row_index += 1

    _auto_width(ws_dynamics)

    # ---------- ЛИСТ 7: МЕТОДИКА ----------
    ws_methodology = wb.create_sheet("Методика")

    _style_title(ws_methodology, 1, 1, "Методика расчётов")
    _style_subtitle(ws_methodology, 2, 1, f"Период: {date_from} — {date_to}")

    notes = [
        "Часы считаются по плановой длительности смены из типа смены.",
        "Процент отчётов = доля дат со сменами, где есть хотя бы один отчёт.",
        "В чек-листах учитываются только записи со статусом completed = 1.",
        "Отчёт сформирован автоматически админ-панелью бота.",
    ]

    row_index = 4

    for note in notes:
        cell = ws.cell(row=row_index, column=1, value=note)
        cell.font = Font(name=FONT_NAME, size=10, color=COLOR_DARK)
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
        ws.row_dimensions[row_index].height = 20
        row_index += 1

    _auto_width(ws_methodology, min_width=20, max_width=100)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


# =========================================================
# XLSX: ОТЧЁТ ПО ОДНОМУ СОТРУДНИКУ
# =========================================================
def generate_employee_report(user_id: int, period_days: int = 30) -> bytes:
    wb = Workbook()

    user = get_user(user_id) or {"tg_id": user_id}
    date_from, date_to = _period_range(period_days)

    info = get_employee_full_info(user_id) or {}
    shifts = get_employee_shifts(user_id, date_from, date_to)
    reports = get_employee_reports(user_id, date_from, date_to)
    checklist = get_employee_checklist_activity(user_id, date_from, date_to)

    total_hours = sum((s.get("duration") or 0) / 60 for s in shifts)
    shift_dates = {s["date"] for s in shifts if s.get("date")}
    report_dates = {r["date"] for r in reports if r.get("date")}
    covered = shift_dates & report_dates
    report_coverage = _num(len(covered) / len(shift_dates) * 100, 1) if shift_dates else None

    name = user.get("full_name") or user.get("first_name") or str(user_id)

    # ---------- ЛИСТ 1: ПРОФИЛЬ ----------
    ws = wb.active
    ws.title = "Профиль"

    _style_title(ws, 1, 1, name)
    _style_subtitle(ws, 2, 1, f"Отчёт за период {date_from} — {date_to}")

    rows = [
        ("ФИО", _safe(info.get("full_name"))),
        ("Позиция", _safe(info.get("position"))),
        ("Статус", _safe(info.get("status"))),
        ("Телефон", _safe(info.get("phone"))),
        ("Дата рождения", _safe(info.get("birthday"))),
        ("Адрес", _safe(info.get("address"))),
        ("Обязанности", _safe(info.get("responsibilities"))),
        ("Комментарий админа", _safe(info.get("admin_comment"))),
    ]

    row_index = 4

    for label, value in rows:
        _style_metric_row(ws, row_index, label, value, zebra=(row_index % 2 == 0))
        row_index += 1

    _auto_width(ws, max_width=60)

    # ---------- ЛИСТ 2: СВОДКА ----------
    ws_kpi = wb.create_sheet("Сводка")

    sections = [
        (
            "Период",
            [
                ("Дата начала", date_from),
                ("Дата конца", date_to),
                ("Дней", period_days),
            ],
        ),
        (
            "Работа",
            [
                ("Смен", len(shifts)),
                ("Часов", _num(total_hours, 1)),
                ("Средняя смена, ч", _num(total_hours / len(shifts), 1) if shifts else 0),
            ],
        ),
        (
            "Процессы",
            [
                ("Отчётов", len(reports)),
                ("Покрытие смен отчётами", _safe_percent(report_coverage)),
                ("Выполнено задач", len(checklist)),
                ("Задач с фото", sum(1 for a in checklist if a.get("has_photo"))),
            ],
        ),
    ]

    _write_sections_sheet(ws_kpi, "Сводка", f"Сотрудник: {name}", sections)

    # ---------- ЛИСТ 3: СМЕНЫ ----------
    ws_shifts = wb.create_sheet("Смены")

    _style_title(ws_shifts, 1, 1, "Смены")
    _style_subtitle(ws_shifts, 2, 1, f"Период: {date_from} — {date_to}")

    headers = ["Дата", "Смена", "Локация", "Начало", "Часов", "Активна"]
    _style_header_row(ws_shifts, 4, headers)

    row_index = 5

    for shift in shifts:
        values = [
            _safe(shift.get("date")),
            _safe(shift.get("shift_name")),
            _normalize_location(shift.get("location")),
            _safe(shift.get("start_time")),
            _num((shift.get("duration") or 0) / 60, 1),
            "Да" if shift.get("active") else "Закрыта",
        ]

        _style_data_row(ws_shifts, row_index, values, zebra=(row_index % 2 == 0))
        row_index += 1

    _auto_width(ws_shifts)

    # ---------- ЛИСТ 4: ОТЧЁТЫ ----------
    ws_reports = wb.create_sheet("Отчёты")

    _style_title(ws_reports, 1, 1, "Отчёты")
    _style_subtitle(ws_reports, 2, 1, f"Период: {date_from} — {date_to}")

    headers = ["Дата", "Тип", "Длина текста", "Текст"]
    _style_header_row(ws_reports, 4, headers)

    row_index = 5

    for report in reports:
        report_type = "Открытие" if report.get("report_type") == "opening" else "Закрытие"
        full_text = _safe(report.get("full_text"))

        values = [
            _safe(report.get("date")),
            report_type,
            len(full_text),
            _truncate(full_text, 700),
        ]

        _style_data_row(ws_reports, row_index, values, zebra=(row_index % 2 == 0))
        row_index += 1

    _auto_width(ws_reports, max_width=80)

    # ---------- ЛИСТ 5: ЧЕК-ЛИСТЫ ----------
    ws_check = wb.create_sheet("Чек-листы")

    _style_title(ws_check, 1, 1, "Чек-листы")
    _style_subtitle(ws_check, 2, 1, f"Период: {date_from} — {date_to}")

    headers = ["Дата", "Задача", "Локация", "Категория", "Время", "Фото"]
    _style_header_row(ws_check, 4, headers)

    row_index = 5

    for act in checklist:
        values = [
            _safe(act.get("date")),
            _safe(act.get("item_text")),
            _normalize_location(act.get("location")),
            _safe(act.get("category")),
            _safe(act.get("completed_at")),
            "📷 Есть" if act.get("has_photo") else "—",
        ]

        _style_data_row(ws_check, row_index, values, zebra=(row_index % 2 == 0))
        row_index += 1

    _auto_width(ws_check, max_width=60)

    # ---------- ЛИСТ 6: МЕТОДИКА ----------
    ws_methodology = wb.create_sheet("Методика")

    _style_title(ws_methodology, 1, 1, "Методика расчётов")
    _style_subtitle(ws_methodology, 2, 1, f"Период: {date_from} — {date_to}")

    notes = [
        "Часы считаются по плановой длительности смены из типа смены.",
        "Процент отчётов = доля дат со сменами, где есть хотя бы один отчёт.",
        "В чек-листах учитываются только записи со статусом completed = 1.",
        "Отчёт сформирован автоматически админ-панелью бота.",
    ]

    row_index = 4

    for note in notes:
        cell = ws.cell(row=row_index, column=1, value=note)
        cell.font = Font(name=FONT_NAME, size=10, color=COLOR_DARK)
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
        ws.row_dimensions[row_index].height = 20
        row_index += 1

    _auto_width(ws_methodology, min_width=20, max_width=100)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


# =========================================================
# УДАЛЕНИЕ СОТРУДНИКА
# =========================================================
def delete_employee_completely(tg_id: int) -> None:
    """
    Полное удаление сотрудника со всей историей:
    - смены
    - отчёты
    - прогресс чек-листов (как completed_by)
    - профиль (таблица users)
    """
    with get_connection() as conn:
        conn.execute("DELETE FROM shifts WHERE user_id = ?", (tg_id,))
        logger.info("Удалены смены для %s", tg_id)

        conn.execute("DELETE FROM shift_reports WHERE author_id = ?", (tg_id,))
        logger.info("Удалены отчёты для %s", tg_id)

        conn.execute(
            "UPDATE checklist_shared_progress SET completed_by = NULL WHERE completed_by = ?",
            (tg_id,)
        )
        logger.info("Обнулены completed_by для %s", tg_id)

        conn.execute("DELETE FROM users WHERE tg_id = ?", (tg_id,))
        logger.info("Удалён пользователь %s", tg_id)

        conn.commit()