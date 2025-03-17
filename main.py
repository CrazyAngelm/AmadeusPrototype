# main.py

import os
import sys
import argparse
import json
import logging
from datetime import datetime

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Импортируем необходимые модули после настройки логирования
# Сначала инициализируем загрузку персонажей из JSON
from characters import list_characters, get_character
from characters_loader import initialize_characters, create_example_characters
from agent import CharacterAgent
from llm_provider import list_available_providers


def format_timestamp(timestamp_str):
    """Преобразует ISO timestamp в читаемый формат"""
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return timestamp_str


class CharacterAgentCLI:
    """CLI-интерфейс для персонажного агента"""
    
    def __init__(self, agent, args):
        """
        Инициализация CLI-интерфейса
        
        Args:
            agent (CharacterAgent): Инициализированный агент персонажа
            args (Namespace): Аргументы командной строки
        """
        self.agent = agent
        self.character_name = agent.character_name
        self.top_k = args.top_k
        self.relevance_method = args.relevance_method
        self.min_relevance = args.min_relevance
        self.remember_interactions = not args.no_memory
        
        # Словарь с обработчиками команд
        self.commands = {
            'info': self.cmd_info,
            'set': self.cmd_set_param,
            'save': self.cmd_save,
            'help': self.cmd_help,
            'style': self.cmd_add_style_example,
            'remember': self.cmd_remember_interaction,
            'memories': self.cmd_memories,
            'characters': self.cmd_list_characters,
            'providers': self.cmd_list_providers
        }
        
        print("\n" + "-"*50)
        print(f"Агент {self.character_name} готов к работе!")
        print("Введите ваше сообщение или 'выход' для завершения.")
        print("Специальные команды: /info, /set, /save, /help, /style, /remember, /memories")
        print("-"*50 + "\n")
    
    def run(self):
        """Запуск основного цикла диалога"""
        try:
            while True:
                user_input = input("Вы: ")
                
                # Проверка на выход
                if user_input.lower() in ['выход', 'exit', 'quit', 'q']:
                    print("Сохранение состояния агента...")
                    self.agent.save_state()
                    print("Завершение работы агента. До свидания!")
                    break
                
                # Обработка специальных команд
                if user_input.startswith('/'):
                    self.handle_command(user_input[1:])
                    continue
                
                # Получение ответа от агента
                response = self.agent.process_message(
                    user_input,
                    top_k=self.top_k,
                    relevance_method=self.relevance_method,
                    min_relevance=self.min_relevance,
                    remember_interactions=self.remember_interactions
                )
                
                # Вывод ответа
                print(f"\n{self.character_name}: {response}\n")
                
                # Периодическое автосохранение (каждые 3 сообщения)
                if len(self.agent.memory.short_term_memory) % 3 == 0:
                    print("Автосохранение состояния агента...")
                    self.agent.save_state()
                    
        except KeyboardInterrupt:
            print("\nПрервано пользователем. Сохранение состояния агента...")
            self.agent.save_state()
            print("Завершение работы агента. До свидания!")
        except Exception as e:
            print(f"\nПроизошла ошибка: {str(e)}")
            print("Попытка сохранения текущего состояния агента...")
            try:
                self.agent.save_state()
                print("Состояние агента сохранено.")
            except:
                print("Не удалось сохранить состояние агента.")
    
    def handle_command(self, command_text):
        """
        Обработка команды
        
        Args:
            command_text (str): Текст команды без префикса '/'
        """
        parts = command_text.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Вызов соответствующего обработчика команды
        if cmd in self.commands:
            self.commands[cmd](args)
        else:
            print(f"Неизвестная команда: /{cmd}")
            print("Используйте /help для просмотра списка доступных команд.")
    
    def cmd_info(self, args):
        """Показать информацию о персонаже и параметрах"""
        character = get_character(self.character_name)
        
        print(f"\n--- Информация о персонаже ---")
        print(f"Имя: {self.character_name}")
        print(f"Эпоха: {character.era}")
        print(f"Описание: {character.description}")
        
        print(f"\n--- Параметры LLM ---")
        print(f"Провайдер: {self.agent.llm.provider_name}")
        print(f"Модель: {self.agent.llm.model_name}")
        print(f"Информация о модели: {self.agent.llm.get_model_info(self.agent.llm.model_name)['description']}")
        
        # Добавляем информацию о настройках LLM из персонажа
        if hasattr(character, 'llm_settings'):
            print(f"\n--- Настройки LLM персонажа ---")
            for key, value in character.llm_settings.items():
                print(f"{key}: {value}")
        
        print(f"\n--- Параметры агента ---")
        print(f"Модель эмбеддингов: {self.agent.model_name}")
        print(f"Тип индекса: {self.agent.index_type}")
        print(f"Метрика: {'косинусное сходство' if self.agent.use_cosine else 'евклидово расстояние'}")
        print(f"Текущие параметры поиска: top_k={self.top_k}, метод={self.relevance_method}, мин.релевантность={self.min_relevance}")
        print(f"Уровень стилизации: {self.agent.style_level}")
        print(f"Запоминание взаимодействий: {'Включено' if self.remember_interactions else 'Отключено'}")
        print(f"Встроенные примеры стиля: {len(character.style_examples)} | Пользовательские: {len(self.agent.custom_style_examples)}")
        
        # Информация об эпизодической памяти
        episodic_count = len(self.agent.memory.episodic_memories) if hasattr(self.agent.memory, 'episodic_memories') else 0
        print(f"Эпизодические воспоминания: {episodic_count}")
        
        print(f"--- Размер долговременной памяти ---")
        for memory_type in ["facts", "traits", "speech_patterns"]:
            print(f"  {memory_type}: {len(self.agent.memory.get_memory_texts(memory_type))} элементов")
    
    def cmd_set_param(self, args):
        """Изменение параметров агента"""
        if not args:
            print("Использование: /set [параметр] [значение]")
            print("Доступные параметры: top_k, method, min_relevance, style, remember, llm")
            return
        
        param_parts = args.split(maxsplit=1)
        if len(param_parts) != 2:
            print("Использование: /set [параметр] [значение]")
            return
            
        param, value = param_parts
        
        if param == 'top_k':
            try:
                self.top_k = int(value)
                print(f"Установлено top_k = {self.top_k}")
            except ValueError:
                print("Ошибка: top_k должно быть целым числом")
        elif param == 'method':
            if value in ['inverse', 'exponential', 'sigmoid']:
                self.relevance_method = value
                print(f"Установлен метод релевантности = {self.relevance_method}")
            else:
                print("Ошибка: метод должен быть одним из: inverse, exponential, sigmoid")
        elif param == 'min_relevance':
            try:
                self.min_relevance = float(value)
                print(f"Установлена мин. релевантность = {self.min_relevance}")
            except ValueError:
                print("Ошибка: min_relevance должно быть числом с плавающей точкой")
        elif param == 'style':
            if value in ['low', 'medium', 'high']:
                self.agent.style_level = value
                print(f"Установлен уровень стилизации = {value}")
            else:
                print("Ошибка: уровень стилизации должен быть одним из: low, medium, high")
        elif param == 'remember':
            if value.lower() in ['on', 'true', '1', 'yes']:
                self.remember_interactions = True
                print("Запоминание взаимодействий включено")
            elif value.lower() in ['off', 'false', '0', 'no']:
                self.remember_interactions = False
                print("Запоминание взаимодействий отключено")
            else:
                print("Ошибка: значение должно быть одним из: on/off, true/false, 1/0, yes/no")
        elif param == 'llm':
            # Формат: provider/model, например: openai/gpt-4o-mini или anthropic/claude-3-haiku
            if '/' in value:
                try:
                    provider, model = value.split('/', 1)
                    providers = list_available_providers()
                    if provider not in providers:
                        print(f"Ошибка: неизвестный провайдер {provider}")
                        print(f"Доступные провайдеры: {', '.join(providers.keys())}")
                        return
                    
                    print(f"Смена LLM требует перезапуска агента. Пожалуйста, перезапустите программу с параметрами:")
                    print(f"--llm-provider {provider} --llm-model {model}")
                except ValueError:
                    print("Ошибка: формат должен быть [провайдер]/[модель], например: openai/gpt-4o-mini")
            else:
                print("Ошибка: формат должен быть [провайдер]/[модель], например: openai/gpt-4o-mini")
        else:
            print(f"Неизвестный параметр: {param}")
    
    def cmd_save(self, args):
        """Сохранение состояния агента"""
        self.agent.save_state()
        print("Состояние агента сохранено.")
    
    def cmd_add_style_example(self, args):
        """Добавление примера стиля"""
        if not args:
            print("Использование: /style [сообщение пользователя] | [ответ персонажа]")
            return
        
        try:
            user_msg, char_response = args.split('|', 1)
            user_msg = user_msg.strip()
            char_response = char_response.strip()
            
            if not user_msg or not char_response:
                print("Ошибка: и сообщение пользователя, и ответ персонажа должны быть непустыми")
                return
            
            self.agent.add_style_example(user_msg, char_response)
            print("Пример стиля успешно добавлен!")
        except ValueError:
            print("Ошибка: неправильный формат. Используйте: /style [сообщение] | [ответ]")
    
    def cmd_remember_interaction(self, args):
        """Запоминание последнего взаимодействия как пример стиля"""
        if len(self.agent.memory.short_term_memory) < 2:
            print("Ошибка: нет доступных взаимодействий для запоминания")
            return
        
        try:
            # Получаем последнее взаимодействие
            last_user_msg = None
            last_char_response = None
            
            # Ищем последние сообщения пользователя и персонажа
            for msg in reversed(self.agent.memory.short_term_memory):
                if msg.startswith(f"{self.character_name}:") and not last_char_response:
                    last_char_response = msg[len(f"{self.character_name}:"):].strip()
                elif msg.startswith("Пользователь:") and not last_user_msg:
                    last_user_msg = msg[len("Пользователь:"):].strip()
                
                if last_user_msg and last_char_response:
                    break
            
            if last_user_msg and last_char_response:
                self.agent.add_style_example(last_user_msg, last_char_response)
                print("Последнее взаимодействие сохранено как пример стиля!")
            else:
                print("Не удалось найти последнее полное взаимодействие")
        except Exception as e:
            print(f"Ошибка при запоминании взаимодействия: {str(e)}")
    
    def cmd_memories(self, args):
        """Управление эпизодической памятью"""
        if not args:
            # Показываем список эпизодических воспоминаний по важности
            memories = self.agent.get_episodic_memories(sort_by="importance")
            if not memories:
                print("Эпизодическая память пуста.")
                return
            
            print("\n--- Эпизодические воспоминания ---")
            for i, memory in enumerate(memories):
                importance = memory["importance"]
                timestamp = format_timestamp(memory["timestamp"])
                category = memory.get("category", "без категории")
                emotion = memory.get("emotion", "нейтральная")
                
                # Сокращаем длинные тексты для отображения
                text = memory["text"]
                if len(text) > 100:
                    text = text[:97] + "..."
                
                print(f"{i}. [{timestamp}] {text}")
                print(f"   Важность: {importance:.2f}, Категория: {category}, Эмоция: {emotion}")
            
            print("\nИспользуйте '/memories show [индекс]' для показа полного воспоминания")
            print("Используйте '/memories add [текст] [важность 0.0-1.0] [категория] [эмоция]' для добавления")
            print("Используйте '/memories importance [индекс] [важность 0.0-1.0]' для изменения важности")
            print("Используйте '/memories clear' для очистки всей эпизодической памяти")
            return
            
        subcmd = args.split(maxsplit=1)
        if subcmd[0] == "show" and len(subcmd) > 1:
            try:
                idx = int(subcmd[1])
                memories = self.agent.get_episodic_memories()
                if 0 <= idx < len(memories):
                    memory = memories[idx]
                    print("\n--- Эпизодическое воспоминание ---")
                    print(f"Текст: {memory['text']}")
                    print(f"Дата: {format_timestamp(memory['timestamp'])}")
                    print(f"Важность: {memory['importance']:.2f}")
                    print(f"Категория: {memory.get('category', 'не указана')}")
                    print(f"Эмоция: {memory.get('emotion', 'не указана')}")
                    print(f"Обращений: {memory.get('access_count', 0)}")
                else:
                    print(f"Ошибка: индекс {idx} вне диапазона")
            except ValueError:
                print("Ошибка: индекс должен быть целым числом")
        
        elif subcmd[0] == "add" and len(subcmd) > 1:
            # Формат: /memories add [текст] [важность] [категория] [эмоция]
            parts = subcmd[1].split(maxsplit=3)
            
            if len(parts) < 1:
                print("Ошибка: укажите хотя бы текст воспоминания")
                return
            
            text = parts[0]
            importance = 0.5  # По умолчанию
            category = None
            emotion = None
            
            if len(parts) >= 2:
                try:
                    importance = float(parts[1])
                    if not (0 <= importance <= 1):
                        importance = 0.5
                except ValueError:
                    pass
            
            if len(parts) >= 3:
                category = parts[2]
            
            if len(parts) >= 4:
                emotion = parts[3]
            
            # Добавляем воспоминание
            idx = self.agent.add_episodic_memory(text, importance, category, emotion)
            print(f"Добавлено новое воспоминание (индекс: {idx}, важность: {importance:.2f})")
        
        elif subcmd[0] == "importance" and len(subcmd) > 1:
            # Формат: /memories importance [индекс] [важность]
            parts = subcmd[1].split()
            if len(parts) != 2:
                print("Ошибка: требуется индекс и новая важность")
                return
            
            try:
                idx = int(parts[0])
                importance = float(parts[1])
                
                if not (0 <= importance <= 1):
                    print("Ошибка: важность должна быть от 0.0 до 1.0")
                    return
                
                success = self.agent.update_episodic_memory_importance(idx, importance)
                if success:
                    print(f"Важность воспоминания {idx} обновлена на {importance:.2f}")
                else:
                    print(f"Ошибка: не удалось обновить важность воспоминания {idx}")
            except ValueError:
                print("Ошибка: индекс и важность должны быть числами")
        
        elif subcmd[0] == "clear":
            # Очистка всей эпизодической памяти
            confirm = input("Вы уверены, что хотите очистить всю эпизодическую память? (y/n): ")
            if confirm.lower() in ['y', 'yes', 'да']:
                count = self.agent.clear_episodic_memories()
                print(f"Эпизодическая память очищена. Удалено {count} воспоминаний.")
            else:
                print("Операция отменена.")
        
        else:
            print("Неизвестная подкоманда. Используйте '/memories' для просмотра списка воспоминаний.")
    
    def cmd_list_characters(self, args):
        """Показать список доступных персонажей"""
        available_characters = list_characters()
        print("\n--- Доступные персонажи ---")
        for name, desc in available_characters:
            character = get_character(name)
            print(f"- {name} ({character.era}): {desc}")
        print("---")
    
    def cmd_list_providers(self, args):
        """Показать список доступных LLM провайдеров"""
        available_providers = list_available_providers()
        print("\n--- Доступные LLM провайдеры ---")
        for provider, info in available_providers.items():
            print(f"\n{provider.upper()}: {info['description']}")
            for model in info['models']:
                print(f"  - {model}")
        print("---")
    
    def cmd_help(self, args):
        """Показать справку по командам"""
        print("\n--- Доступные команды ---")
        print("/info - показать информацию о текущих параметрах и персонаже")
        print("/set [параметр] [значение] - изменить параметр:")
        print("   top_k, method, min_relevance - параметры поиска")
        print("   style - уровень стилизации (low, medium, high)")
        print("   remember - включить/отключить запоминание (on/off)")
        print("   llm - сменить провайдер/модель (формат: provider/model)")
        print("/save - сохранить текущее состояние агента")
        print("/style [сообщение] | [ответ] - добавить пример стиля")
        print("/remember - сохранить последнее взаимодействие как пример стиля")
        print("/memories - управление эпизодической памятью:")
        print("   /memories - просмотр списка воспоминаний")
        print("   /memories show [индекс] - показать полное воспоминание")
        print("   /memories add [текст] [важность] [категория] [эмоция] - добавить воспоминание")
        print("   /memories importance [индекс] [важность] - изменить важность")
        print("   /memories clear - очистить всю эпизодическую память")
        print("/characters - показать список доступных персонажей")
        print("/providers - показать список доступных LLM провайдеров и моделей")
        print("/help - показать эту справку")
        print("---")


