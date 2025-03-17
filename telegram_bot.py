# telegram_bot.py

"""
Telegram бот для общения с персонажами.
Поддерживает команды для смены персонажей, просмотра отношений и управления памятью.
"""

import os
import json
import logging
import re
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.ext import ContextTypes, filters, ConversationHandler
from session_manager import SessionManager
from characters import get_character
from llm_provider import list_available_providers

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для конечного автомата ConversationHandler
ADDING_MEMORY = 2
SETTING_IMPORTANCE = 3
SELECTING_RELATIONSHIP = 4
CHANGING_RELATIONSHIP = 5

# Инициализация менеджера сессий
session_manager = SessionManager()

# Получаем токен бота из переменных окружения
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Не найден токен Telegram бота. Пожалуйста, установите переменную окружения TELEGRAM_BOT_TOKEN.")

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = str(user.id)
    
    # Получаем агента для пользователя с персонажем по умолчанию
    agent = session_manager.get_agent_for_user(user_id)
    character_name = agent.character_name
    
    # Приветственное сообщение
    welcome_text = (
        f"Привет, {user.first_name}! 👋\n\n"
        f"Я бот для общения с различными персонажами. "
        f"Сейчас ты общаешься с персонажем {character_name}.\n\n"
        f"Просто отправь сообщение, и персонаж ответит тебе. "
        f"Используй /help чтобы узнать о доступных командах."
    )
    
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = (
        "Доступные команды:\n\n"
        "/start - Начать общение\n"
        "/help - Показать это сообщение\n"
        "/character [имя персонажа] - Сменить персонажа\n"
        "/characters - Показать список доступных персонажей\n"
        "/model [провайдер] [модель] - Выбрать провайдера и модель LLM\n"
        "/relationship - Посмотреть текущие отношения персонажа к вам\n"
        "/memories - Управление эпизодической памятью персонажа\n"
        "/clear_memory - Очистить эпизодическую память\n"
        "/save - Сохранить текущее состояние\n"
        "/providers - Показать доступные LLM провайдеры\n\n"
        "Примеры использования:\n"
        "/character Шерлок Холмс - переключиться на персонажа Шерлока Холмса\n"
        "/model openai gpt-4o-mini - переключиться на модель OpenAI GPT-4o-mini\n\n"
        "Просто отправьте сообщение, чтобы пообщаться с текущим персонажем."
    )
    
    await update.message.reply_text(help_text)

async def characters_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /characters - показывает список доступных персонажей"""
    available_characters = session_manager.get_available_characters()
    
    characters_text = "Доступные персонажи:\n\n"
    
    for name, desc in available_characters:
        # Получаем персонажа для определения эпохи
        character = get_character(name)
        era = character.era if hasattr(character, 'era') else "Неизвестная эпоха"
        
        characters_text += f"• {name} ({era})\n"
        characters_text += f"  {desc}\n\n"
    
    characters_text += "Используйте команду /character [имя персонажа] для смены персонажа."
    
    await update.message.reply_text(characters_text)

async def providers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /providers - показывает список доступных LLM провайдеров"""
    available_providers = list_available_providers()
    
    providers_text = "Доступные LLM провайдеры:\n\n"
    
    for provider, info in available_providers.items():
        providers_text += f"• {provider.upper()}: {info['description']}\n"
        providers_text += "  Модели:\n"
        
        for model in info['models']:
            providers_text += f"  - {model}\n"
        
        providers_text += "\n"
    
    providers_text += "Используйте команду /model [провайдер] [модель] для смены модели."
    
    await update.message.reply_text(providers_text)

