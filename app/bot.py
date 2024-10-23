import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram import Router
from todoist_utils import generate_custom_report, get_labels_data, get_project_data
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загрузка переменных окружения
load_dotenv()

API_TOKEN = os.getenv('TELEGRAM_KEY')

# Создаем экземпляры бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# Определяем проекты и лейблы для выбора
PROJECTS = ["Cherrypick", "Management planning", "Личный ассистент основа"]
LABELS = ["cherrypick.agency", "marketing", "waiting_list", "support_task"]

# Класс состояний для управления вводом данных
class TaskReportState(StatesGroup):
    waiting_for_days = State()
    waiting_for_project_selection = State()
    waiting_for_label_selection = State()
    waiting_for_manual_dates = State()
    waiting_for_start_date = State()
    waiting_for_end_date = State()

# Клавиатура для выбора количества дней
def days_keyboard():
    buttons = [
        KeyboardButton(text="7 дней"),
        KeyboardButton(text="14 дней"),
        KeyboardButton(text="30 дней"),
        KeyboardButton(text="Ввести вручную")
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=[buttons], resize_keyboard=True, row_width=2)
    return keyboard

# Клавиатура для выбора проекта
def projects_keyboard():
    buttons = [KeyboardButton(text=project) for project in PROJECTS]
    keyboard = ReplyKeyboardMarkup(keyboard=[buttons], resize_keyboard=True, row_width=1)
    return keyboard

# Клавиатура для выбора лейблов
def labels_keyboard():
    buttons = [KeyboardButton(text=label) for label in LABELS]
    keyboard = ReplyKeyboardMarkup(keyboard=[buttons], resize_keyboard=True, row_width=1)
    return keyboard

# Функция для отправки длинных сообщений
async def send_long_message(chat_id: int, text: str, bot: Bot, chunk_size: int = 4096):
    """Функция для отправки длинных сообщений по частям."""
    for chunk in [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]:
        await bot.send_message(chat_id, chunk)

# Команда /start — приветственное сообщение
@router.message(Command(commands=["start"]))
async def start_command(message: Message):
    await message.answer(
        "Привет! Я бот для анализа выполненных задач в Todoist. Введи /help, чтобы узнать список доступных команд."
    )

# Команда /help — список всех доступных команд
@router.message(Command(commands=["help"]))
async def help_command(message: Message):
    help_text = (
        "/start - Запустить бота и получить приветственное сообщение.\n"
        "/help - Список доступных команд и их описание.\n"
        "/tasks - Получить отчет о задачах за последние N дней.\n"
        "/tasks_by_project - Получить отчет по проекту.\n"
        "/tasks_by_label - Получить отчет по лейблу.\n"
        "/full_report - Получить полную статистику за 30 дней.\n"
        "/custom_report - Настроить и получить кастомный отчет."
    )
    await message.answer(help_text)

# Команда /tasks — получение задач за последние N дней с клавиатурой
@router.message(Command(commands=["tasks"]))
async def get_tasks_command(message: Message, state: FSMContext):
    await message.answer("Выберите количество дней для анализа или введите вручную:", reply_markup=days_keyboard())
    await state.set_state(TaskReportState.waiting_for_days)

@router.message(TaskReportState.waiting_for_days)
async def process_days_input(message: Message, state: FSMContext):
    days_mapping = {
        "7 дней": 7,
        "14 дней": 14,
        "30 дней": 30
    }

    if message.text in days_mapping:
        days = days_mapping[message.text]
        report = generate_custom_report(n_days=days)
        await send_long_message(message.chat.id, report, bot)
        await state.clear()
    elif message.text == "Ввести вручную":
        await message.answer("Введите количество дней вручную:")
    else:
        try:
            days = int(message.text)
            report = generate_custom_report(n_days=days)
            await send_long_message(message.chat.id, report, bot)
            await state.clear()
        except ValueError:
            await message.answer("Пожалуйста, введите корректное число.")

# Команда /tasks_by_project — получение задач по выбранному проекту
@router.message(Command(commands=["tasks_by_project"]))
async def get_tasks_by_project_command(message: Message, state: FSMContext):
    await message.answer("Выберите проект для анализа:", reply_markup=projects_keyboard())
    await state.set_state(TaskReportState.waiting_for_project_selection)

@router.message(TaskReportState.waiting_for_project_selection)
async def process_project_selection(message: Message, state: FSMContext):
    if message.text in PROJECTS:
        project_name = message.text
        report = generate_custom_report(project_name=project_name)
        await send_long_message(message.chat.id, report, bot)
        await state.clear()
    else:
        await message.answer("Выберите корректный проект.")

# Команда /tasks_by_label — получение задач по выбранному лейблу
@router.message(Command(commands=["tasks_by_label"]))
async def get_tasks_by_label_command(message: Message, state: FSMContext):
    await message.answer("Выберите лейбл для анализа:", reply_markup=labels_keyboard())
    await state.set_state(TaskReportState.waiting_for_label_selection)

@router.message(TaskReportState.waiting_for_label_selection)
async def process_label_selection(message: Message, state: FSMContext):
    if message.text in LABELS:
        label_name = message.text
        report = generate_custom_report(label_name=label_name)
        await send_long_message(message.chat.id, report, bot)
        await state.clear()
    else:
        await message.answer("Выберите корректный лейбл.")

# Команда /full_report — получение полной статистики без фильтров
@router.message(Command(commands=["full_report"]))
async def full_report_command(message: Message):
    report = generate_custom_report(n_days=30)
    await send_long_message(message.chat.id, report, bot)

# Функция для запуска бота
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
