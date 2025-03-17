# main.py

import os
import argparse
import json
from datetime import datetime
from characters import list_characters, get_character
from agent import CharacterAgent
from llm_provider import list_available_providers

def format_timestamp(timestamp_str):
    """Преобразует ISO timestamp в читаемый формат"""
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return timestamp_str

def main():
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
    args = parser.parse_args()
    
    # Если запрошен список персонажей, показываем его и выходим
    if args.list:
        print("Доступные персонажи:")
        for name, desc in available_characters:
            print(f"- {name}: {desc}")
        return
    
    # Если запрошен список провайдеров, показываем его и выходим
    if args.providers:
        print("Доступные провайдеры LLM и их модели:")
        for provider, info in available_providers.items():
            print(f"\n{provider.upper()}: {info['description']}")
            for model in info['models']:
                print(f"  - {model}")
        return
    
    character_name = args.character
    reset_memory = args.reset
    index_type = args.index_type
    use_cosine = args.metric == 'cosine'
    top_k = args.top_k
    relevance_method = args.relevance_method
    min_relevance = args.min_relevance
    model_name = args.model
    style_level = args.style
    remember_interactions = not args.no_memory
    llm_provider = args.llm_provider
    llm_model = args.llm_model
    llm_api_key = args.llm_api_key
    
    # Проверяем, существует ли персонаж
    character = get_character(character_name)
    if not character:
        print(f"Ошибка: Персонаж '{character_name}' не найден")
        print("Доступные персонажи:")
        for name, desc in available_characters:
            print(f"- {name}")
        return
    
    print(f"Запуск агента для персонажа '{character_name}' ({character.era})")
    print(f"Параметры поиска: индекс={index_type}, метрика={args.metric}, "
          f"top_k={top_k}, релевантность={relevance_method}, мин.релевантность={min_relevance}")
    print(f"Уровень стилизации: {style_level}")
    print(f"Запоминание взаимодействий: {'Включено' if remember_interactions else 'Отключено'}")
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
    except Exception as e:
        print(f"Ошибка при создании/загрузке агента: {str(e)}")
        return
    
    print("\n" + "-"*50)
    print(f"Агент {character_name} готов к работе!")
    print("Введите ваше сообщение или 'выход' для завершения.")
    print("Специальные команды: /info, /set, /save, /help, /style, /remember, /memories")
    print("-"*50 + "\n")
    
    # Основной цикл диалога
    try:
        while True:
            user_input = input("Вы: ")
            
            # Проверка на выход
            if user_input.lower() in ['выход', 'exit', 'quit', 'q']:
                print("Сохранение состояния агента...")
                agent.save_state()
                print("Завершение работы агента. До свидания!")
                break
            
            # Обработка специальных команд
            if user_input.startswith('/'):
                parts = user_input[1:].split(maxsplit=1)
                cmd = parts[0].lower()
                
                if cmd == 'info':
                    # Информация о текущих параметрах
                    print(f"\n--- Информация о персонаже ---")
                    print(f"Имя: {character_name}")
                    print(f"Эпоха: {character.era}")
                    print(f"Описание: {character.description}")
                    print(f"\n--- Параметры LLM ---")
                    print(f"Провайдер: {agent.llm.provider_name}")
                    print(f"Модель: {agent.llm.model_name}")
                    print(f"Информация о модели: {agent.llm.get_model_info(agent.llm.model_name)['description']}")
                    print(f"\n--- Параметры агента ---")
                    print(f"Модель эмбеддингов: {agent.model_name}")
                    print(f"Тип индекса: {agent.index_type}")
                    print(f"Метрика: {'косинусное сходство' if agent.use_cosine else 'евклидово расстояние'}")
                    print(f"Текущие параметры поиска: top_k={top_k}, метод={relevance_method}, мин.релевантность={min_relevance}")
                    print(f"Уровень стилизации: {agent.style_level}")
                    print(f"Запоминание взаимодействий: {'Включено' if remember_interactions else 'Отключено'}")
                    print(f"Встроенные примеры стиля: {len(character.style_examples)} | Пользовательские: {len(agent.custom_style_examples)}")
                    
                    # Информация об эпизодической памяти
                    episodic_count = len(agent.memory.episodic_memory) if hasattr(agent.memory, 'episodic_memory') else 0
                    print(f"Эпизодические воспоминания: {episodic_count}")
                    
                    print(f"--- Размер долговременной памяти ---")
                    for memory_type in ["facts", "traits", "speech_patterns"]:
                        print(f"  {memory_type}: {len(agent.memory.memory_texts[memory_type])} элементов")
                    continue
                
                elif cmd == 'set':
                    # Изменение параметров
                    if len(parts) < 2:
                        print("Использование: /set [параметр] [значение]")
                        print("Доступные параметры: top_k, method, min_relevance, style, remember, llm")
                        continue
                    
                    param_parts = parts[1].split(maxsplit=1)
                    if len(param_parts) != 2:
                        print("Использование: /set [параметр] [значение]")
                        continue
                        
                    param, value = param_parts
                    
                    if param == 'top_k':
                        try:
                            top_k = int(value)
                            print(f"Установлено top_k = {top_k}")
                        except ValueError:
                            print("Ошибка: top_k должно быть целым числом")
                    elif param == 'method':
                        if value in ['inverse', 'exponential', 'sigmoid']:
                            relevance_method = value
                            print(f"Установлен метод релевантности = {relevance_method}")
                        else:
                            print("Ошибка: метод должен быть одним из: inverse, exponential, sigmoid")
                    elif param == 'min_relevance':
                        try:
                            min_relevance = float(value)
                            print(f"Установлена мин. релевантность = {min_relevance}")
                        except ValueError:
                            print("Ошибка: min_relevance должно быть числом с плавающей точкой")
                    elif param == 'style':
                        if value in ['low', 'medium', 'high']:
                            agent.style_level = value
                            print(f"Установлен уровень стилизации = {value}")
                        else:
                            print("Ошибка: уровень стилизации должен быть одним из: low, medium, high")
                    elif param == 'remember':
                        if value.lower() in ['on', 'true', '1', 'yes']:
                            remember_interactions = True
                            print("Запоминание взаимодействий включено")
                        elif value.lower() in ['off', 'false', '0', 'no']:
                            remember_interactions = False
                            print("Запоминание взаимодействий отключено")
                        else:
                            print("Ошибка: значение должно быть одним из: on/off, true/false, 1/0, yes/no")
                    elif param == 'llm':
                        # Формат: provider/model, например: openai/gpt-4o-mini или anthropic/claude-3-haiku
                        if '/' in value:
                            try:
                                provider, model = value.split('/', 1)
                                if provider not in provider_names:
                                    print(f"Ошибка: неизвестный провайдер {provider}")
                                    print(f"Доступные провайдеры: {', '.join(provider_names)}")
                                    continue
                                
                                # Здесь мы бы перезагрузили агента с новым провайдером, но это сложно делать на лету
                                print(f"Смена LLM требует перезапуска агента. Пожалуйста, перезапустите программу с параметрами:")
                                print(f"--llm-provider {provider} --llm-model {model}")
                            except ValueError:
                                print("Ошибка: формат должен быть [провайдер]/[модель], например: openai/gpt-4o-mini")
                        else:
                            print("Ошибка: формат должен быть [провайдер]/[модель], например: openai/gpt-4o-mini")
                    else:
                        print(f"Неизвестный параметр: {param}")
                    
                    continue
                
                elif cmd == 'save':
                    # Принудительное сохранение
                    agent.save_state()
                    print("Состояние агента сохранено.")
                    continue
                
                elif cmd == 'style':
                    # Добавление примера стиля
                    if len(parts) < 2:
                        print("Использование: /style [сообщение пользователя] | [ответ персонажа]")
                        continue
                    
                    try:
                        user_msg, char_response = parts[1].split('|', 1)
                        user_msg = user_msg.strip()
                        char_response = char_response.strip()
                        
                        if not user_msg or not char_response:
                            print("Ошибка: и сообщение пользователя, и ответ персонажа должны быть непустыми")
                            continue
                        
                        agent.add_style_example(user_msg, char_response)
                        print("Пример стиля успешно добавлен!")
                    except ValueError:
                        print("Ошибка: неправильный формат. Используйте: /style [сообщение] | [ответ]")
                    
                    continue
                
                elif cmd == 'remember':
                    # Запоминание последнего взаимодействия как пример стиля
                    if len(agent.memory.short_term_memory) < 2:
                        print("Ошибка: нет доступных взаимодействий для запоминания")
                        continue
                    
                    try:
                        # Получаем последнее взаимодействие
                        last_user_msg = None
                        last_char_response = None
                        
                        # Ищем последние сообщения пользователя и персонажа
                        for msg in reversed(agent.memory.short_term_memory):
                            if msg.startswith(f"{character_name}:") and not last_char_response:
                                last_char_response = msg[len(f"{character_name}:"):].strip()
                            elif msg.startswith("Пользователь:") and not last_user_msg:
                                last_user_msg = msg[len("Пользователь:"):].strip()
                            
                            if last_user_msg and last_char_response:
                                break
                        
                        if last_user_msg and last_char_response:
                            agent.add_style_example(last_user_msg, last_char_response)
                            print("Последнее взаимодействие сохранено как пример стиля!")
                        else:
                            print("Не удалось найти последнее полное взаимодействие")
                    except Exception as e:
                        print(f"Ошибка при запоминании взаимодействия: {str(e)}")
                    
                    continue
                
                elif cmd == 'memories':
                    # Управление эпизодической памятью
                    if len(parts) < 2:
                        # Показываем список эпизодических воспоминаний по важности
                        memories = agent.get_episodic_memories(sort_by="importance")
                        if not memories:
                            print("Эпизодическая память пуста.")
                            continue
                        
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
                    else:
                        subcmd = parts[1].split(maxsplit=1)
                        if subcmd[0] == "show" and len(subcmd) > 1:
                            try:
                                idx = int(subcmd[1])
                                memories = agent.get_episodic_memories()
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
                                continue
                            
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
                            idx = agent.add_episodic_memory(text, importance, category, emotion)
                            print(f"Добавлено новое воспоминание (индекс: {idx}, важность: {importance:.2f})")
                        
                        elif subcmd[0] == "importance" and len(subcmd) > 1:
                            # Формат: /memories importance [индекс] [важность]
                            parts = subcmd[1].split()
                            if len(parts) != 2:
                                print("Ошибка: требуется индекс и новая важность")
                                continue
                            
                            try:
                                idx = int(parts[0])
                                importance = float(parts[1])
                                
                                if not (0 <= importance <= 1):
                                    print("Ошибка: важность должна быть от 0.0 до 1.0")
                                    continue
                                
                                success = agent.update_episodic_memory_importance(idx, importance)
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
                                count = agent.clear_episodic_memories()
                                print(f"Эпизодическая память очищена. Удалено {count} воспоминаний.")
                            else:
                                print("Операция отменена.")
                        
                        else:
                            print("Неизвестная подкоманда. Используйте '/memories' для просмотра списка воспоминаний.")
                    
                    continue
                
                elif cmd == 'characters':
                    # Показать список доступных персонажей
                    print("\n--- Доступные персонажи ---")
                    for name, desc in available_characters:
                        character = get_character(name)
                        print(f"- {name} ({character.era}): {desc}")
                    print("---")
                    continue
                
                elif cmd == 'providers':
                    # Показать список доступных LLM провайдеров
                    print("\n--- Доступные LLM провайдеры ---")
                    for provider, info in available_providers.items():
                        print(f"\n{provider.upper()}: {info['description']}")
                        for model in info['models']:
                            print(f"  - {model}")
                    print("---")
                    continue
                
                elif cmd == 'help':
                    # Справка по командам
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
                    continue
            
            # Получение ответа от агента
            response = agent.process_message(
                user_input,
                top_k=top_k,
                relevance_method=relevance_method,
                min_relevance=min_relevance,
                remember_interactions=remember_interactions
            )
            
            # Вывод ответа
            print(f"\n{character_name}: {response}\n")
            
            # Периодическое автосохранение (каждые 3 сообщения)
            if len(agent.memory.short_term_memory) % 3 == 0:
                print("Автосохранение состояния агента...")
                agent.save_state()
                
    except KeyboardInterrupt:
        print("\nПрервано пользователем. Сохранение состояния агента...")
        agent.save_state()
        print("Завершение работы агента. До свидания!")
    except Exception as e:
        print(f"\nПроизошла ошибка: {str(e)}")
        print("Попытка сохранения текущего состояния агента...")
        try:
            agent.save_state()
            print("Состояние агента сохранено.")
        except:
            print("Не удалось сохранить состояние агента.")

if __name__ == "__main__":
    main()