async def character_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /character [имя персонажа]"""
    user_id = str(update.effective_user.id)
    args = context.args
    
    # Если аргументы не переданы, показываем список персонажей
    if not args:
        available_characters = session_manager.get_available_characters()
        character_list = "Для смены персонажа введите: /character [имя персонажа]\n\nДоступные персонажи:\n"
        
        for name, _ in available_characters:
            character_list += f"• {name}\n"
        
        await update.message.reply_text(character_list)
        return
    
    # Соединяем аргументы в полное имя персонажа
    character_name = " ".join(args)
    
    # Меняем персонажа
    if session_manager.change_character(user_id, character_name):
        await update.message.reply_text(f"Теперь вы общаетесь с персонажем {character_name}.")
    else:
        # Проверяем, может есть персонаж с похожим именем
        available_characters = session_manager.get_available_characters()
        character_names = [name for name, _ in available_characters]
        
        # Пытаемся найти похожее имя (без учета регистра)
        possible_matches = [name for name in character_names 
                           if character_name.lower() in name.lower()]
        
        if possible_matches:
            suggestion_text = "Персонаж не найден. Возможно, вы имели в виду:\n"
            for name in possible_matches:
                suggestion_text += f"• {name}\n"
            
            await update.message.reply_text(suggestion_text)
        else:
            await update.message.reply_text(
                f"Ошибка: персонаж '{character_name}' не найден. "
                f"Используйте /characters для просмотра списка доступных персонажей."
            )

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /model [провайдер] [модель]"""
    user_id = str(update.effective_user.id)
    args = context.args
    
    # Если аргументы не переданы, показываем информацию об использовании
    if not args or len(args) < 2:
        await update.message.reply_text(
            "Для смены модели введите: /model [провайдер] [модель]\n\n"
            "Например: /model openai gpt-4o-mini\n\n"
            "Используйте /providers для просмотра доступных провайдеров и моделей."
        )
        return
    
    provider_name = args[0].lower()
    model_name = args[1]
    
    # Если модель содержит пробелы, соединяем оставшиеся аргументы
    if len(args) > 2:
        model_name = " ".join(args[1:])
    
    # Проверяем доступность провайдера
    available_providers = list_available_providers()
    if provider_name not in available_providers:
        provider_list = ", ".join(available_providers.keys())
        await update.message.reply_text(
            f"Ошибка: провайдер '{provider_name}' не найден.\n"
            f"Доступные провайдеры: {provider_list}"
        )
        return
    
    # Меняем модель для агента пользователя
    agent = session_manager.get_agent_for_user(user_id)
    try:
        # Обновляем параметры LLM
        success = agent.setup_llm(provider_name=provider_name, model_name=model_name)
        
        if success:
            await update.message.reply_text(
                f"Модель успешно изменена на {provider_name.upper()}/{model_name}."
            )
        else:
            await update.message.reply_text(
                f"Ошибка при смене модели. Проверьте название модели и повторите попытку."
            )
    except Exception as e:
        await update.message.reply_text(f"Ошибка при смене модели: {str(e)}")

