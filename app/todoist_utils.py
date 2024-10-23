import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import pytz

load_dotenv()

API_TOKEN = os.getenv('TODOIST_KEY')
API_URL_SYNC = 'https://api.todoist.com/sync/v9/sync'
API_URL_COMPLETED = 'https://api.todoist.com/sync/v9/completed/get_all'

def get_completed_tasks(since=None, until=None, label_name=None, project_name=None):
    """Получает выполненные задачи с возможностью фильтрации по дате, лейблу и проекту."""
    headers = {
        "Authorization": f"Bearer {API_TOKEN}"
    }
    params = {
        'since': since.isoformat(timespec='seconds') + 'Z' if since else None,
        'until': until.isoformat(timespec='seconds') + 'Z' if until else None,
        'limit': 200
    }
    response = requests.get(API_URL_COMPLETED, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    tasks = data.get('items', [])
    df_tasks = pd.DataFrame(tasks)

    # Получаем дополнительные данные для фильтрации
    df_projects = get_project_data()

    # Объединяем данные задач с проектами
    df_tasks = df_tasks.merge(
        df_projects[['id', 'name']],
        left_on='project_id',
        right_on='id',
        how='left',
        suffixes=('_task', '_project')
    ).rename(columns={'name': 'project_name'})

    # Если нужно фильтровать по имени проекта
    if project_name:
        df_tasks = df_tasks[df_tasks['project_name'] == project_name]

    # Фильтрация по лейблу невозможна для выполненных задач, так как API не предоставляет эту информацию

    return df_tasks

def get_all_active_tasks():
    """Получает все активные (невыполненные) задачи."""
    headers = {
        "Authorization": f"Bearer {API_TOKEN}"
    }
    data = {
        "sync_token": "*",
        "resource_types": '["items"]'
    }
    response = requests.post(API_URL_SYNC, headers=headers, data=data)
    response.raise_for_status()
    data = response.json()
    tasks = data.get('items', [])
    df = pd.DataFrame(tasks)
    return df

def get_project_data():
    """Получает данные о проектах."""
    headers = {
        "Authorization": f"Bearer {API_TOKEN}"
    }
    data = {
        "sync_token": "*",
        "resource_types": '["projects"]'
    }
    response = requests.post(API_URL_SYNC, headers=headers, data=data)
    response.raise_for_status()
    data = response.json()
    projects = data.get('projects', [])
    df = pd.DataFrame(projects)
    return df

def get_labels_data():
    """Получает данные о лейблах."""
    headers = {
        "Authorization": f"Bearer {API_TOKEN}"
    }
    data = {
        "sync_token": "*",
        "resource_types": '["labels"]'
    }
    response = requests.post(API_URL_SYNC, headers=headers, data=data)  # Добавляем запрос
    response.raise_for_status()
    data = response.json()
    labels = data.get('labels', [])
    df = pd.DataFrame(labels)
    return df

def completed_task_statistics(n_days=7, project_name=None):
    """Статистика выполненных задач с настройками."""
    since = datetime.now(timezone.utc) - timedelta(days=n_days)
    completed_tasks = get_completed_tasks(since=since, project_name=project_name)
    total_tasks = len(completed_tasks)

    report = f"Статистика выполненных задач за последние {n_days} дней:\n"
    report += f"— Всего выполнено задач: {total_tasks}\n"

    if total_tasks > 0:
        # Группировка по проектам
        tasks_per_project = completed_tasks.groupby('project_name')['task_id'].count().reset_index()
        tasks_per_project = tasks_per_project.sort_values(by='task_id', ascending=False)

        report += "— По проектам:\n"
        for _, row in tasks_per_project.iterrows():
            report += f"  Проект '{row['project_name']}': {row['task_id']} задач(и)\n"

        # Добавим конкретные задачи в отчет
        report += "\n— Список выполненных задач:\n"
        for _, task in completed_tasks.iterrows():
            report += f"  - {task['content']} (выполнено: {task['completed_at']})\n"

    return report

def overdue_tasks_statistics(project_name=None, label_name=None):
    """Статистика по просроченным задачам с настройками."""
    tasks = get_all_active_tasks()

    if tasks.empty:
        return "— Нет активных задач.\n"

    # Обработка поля 'due'
    tasks['due_date_utc'] = tasks['due'].apply(
    lambda x: pd.to_datetime(x['date']).tz_localize('UTC') if pd.notnull(x) and x.get('date') else None
)

    now = datetime.now(timezone.utc)

    overdue_tasks = tasks[(tasks['due_date_utc'] < now) & (tasks['due_date_utc'].notnull()) & (tasks['checked'] == False)]

    # Фильтрация по проекту
    if project_name:
        df_projects = get_project_data()
        overdue_tasks = overdue_tasks.merge(
            df_projects[['id', 'name']],
            left_on='project_id',
            right_on='id',
            how='left',
            suffixes=('_task', '_project')
        )
        overdue_tasks = overdue_tasks[overdue_tasks['name'] == project_name]

    # Фильтрация по лейблу
    if label_name:
        overdue_tasks = overdue_tasks.explode('labels')
        df_labels = get_labels_data()
        overdue_tasks = overdue_tasks.merge(
            df_labels[['id', 'name']],
            left_on='labels',
            right_on='id',
            how='left',
            suffixes=('', '_label')
        ).rename(columns={'name_label': 'label_name'})
        overdue_tasks = overdue_tasks[overdue_tasks['label_name'] == label_name]

    total_overdue = len(overdue_tasks)
    report = f"— Просроченные задачи: {total_overdue}\n"

    # Если есть просроченные задачи, выведем их список
    if total_overdue > 0:
        report += "\n— Список просроченных задач:\n"
        for _, task in overdue_tasks.iterrows():
            report += f"  - {task['content']} (дедлайн был: {task['due']['date']})\n"

    return report

def productivity_recommendations(n_days=7, project_name=None):
    """Рекомендации по продуктивности с настройками."""
    since = datetime.now(timezone.utc) - timedelta(days=n_days)
    completed_tasks = get_completed_tasks(since=since, project_name=project_name)
    
    # Так как 'priority' отсутствует, даем общую рекомендацию
    recommendation = "Рекомендация: Продолжайте следить за приоритетами задач и стараться выполнять самые важные в первую очередь."

    if len(completed_tasks) == 0:
        recommendation += "\n— На данный момент нет выполненных задач. Попробуйте сосредоточиться на небольших, но важных задачах для повышения продуктивности."

    return recommendation

def tasks_due_soon(days=3, project_name=None, label_name=None):
    """Задачи, срок выполнения которых истекает скоро."""
    tasks = get_all_active_tasks()

    if tasks.empty:
        return "— Нет активных задач.\n"

    # Обработка поля 'due'
    tasks['due_date_utc'] = tasks['due'].apply(
    lambda x: pd.to_datetime(x['date']).tz_localize('UTC') if pd.notnull(x) and x.get('date') else None
)

    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=days)
    due_soon_tasks = tasks[(tasks['due_date_utc'] <= soon) & (tasks['due_date_utc'] >= now) & (tasks['checked'] == False)]

    # Фильтрация по проекту
    if project_name:
        df_projects = get_project_data()
        due_soon_tasks = due_soon_tasks.merge(
            df_projects[['id', 'name']],
            left_on='project_id',
            right_on='id',
            how='left',
            suffixes=('_task', '_project')
        )
        due_soon_tasks = due_soon_tasks[due_soon_tasks['name'] == project_name]

    # Фильтрация по лейблу
    if label_name:
        due_soon_tasks = due_soon_tasks.explode('labels')
        df_labels = get_labels_data()
        due_soon_tasks = due_soon_tasks.merge(
            df_labels[['id', 'name']],
            left_on='labels',
            right_on='id',
            how='left',
            suffixes=('', '_label')
        ).rename(columns={'name_label': 'label_name'})
        due_soon_tasks = due_soon_tasks[due_soon_tasks['label_name'] == label_name]

    total_due_soon = len(due_soon_tasks)
    report = f"— Задачи, срок выполнения которых истекает в ближайшие {days} дней: {total_due_soon}\n"

    # Выведем список задач с ближайшим сроком выполнения
    if total_due_soon > 0:
        report += "\n— Список задач с ближайшим дедлайном:\n"
        for _, task in due_soon_tasks.iterrows():
            report += f"  - {task['content']} (дедлайн: {task['due']['date']})\n"

    return report

def generate_custom_report(n_days=7, project_name=None):
    """Генерирует кастомный отчёт по задачам с настройками."""
    report = f"Отчёт за последние {n_days} дней:\n"
    report += completed_task_statistics(n_days=n_days, project_name=project_name)
    report += overdue_tasks_statistics(project_name=project_name)
    report += productivity_recommendations(n_days=n_days, project_name=project_name)
    report += tasks_due_soon(days=3, project_name=project_name)
    return report
