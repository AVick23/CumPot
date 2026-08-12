from db.shifts import start_shift, get_active_shift, end_shift
from db.users import get_user
from .constants import LOCATIONS


def start_shift_for_user(user_id: int) -> bool:
    """
    Начинает смену для пользователя, если у него есть позиция.
    Возвращает True, если успешно, иначе False.
    """
    user = get_user(user_id)
    if not user:
        return False
    position = user.get("position")
    if position not in LOCATIONS:
        return False
    start_shift(user_id, position)
    return True


def get_current_shift(user_id: int) -> dict | None:
    """Возвращает текущую активную смену пользователя или None."""
    return get_active_shift(user_id)


def end_shift_for_user(user_id: int) -> bool:
    """
    Завершает активную смену пользователя.
    Возвращает True, если смена была завершена, иначе False.
    """
    shift = get_active_shift(user_id)
    if not shift:
        return False
    end_shift(user_id)
    return True


def get_position_label(position: str | None) -> str:
    """Возвращает читаемое название позиции."""
    return LOCATIONS.get(position, position or "—")