async def show_relationship(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /relationship"""
    user_id = str(update.effective_user.id)
    
    # Получаем агента и статус отношений
    agent = session_manager.get_agent_for_user(user_id)
    relationship_status = agent.get_relationship_status()
    
    # Форматируем информацию об отношениях
    character_name = agent.character_name
    overall = relationship_status['overall']
    rapport = relationship_status['rapport_value']
    
    relationship_text = f"Отношение {character_name} к вам: {overall} (уровень: {rapport:.2f})\n\n"
    
    # Аспекты отношений
    relationship_text += "Аспекты отношений:\n"
    aspects = {
        "respect": "Уважение",
        "trust": "Доверие",
        "liking": "Симпатия",
        "patience": "Терпение"
    }
    
    for aspect, title in aspects.items():
        value = relationship_status['aspect_values'].get(aspect, 0)
        desc = relationship_status['aspects'].get(aspect, "нейтральное")
        relationship_text += f"• {title}: {desc} ({value:.2f})\n"
    
    # Последнее изменение
    last_change = relationship_status.get('last_change')
    if last_change:
        when = last_change.get('when')
        reason = last_change.get('reason')
        relationship_text += f"\nПоследнее изменение:\n{reason}\n"
    
    # Создаем клавиатуру для изменения отношений
    keyboard = [[InlineKeyboardButton("Изменить отношения", callback_data="modify_relationship")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        relationship_text,
        reply_markup=reply_markup
    )

async def modify_relationship_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса изменения отношений"""
    query = update.callback_query
    await query.answer()
    
    # Создаем клавиатуру для выбора аспекта отношений
    keyboard = [
        [InlineKeyboardButton("Общее отношение", callback_data="relationship_rapport")],
        [InlineKeyboardButton("Уважение", callback_data="relationship_respect")],
        [InlineKeyboardButton("Доверие", callback_data="relationship_trust")],
        [InlineKeyboardButton("Симпатия", callback_data="relationship_liking")],
        [InlineKeyboardButton("Терпение", callback_data="relationship_patience")],
        [InlineKeyboardButton("Отмена", callback_data="relationship_cancel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Выберите аспект отношений для изменения:",
        reply_markup=reply_markup
    )
    
    return SELECTING_RELATIONSHIP

async def relationship_aspect_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик выбора аспекта отношений"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "relationship_cancel":
        await query.edit_message_text("Изменение отношений отменено.")
        return ConversationHandler.END
    
    # Извлекаем аспект из callback_data
    aspect = callback_data.replace("relationship_", "")
    context.user_data['selected_aspect'] = aspect
    
    # Создаем клавиатуру для выбора направления изменения
    keyboard = [
        [InlineKeyboardButton("Сильно улучшить (+0.3)", callback_data="change_0.3")],
        [InlineKeyboardButton("Улучшить (+0.1)", callback_data="change_0.1")],
        [InlineKeyboardButton("Немного улучшить (+0.05)", callback_data="change_0.05")],
        [InlineKeyboardButton("Немного ухудшить (-0.05)", callback_data="change_-0.05")],
        [InlineKeyboardButton("Ухудшить (-0.1)", callback_data="change_-0.1")],
        [InlineKeyboardButton("Сильно ухудшить (-0.3)", callback_data="change_-0.3")],
        [InlineKeyboardButton("Отмена", callback_data="change_cancel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    aspect_names = {
        "rapport": "общее отношение",
        "respect": "уважение",
        "trust": "доверие",
        "liking": "симпатия",
        "patience": "терпение"
    }
    
    aspect_name = aspect_names.get(aspect, aspect)
    
    await query.edit_message_text(
        f"Выберите, как изменить {aspect_name}:",
        reply_markup=reply_markup
    )
    
    return CHANGING_RELATIONSHIP

async def change_relationship(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик изменения отношений"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    callback_data = query.data
    
    if callback_data == "change_cancel":
        await query.edit_message_text("Изменение отношений отменено.")
        return ConversationHandler.END
    
    # Извлекаем величину изменения из callback_data
    change = float(callback_data.replace("change_", ""))
    aspect = context.user_data.get('selected_aspect')
    
    if not aspect:
        await query.edit_message_text("Ошибка: не выбран аспект отношений.")
        return ConversationHandler.END
    
    # Получаем агента и обновляем отношения
    agent = session_manager.get_agent_for_user(user_id)
    success = agent.update_relationship_manually(aspect, change)
    
    aspect_names = {
        "rapport": "Общее отношение",
        "respect": "Уважение",
        "trust": "Доверие",
        "liking": "Симпатия",
        "patience": "Терпение"
    }
    
    aspect_name = aspect_names.get(aspect, aspect)
    
    if success:
        # Получаем обновленный статус отношений
        status = agent.get_relationship_status()
        new_value = status['rapport_value'] if aspect == 'rapport' else status['aspect_values'].get(aspect, 0)
        
        direction = "улучшено" if change > 0 else "ухудшено"
        await query.edit_message_text(
            f"{aspect_name} {direction} на {abs(change):.2f}. Новое значение: {new_value:.2f}"
        )
        
        # Добавляем эпизодическое воспоминание об изменении отношений
        memory_text = f"[Ручное изменение отношения]: {aspect_name} было {direction} на {abs(change):.2f}"
        agent.add_episodic_memory(memory_text, importance=0.7, category="отношения")
    else:
        await query.edit_message_text(f"Ошибка при изменении отношений.")
    
    return ConversationHandler.END

async def memories_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /memories"""
    user_id = str(update.effective_user.id)
    
    # Получаем агента и эпизодические воспоминания
    agent = session_manager.get_agent_for_user(user_id)
    memories = agent.get_episodic_memories(sort_by="importance")
    
    if not memories:
        # Создаем клавиатуру для добавления воспоминания
        keyboard = [[InlineKeyboardButton("Добавить воспоминание", callback_data="add_memory")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "У персонажа пока нет эпизодических воспоминаний.",
            reply_markup=reply_markup
        )
        return
    
    # Форматируем список воспоминаний
    memory_text = f"Эпизодические воспоминания {agent.character_name}\n\n"
    
    # Показываем только первые 10 воспоминаний
    show_count = min(10, len(memories))
    for i, memory in enumerate(memories[:show_count]):
        # Форматируем текст воспоминания (сокращаем, если слишком длинный)
        text = memory["text"]
        if len(text) > 100:
            text = text[:97] + "..."
        
        # Форматируем временную метку
        timestamp = memory.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                timestamp = dt.strftime("%d.%m.%Y %H:%M")
            except:
                pass
        
        importance = memory.get("importance", 0)
        category = memory.get("category", "без категории")
        
        memory_text += f"{i+1}. [{timestamp}] {text}\n"
        memory_text += f"   Важность: {importance:.2f}, Категория: {category}\n\n"
    
    if len(memories) > show_count:
        memory_text += f"(показано {show_count} из {len(memories)} воспоминаний)\n"
    
    # Создаем клавиатуру для действий с воспоминаниями
    keyboard = [
        [InlineKeyboardButton("Добавить воспоминание", callback_data="add_memory")],
        [InlineKeyboardButton("Очистить память", callback_data="clear_memory")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        memory_text,
        reply_markup=reply_markup
    )

async def start_add_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса добавления воспоминания"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "Отправьте текст воспоминания, которое нужно добавить персонажу:"
    )
    
    return ADDING_MEMORY

async def memory_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик получения текста воспоминания"""
    memory_text = update.message.text
    context.user_data['memory_text'] = memory_text
    
    # Создаем клавиатуру для выбора важности
    keyboard = [
        [InlineKeyboardButton("Очень важное (0.9)", callback_data="importance_0.9")],
        [InlineKeyboardButton("Важное (0.7)", callback_data="importance_0.7")],
        [InlineKeyboardButton("Среднее (0.5)", callback_data="importance_0.5")],
        [InlineKeyboardButton("Маловажное (0.3)", callback_data="importance_0.3")],
        [InlineKeyboardButton("Отмена", callback_data="importance_cancel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Выберите важность воспоминания:",
        reply_markup=reply_markup
    )
    
    return SETTING_IMPORTANCE

async def memory_importance_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик выбора важности воспоминания"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    callback_data = query.data
    
    if callback_data == "importance_cancel":
        await query.edit_message_text("Добавление воспоминания отменено.")
        return ConversationHandler.END
    
    # Извлекаем важность из callback_data
    importance = float(callback_data.replace("importance_", ""))
    memory_text = context.user_data.get('memory_text', "")
    
    if not memory_text:
        await query.edit_message_text("Ошибка: текст воспоминания не найден.")
        return ConversationHandler.END
    
    # Получаем агента и добавляем воспоминание
    agent = session_manager.get_agent_for_user(user_id)
    agent.add_episodic_memory(memory_text, importance=importance)
    
    await query.edit_message_text(
        f"Воспоминание успешно добавлено персонажу {agent.character_name} с важностью {importance:.1f}."
    )
    
    return ConversationHandler.END

async def clear_memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /clear_memory - запрос на очистку памяти"""
    # Создаем клавиатуру для подтверждения
    keyboard = [
        [InlineKeyboardButton("Да, очистить", callback_data="clear_memory_confirmed")],
        [InlineKeyboardButton("Отмена", callback_data="clear_memory_cancel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Вы уверены, что хотите очистить всю эпизодическую память персонажа? Это действие нельзя отменить.",
        reply_markup=reply_markup
    )

async def clear_memory_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запрос подтверждения очистки памяти"""
    query = update.callback_query
    await query.answer()
    
    # Создаем клавиатуру для подтверждения
    keyboard = [
        [InlineKeyboardButton("Да, очистить", callback_data="clear_memory_confirmed")],
        [InlineKeyboardButton("Отмена", callback_data="clear_memory_cancel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Вы уверены, что хотите очистить всю эпизодическую память персонажа? Это действие нельзя отменить.",
        reply_markup=reply_markup
    )

async def clear_memory_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выполнение очистки памяти"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = str(query.from_user.id)
    
    if callback_data == "clear_memory_cancel":
        await query.edit_message_text("Очистка памяти отменена.")
        return
    
    # Получаем агента и очищаем память
    agent = session_manager.get_agent_for_user(user_id)
    count = agent.clear_episodic_memories()
    
    await query.edit_message_text(
        f"Эпизодическая память персонажа {agent.character_name} очищена. Удалено {count} воспоминаний."
    )

async def save_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /save"""
    user_id = str(update.effective_user.id)
    
    # Получаем агента и сохраняем его состояние
    agent = session_manager.get_agent_for_user(user_id)
    agent.save_state()
    
    await update.message.reply_text(
        f"Состояние персонажа {agent.character_name} успешно сохранено."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик обычных сообщений"""
    user_id = str(update.effective_user.id)
    message_text = update.message.text
    
    # Показываем статус "печатает..."
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action='typing'
    )
    
    # Получаем ответ от персонажа
    try:
        response = session_manager.process_message(user_id, message_text)
        
        # Отправляем ответ по частям, если он слишком длинный
        if len(response) > 4000:
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {str(e)}")
        await update.message.reply_text(
            "Произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте еще раз."
        )

async def periodic_save() -> None:
    """Периодическое сохранение всех сессий"""
    while True:
        await asyncio.sleep(600)  # 10 минут
        session_manager.save_all_sessions()
        logger.info("Выполнено периодическое сохранение сессий")

async def post_init(application: Application) -> None:
    """Запуск периодического сохранения после инициализации приложения"""
    application.create_task(periodic_save())
    logger.info("Запланировано периодическое сохранение сессий")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке обновления {update}: {context.error}")

def main() -> None:
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(TOKEN).post_init(post_init).build()
    
    # Регистрируем обработчик добавления воспоминания
    memory_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_memory, pattern=r'^add_memory$')],
        states={
            ADDING_MEMORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, memory_text_received)],
            SETTING_IMPORTANCE: [CallbackQueryHandler(memory_importance_selected, pattern=r'^importance_')]
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
        per_chat=True
    )
    
    # Регистрируем обработчик изменения отношений
    relationship_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(modify_relationship_start, pattern=r'^modify_relationship$')],
        states={
            SELECTING_RELATIONSHIP: [CallbackQueryHandler(relationship_aspect_selected, pattern=r'^relationship_')],
            CHANGING_RELATIONSHIP: [CallbackQueryHandler(change_relationship, pattern=r'^change_')]
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
        per_chat=True
    )
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("character", character_command))
    application.add_handler(CommandHandler("relationship", show_relationship))
    application.add_handler(CommandHandler("memories", memories_command))
    application.add_handler(CommandHandler("save", save_state))
    application.add_handler(CommandHandler("characters", characters_command))
    application.add_handler(CommandHandler("providers", providers_command))
    application.add_handler(CommandHandler("clear_memory", clear_memory_command))
    application.add_handler(CommandHandler("model", model_command))
    
    # Добавляем обработчики разговоров
    application.add_handler(memory_conv_handler)
    application.add_handler(relationship_conv_handler)
    
    # Добавляем обработчики callback-запросов
    application.add_handler(CallbackQueryHandler(clear_memory_confirm, pattern=r'^clear_memory$'))
    application.add_handler(CallbackQueryHandler(clear_memory_execute, pattern=r'^clear_memory_'))
    
    # Добавляем обработчик обычных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()