def create_argument_parser():
    """Создание парсера аргументов командной строки"""
    # Загружаем персонажей из JSON-файлов перед созданием парсера
    initialize_characters("characters")
    
    # Получение списка доступных персонажей
    available_characters = list_characters()
    character_names = [name for name, _ in available_characters]
    
    # Получение списка доступных LLM провайдеров
    available_providers = list_available_providers()
    provider_names = list(available_providers.keys())
    
    # Подготовка справки по доступным моделям
    providers_help = "Доступные LLM провайдеры и модели:\n"
    for provider, info in available_providers.items():
        providers_help += f"  {provider}: {info['description']}\n"
        for model in info['models']:
            providers_help += f"    - {model}\n"
    
    # Формирование справки по персонажам
    characters_help = "Доступные персонажи:\n"
    for name, desc in available_characters:
        characters_help += f"  - {name}: {desc}\n"
    
    # Полная справка для аргументов
    full_help = f"{providers_help}\n{characters_help}"
    
    # Разбор аргументов командной строки
    parser = argparse.ArgumentParser(
        description='Запуск персонажного агента с эпизодической памятью',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=full_help
    )
    parser.add_argument('--character', type=str, default="Шерлок Холмс", choices=character_names,
                        help='Имя персонажа')
    parser.add_argument('--reset', action='store_true', 
                        help='Сбросить память персонажа и начать заново')
    parser.add_argument('--index-type', type=str, choices=['flat', 'ivf', 'ivfpq', 'hnsw'], default='flat',
                        help='Тип индекса FAISS для векторного поиска')
    parser.add_argument('--metric', type=str, choices=['cosine', 'euclidean'], default='cosine',
                        help='Метрика расстояния для векторного поиска')
    parser.add_argument('--top-k', type=int, default=3,
                        help='Количество наиболее релевантных результатов для каждого типа памяти')
    parser.add_argument('--relevance-method', type=str, 
                        choices=['inverse', 'exponential', 'sigmoid'], default='sigmoid',
                        help='Метод расчета релевантности')
    parser.add_argument('--min-relevance', type=float, default=0.2,
                        help='Минимальное значение релевантности для включения в результаты')
    parser.add_argument('--model', type=str, default='paraphrase-multilingual-MiniLM-L12-v2',
                        help='Название модели sentence-transformers')
    parser.add_argument('--style', type=str, choices=['low', 'medium', 'high'], default='high',
                        help='Уровень стилевого кондиционирования (low, medium, high)')
    parser.add_argument('--no-memory', action='store_true',
                        help='Отключить сохранение взаимодействий в эпизодическую память')
    parser.add_argument('--list', action='store_true',
                        help='Показать список доступных персонажей и выйти')
    parser.add_argument('--llm-provider', type=str, choices=provider_names, default='openai',
                        help='Провайдер языковой модели (openai, anthropic, deepseek)')
    parser.add_argument('--llm-model', type=str, default=None,
                        help='Модель языковой модели (если не указана, используется модель по умолчанию)')
    parser.add_argument('--llm-api-key', type=str, default=None,
                        help='API ключ для провайдера (если не указан, берется из переменных окружения)')
    parser.add_argument('--providers', action='store_true',
                        help='Показать список доступных провайдеров LLM и их моделей')
    
    # Дополнительные параметры для работы с JSON-файлами персонажей
    parser.add_argument('--characters-dir', type=str, default='characters',
                      help='Директория с JSON-файлами персонажей')
    parser.add_argument('--init-examples', action='store_true',
                      help='Создать примеры JSON-файлов персонажей, если их нет')
    parser.add_argument('--convert', action='store_true',
                      help='Конвертировать встроенных персонажей в JSON-файлы')
    
    parser.add_argument('--telegram', action='store_true',
                  help='Запустить в режиме Telegram бота')
    
    return parser


