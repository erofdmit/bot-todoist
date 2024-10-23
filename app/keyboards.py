from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def days_keyboard():
    buttons = [
        InlineKeyboardButton(text="7 дней", callback_data="days_7"),
        InlineKeyboardButton(text="30 дней", callback_data="days_30"),
        InlineKeyboardButton(text="90 дней", callback_data="days_90"),
    ]
    keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=[buttons])
    return keyboard

def project_keyboard(projects):
    
    buttons = [InlineKeyboardButton(text=project, callback_data=f"project_{project}") for project in projects]
    keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=[buttons])
    return keyboard

def help_keyboard():
    
    buttons = [
        KeyboardButton(text="/tasks"),
        KeyboardButton(text="/improvements"),
        KeyboardButton(text="/analyze_project"),
        KeyboardButton(text="/overdue"),
        KeyboardButton(text="/avg_time")
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=[buttons], resize_keyboard=True, row_width=2)
    return keyboard
