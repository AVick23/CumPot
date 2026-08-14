# Состояния
PROFILE_VIEW = 20
PROFILE_EDIT_NAME = 21
PROFILE_EDIT_PHONE = 22
PROFILE_EDIT_BIRTHDAY = 23
PROFILE_EDIT_ADDRESS = 24
PROFILE_EDIT_RESPONSIBILITIES = 25
PROFILE_EDIT_POSITION = 26

# Callback data
CB_PROFILE_BACK = "prof_back"
CB_PROFILE_EDIT_NAME = "prof_edit_name"
CB_PROFILE_EDIT_PHONE = "prof_edit_phone"
CB_PROFILE_EDIT_BIRTHDAY = "prof_edit_bday"
CB_PROFILE_EDIT_ADDRESS = "prof_edit_addr"
CB_PROFILE_EDIT_RESPONSIBILITIES = "prof_edit_resp"
CB_PROFILE_EDIT_POSITION = "prof_edit_pos"
CB_PROFILE_CANCEL = "prof_cancel"

# Человеческие названия полей (с иконками)
FIELD_LABELS = {
    "full_name": "👤 ФИО",
    "phone": "📞 Телефон",
    "birthday": "🎂 День рождения",
    "address": "🏠 Адрес",
    "responsibilities": "📋 Обязанности",
    "position": "💼 Позиция",
}

# Маппинг callback → (поле БД, состояние, подсказка с текущим значением)
EDIT_FIELD_MAP = {
    CB_PROFILE_EDIT_NAME: (
        "full_name",
        PROFILE_EDIT_NAME,
        "Введите новое ФИО (фамилия и имя):"
    ),
    CB_PROFILE_EDIT_PHONE: (
        "phone",
        PROFILE_EDIT_PHONE,
        "Введите номер телефона в формате +7XXXXXXXXXX:"
    ),
    CB_PROFILE_EDIT_BIRTHDAY: (
        "birthday",
        PROFILE_EDIT_BIRTHDAY,
        "Введите дату рождения в формате ГГГГ-ММ-ДД:"
    ),
    CB_PROFILE_EDIT_ADDRESS: (
        "address",
        PROFILE_EDIT_ADDRESS,
        "Введите новый адрес:"
    ),
    CB_PROFILE_EDIT_RESPONSIBILITIES: (
        "responsibilities",
        PROFILE_EDIT_RESPONSIBILITIES,
        "Введите новые обязанности (через запятую или список):"
    ),
    CB_PROFILE_EDIT_POSITION: (
        "position",
        PROFILE_EDIT_POSITION,
        "Введите позицию: bar или kitchen"
    ),
}