def initialize_agent(args):
    """
    Инициализация агента персонажа
    
    Args:
        args (Namespace): Аргументы командной строки
        
    Returns:
        CharacterAgent: Инициализированный агент
    """
    character_name = args.character
    reset_memory = args.reset
    index_type = args.index_type
    use_cosine = args.metric == 'cosine'
    model_name = args.model
    style_level = args.style
    llm_provider = args.llm_provider
    llm_model = args.llm_model
    llm_api_key = args.llm_api_key
    
    # Проверяем, существует ли персонаж
    character = get_character(character_name)
    if not character:
        raise ValueError(f"Персонаж '{character_name}' не найден")
    
    print(f"Запуск агента для персонажа '{character_name}' ({character.era})")
    print(f"Параметры поиска: индекс={index_type}, метрика={args.metric}, "
          f"top_k={args.top_k}, релевантность={args.relevance_method}, мин.релевантность={args.min_relevance}")
    print(f"Уровень стилизации: {style_level}")
    print(f"Запоминание взаимодействий: {'Включено' if not args.no_memory else 'Отключено'}")
    print(f"LLM провайдер: {llm_provider} | Модель: {llm_model or 'по умолчанию'}")
    
    try:
        # Проверяем, нужно ли сбросить память
        if reset_memory:
            print(f"Сброс памяти для {character_name} и создание нового агента...")
            # Создаем нового агента без загрузки предыдущего состояния
            agent = CharacterAgent(
                character_name, 
                load_state=False,
                model_name=model_name,
                index_type=index_type,
                use_cosine=use_cosine,
                style_level=style_level,
                llm_provider=llm_provider,
                llm_model=llm_model,
                llm_api_key=llm_api_key
            )
        else:
            # Пытаемся загрузить существующего агента или создать нового
            agent = CharacterAgent.load_or_create(
                character_name, 
                model_name=model_name,
                index_type=index_type,
                use_cosine=use_cosine,
                style_level=style_level,
                llm_provider=llm_provider,
                llm_model=llm_model,
                llm_api_key=llm_api_key
            )
        
        return agent
    except Exception as e:
        raise RuntimeError(f"Ошибка при создании/загрузке агента: {str(e)}")


