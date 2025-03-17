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

# Инициализация менеджера сессий
session_manager = SessionManager()

# Получаем токен бота из переменных окружения
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    logger.error("Не найден токен Telegram бота. Установите переменную окружения TELEGRAM_BOT_TOKEN.")
    raise ValueError("Не найден токен Telegram бота. Пожалуйста, установите переменную окружения TELEGRAM_BOT_TOKEN.")

def format_timestamp(timestamp_str):
    """Преобразует ISO timestamp в читаемый формат"""
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return timestamp_str

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
        "/relation_change [аспект] [изменение] - Изменить отношение персонажа\n"
        "  Аспекты: rapport, respect, trust, liking, patience\n"
        "  Изменение: число от -0.3 до 0.3\n"
        "  Пример: /relation_change respect 0.1\n"
        "/memories - Показать список эпизодических воспоминаний\n"
        "/memory_add [текст] [важность] - Добавить воспоминание\n"
        "  Важность: число от 0.1 до 0.9\n"
        "  Пример: /memory_add 'Мы говорили о музыке' 0.5\n"
        "/memory_clear - Очистить эпизодическую память\n"
        "/save - Сохранить текущее состояние\n"
        "/providers - Показать доступные LLM провайдеры\n\n"
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
        logger.error(f"Ошибка при смене модели: {str(e)}")
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
    
    # Добавляем инструкцию по изменению отношений
    relationship_text += "\nДля изменения отношений используйте команду:\n"
    relationship_text += "/relation_change [аспект] [изменение]\n"
    relationship_text += "Например: /relation_change trust 0.2"
    
    await update.message.reply_text(relationship_text)

