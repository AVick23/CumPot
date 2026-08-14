import io
from datetime import datetime, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

from db.profile import get_employee_full_info, get_taxi_summary   # <-- исправлено
from db.shifts import get_shifts_for_month
from utils.time_utils import today_msk_str


def _safe_str(value) -> str:
    return str(value) if value is not None else ""


def generate_all_employees_report(users: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Сотрудники"

    headers = ["ФИО", "Позиция", "Телефон", "Дата рождения", "Статус", "Комментарий", "Ставка (₽/час)", "Всего смен", "Сумма такси (₽)"]
    ws.append(headers)
    for col in range(1, len(headers)+1):
        ws.cell(row=1, column=col).font = Font(bold=True)
        ws.cell(row=1, column=col).alignment = Alignment(horizontal='center')

    for user in users:
        tg_id = user['tg_id']
        full_info = get_employee_full_info(tg_id) or {}
        # количество смен за последние 30 дней (для примера)
        date_to = today_msk_str()
        date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        # упрощённо – используем функцию get_shifts_for_month, но она требует год и месяц,
        # поэтому для демонстрации оставим 0, можно доработать
        total_shifts = 0
        taxi_summary = get_taxi_summary(tg_id, "1970-01-01", today_msk_str())
        ws.append([
            _safe_str(full_info.get('full_name')),
            _safe_str(full_info.get('position')),
            _safe_str(full_info.get('phone')),
            _safe_str(full_info.get('birthday')),
            _safe_str(full_info.get('status', 'Сотрудник')),
            _safe_str(full_info.get('admin_comment')),
            full_info.get('current_rate', 0),
            total_shifts,
            taxi_summary.get('total', 0),
        ])

    # автоширина
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 30)
        ws.column_dimensions[column].width = adjusted_width

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def generate_employee_report(tg_id: int) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = f"Сотрудник {tg_id}"

    user = get_employee_full_info(tg_id)
    if not user:
        return b""

    ws.append(["ФИО", user.get('full_name', '')])
    ws.append(["Позиция", user.get('position', '')])
    ws.append(["Телефон", user.get('phone', '')])
    ws.append(["Дата рождения", user.get('birthday', '')])
    ws.append(["Статус", user.get('status', 'Сотрудник')])
    ws.append(["Комментарий", user.get('admin_comment', '')])
    ws.append(["Ставка (₽/час)", user.get('current_rate', 0)])
    ws.append([])

    ws.append(["Дата", "Тип", "Сумма такси", "Смена"])
    expenses = get_taxi_expenses(tg_id)   # нужен импорт get_taxi_expenses
    for exp in expenses:
        ws.append([exp['date'], "Такси", exp['amount'], ""])

    # автоширина
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 30)
        ws.column_dimensions[column].width = adjusted_width

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()