def main():
    """Основная функция запуска персонажного агента"""
    # Создаем парсер аргументов
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Создаем директорию с персонажами, если не существует
    os.makedirs(args.characters_dir, exist_ok=True)
    
    # Обрабатываем аргументы для работы с JSON-файлами персонажей
    if args.init_examples:
        print(f"Создание примеров JSON-файлов персонажей в директории {args.characters_dir}...")
        create_example_characters(args.characters_dir)
        print("Примеры персонажей созданы. Запустите программу без '--init-examples' для использования.")
        return
    
    if args.convert:
        print(f"Конвертация встроенных персонажей в JSON-файлы в директории {args.characters_dir}...")
        from characters_loader import convert_existing_characters_to_json
        convert_existing_characters_to_json(args.characters_dir)
        print("Конвертация завершена. Запустите программу без '--convert' для использования.")
        return
    
    # Если запрошен список персонажей, показываем его и выходим
    if args.list:
        print("Доступные персонажи:")
        for name, desc in list_characters():
            character = get_character(name)
            print(f"- {name} ({character.era}): {desc}")
        return
    
    # Если запрошен список провайдеров, показываем его и выходим
    if args.providers:
        print("Доступные провайдеры LLM и их модели:")
        for provider, info in list_available_providers().items():
            print(f"\n{provider.upper()}: {info['description']}")
            for model in info['models']:
                print(f"  - {model}")
        return
    
    # Если запрошен запуск Telegram бота
    if args.telegram:
        try:
            from telegram_bot import main as telegram_main
            print("Запуск Telegram бота...")
            telegram_main()
            return
        except ImportError as e:
            print(f"Ошибка импорта модуля telegram_bot: {str(e)}")
            print("Убедитесь, что установлен пакет python-telegram-bot (pip install python-telegram-bot)")
            return
    
    # Инициализируем агента
    try:
        agent = initialize_agent(args)
    except Exception as e:
        print(f"Ошибка: {str(e)}")
        return
    
    # Создаем CLI-интерфейс и запускаем диалог
    cli = CharacterAgentCLI(agent, args)
    cli.run()


if __name__ == "__main__":
    main()