async def relation_change_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /relation_change [аспект] [изменение]"""
    user_id = str(update.effective_user.id)
    args = context.args
    
    # Проверяем аргументы
    if not args or len(args) < 2:
        await update.message.reply_text(
            "Использование: /relation_change [аспект] [изменение]\n"
            "Доступные аспекты: rapport, respect, trust, liking, patience\n"
            "Изменение: число от -0.3 до 0.3\n"
            "Например: /relation_change trust 0.2"
        )
        return
    
    aspect = args[0].lower()
    
    # Проверяем корректность аспекта
    valid_aspects = ["rapport", "respect", "trust", "liking", "patience"]
    if aspect not in valid_aspects:
        await update.message.reply_text(
            f"Ошибка: неизвестный аспект '{aspect}'.\n"
            f"Доступные аспекты: {', '.join(valid_aspects)}"
        )
        return
    
    # Проверяем корректность изменения
    try:
        change = float(args[1])
        if change < -0.3 or change > 0.3:
            await update.message.reply_text(
                "Изменение должно быть в диапазоне от -0.3 до 0.3"
            )
            return
    except ValueError:
        await update.message.reply_text(
            "Ошибка: изменение должно быть числом (например, 0.1 или -0.2)"
        )
        return
    
    # Получаем агента и обновляем отношения
    agent = session_manager.get_agent_for_user(user_id)
    
    try:
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
            await update.message.reply_text(
                f"{aspect_name} {direction} на {abs(change):.2f}. Новое значение: {new_value:.2f}"
            )
            
            # Добавляем эпизодическое воспоминание об изменении отношений
            memory_text = f"[(Cheat)Ручное изменение отношения]: {aspect_name} было {direction} на {abs(change):.2f}"
            agent.add_episodic_memory(memory_text, importance=0.7, category="отношения")
        else:
            await update.message.reply_text(f"Ошибка при изменении отношений.")
    except Exception as e:
        logger.error(f"Ошибка при изменении отношений: {str(e)}")
        await update.message.reply_text(f"Произошла ошибка: {str(e)}")

async def memories_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /memories - показывает список эпизодических воспоминаний"""
    user_id = str(update.effective_user.id)
    
    try:
        # Получаем агента 
        agent = session_manager.get_agent_for_user(user_id)
        
        # Получаем список воспоминаний через метод get_episodic_memories
        try:
            memories = agent.get_episodic_memories(sort_by="importance")
        except Exception as e:
            logger.error(f"Ошибка при получении воспоминаний: {str(e)}")
            # Пробуем получить воспоминания напрямую через memory.episodic_memory
            if hasattr(agent.memory, 'episodic_memory'):
                memories = agent.memory.episodic_memory.sort(sort_by="importance")
            else:
                memories = []
        
        if not memories:
            await update.message.reply_text(
                "У персонажа пока нет эпизодических воспоминаний.\n\n"
                "Чтобы добавить воспоминание, используйте команду:\n"
                "/memory_add [текст] [важность]\n"
                "Например: /memory_add 'Мы говорили о музыке' 0.7"
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
                timestamp = format_timestamp(timestamp)
            
            importance = memory.get("importance", 0)
            category = memory.get("category", "без категории")
            
            memory_text += f"{i+1}. [{timestamp}] {text}\n"
            memory_text += f"   Важность: {importance:.2f}, Категория: {category}\n\n"
        
        if len(memories) > show_count:
            memory_text += f"(показано {show_count} из {len(memories)} воспоминаний)\n"
        
        # Добавляем инструкции по управлению памятью
        memory_text += "\nКоманды для управления памятью:\n"
        memory_text += "/memory_add [текст] [важность] - Добавить воспоминание\n"
        memory_text += "/memory_clear - Очистить всю эпизодическую память"
        
        await update.message.reply_text(memory_text)
    
    except Exception as e:
        logger.error(f"Ошибка при выполнении команды memories: {str(e)}")
        await update.message.reply_text(f"Произошла ошибка при получении воспоминаний: {str(e)}")

async def memory_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /memory_add [текст] [важность]"""
    user_id = str(update.effective_user.id)
    args = context.args
    
    # Проверяем наличие аргументов
    if not args:
        await update.message.reply_text(
            "Использование: /memory_add [текст] [важность]\n"
            "Например: /memory_add 'Мы говорили о философии' 0.7\n\n"
            "Важность должна быть числом от 0.1 до 0.9"
        )
        return
    
    # Пытаемся извлечь важность из последнего аргумента
    try:
        importance = float(args[-1])
        if importance < 0.1 or importance > 0.9:
            raise ValueError("Важность должна быть от 0.1 до 0.9")
        
        # Извлекаем текст воспоминания (все аргументы кроме последнего)
        memory_text = " ".join(args[:-1])
        
        # Если текст пустой, используем все аргументы и важность по умолчанию
        if not memory_text:
            memory_text = " ".join(args)
            importance = 0.5
    except ValueError:
        # Если последний аргумент не число, используем все аргументы как текст
        memory_text = " ".join(args)
        importance = 0.5
    
    # Получаем агента и добавляем воспоминание
    agent = session_manager.get_agent_for_user(user_id)
    try:
        idx = agent.add_episodic_memory(memory_text, importance=importance)
        
        await update.message.reply_text(
            f"Воспоминание успешно добавлено персонажу {agent.character_name} с важностью {importance:.1f}."
        )
    except Exception as e:
        logger.error(f"Ошибка при добавлении воспоминания: {str(e)}")
        await update.message.reply_text(f"Произошла ошибка при добавлении воспоминания: {str(e)}")

async def memory_clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /memory_clear"""
    user_id = str(update.effective_user.id)
    
    # Запрашиваем подтверждение
    await update.message.reply_text(
        "Вы уверены, что хотите очистить всю эпизодическую память персонажа?\n"
        "Это действие нельзя отменить.\n\n"
        "Для подтверждения отправьте /memory_clear_confirm"
    )

async def memory_clear_confirm_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /memory_clear_confirm"""
    user_id = str(update.effective_user.id)
    
    # Получаем агента и очищаем память
    agent = session_manager.get_agent_for_user(user_id)
    try:
        count = agent.clear_episodic_memories()
        
        await update.message.reply_text(
            f"Эпизодическая память персонажа {agent.character_name} очищена. Удалено {count} воспоминаний."
        )
    except Exception as e:
        logger.error(f"Ошибка при очистке памяти: {str(e)}")
        await update.message.reply_text(f"Произошла ошибка при очистке памяти: {str(e)}")

async def save_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /save"""
    user_id = str(update.effective_user.id)
    
    # Получаем агента и сохраняем его состояние
    agent = session_manager.get_agent_for_user(user_id)
    try:
        agent.save_state()
        
        await update.message.reply_text(
            f"Состояние персонажа {agent.character_name} успешно сохранено."
        )
    except Exception as e:
        logger.error(f"Ошибка при сохранении состояния: {str(e)}")
        await update.message.reply_text(f"Произошла ошибка при сохранении состояния: {str(e)}")

# Добавьте эту новую функцию в ваш telegram_bot.py
async def keep_typing(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Продолжает показывать статус 'печатает...' пока обрабатывается запрос"""
    try:
        while True:
            await context.bot.send_chat_action(
                chat_id=chat_id,
                action='typing'
            )
            # Обновляем статус каждые 4 секунды
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        # Задача была отменена, это нормально
        pass

# Измените функцию handle_message на следующую:
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик обычных сообщений"""
    user_id = str(update.effective_user.id)
    message_text = update.message.text
    
    # Показываем статус "печатает..." и сохраняем сообщение в переменную
    message = await update.message.reply_text("Обдумываю ответ...")
    
    # Показываем статус "печатает..." продолжительное время
    typing_task = asyncio.create_task(keep_typing(update.effective_chat.id, context))
    
    try:
        # Получаем ответ от персонажа
        response = session_manager.process_message(user_id, message_text)
        
        # Отменяем задачу с "печатает..."
        typing_task.cancel()
        
        # Отправляем ответ по частям, если он слишком длинный
        if len(response) > 4000:
            # Удаляем сообщение "Обдумываю ответ..."
            await message.delete()
            
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            # Редактируем предыдущее сообщение вместо отправки нового
            await message.edit_text(response)
        
    except asyncio.TimeoutError:
        # Отменяем задачу с "печатает..."
        typing_task.cancel()
        await message.edit_text(
            "Извините, я слишком долго думал над ответом. Пожалуйста, повторите запрос или попробуйте сформулировать короче."
        )
    except Exception as e:
        # Отменяем задачу с "печатает..."
        typing_task.cancel()
        logger.error(f"Ошибка при обработке сообщения: {str(e)}")
        await message.edit_text(
            f"Произошла ошибка при обработке вашего сообщения: {str(e)}"
        )

async def periodic_save() -> None:
    """Периодическое сохранение всех сессий"""
    while True:
        await asyncio.sleep(600)  # 10 минут
        try:
            session_manager.save_all_sessions()
            logger.info("Выполнено периодическое сохранение сессий")
        except Exception as e:
            logger.error(f"Ошибка при периодическом сохранении: {str(e)}")

async def post_init(application: Application) -> None:
    """Запуск периодического сохранения после инициализации приложения"""
    application.create_task(periodic_save())
    logger.info("Запланировано периодическое сохранение сессий")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке обновления {update}: {context.error}")
    
    # Если возможно, отправляем пользователю сообщение об ошибке
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз или обратитесь к администратору."
        )

def main() -> None:
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(TOKEN).post_init(post_init).connect_timeout(30).read_timeout(60).write_timeout(30).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("character", character_command))
    application.add_handler(CommandHandler("relationship", show_relationship))
    application.add_handler(CommandHandler("relation_change", relation_change_command))
    application.add_handler(CommandHandler("memories", memories_command))
    application.add_handler(CommandHandler("memory_add", memory_add_command))
    application.add_handler(CommandHandler("memory_clear", memory_clear_command))
    application.add_handler(CommandHandler("memory_clear_confirm", memory_clear_confirm_command))
    application.add_handler(CommandHandler("save", save_state))
    application.add_handler(CommandHandler("characters", characters_command))
    application.add_handler(CommandHandler("providers", providers_command))
    application.add_handler(CommandHandler("model", model_command))
    
    # Добавляем обработчик обычных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("Запуск бота...")
    application.run_polling()

if __name__ == "__main__":
    main()