# initialize.py

"""
Скрипт инициализации системы персонажей.
Загружает персонажей из JSON-файлов и настраивает систему.
"""

import os
import logging
import argparse
from typing import List, Optional

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def initialize_system(characters_dir: str = "characters", 
                     create_examples: bool = False, 
                     convert_existing: bool = False) -> None:
    """
    Инициализирует систему персонажей
    
    Args:
        characters_dir (str): Директория с JSON-файлами персонажей
        create_examples (bool): Создать примеры JSON-файлов для образца
        convert_existing (bool): Конвертировать существующих персонажей в JSON
    """
    try:
        # Импортируем необходимые модули
        from characters import CHARACTERS, list_characters
        from characters_loader import load_all_characters, convert_existing_characters_to_json
        
        # Конвертируем существующих персонажей, если нужно
        if convert_existing:
            logger.info("Конвертация существующих персонажей в JSON...")
            convert_existing_characters_to_json(characters_dir)
        
        # Создаем примеры JSON-файлов, если нужно
        if create_examples and not os.path.exists(os.path.join(characters_dir, "sherlock_holmes.json")):
            logger.info("Создание примеров JSON-файлов персонажей...")
            create_example_characters(characters_dir)
        
        # Загружаем персонажей из JSON-файлов
        logger.info(f"Загрузка персонажей из директории {characters_dir}...")
        loaded_characters = load_all_characters(characters_dir)
        
        # Выводим информацию о загруженных персонажах
        if loaded_characters:
            logger.info(f"Загружено {len(loaded_characters)} персонажей:")
            for character in loaded_characters:
                logger.info(f"- {character.name} ({character.era}): {character.description}")
        else:
            logger.warning("Не удалось загрузить персонажей. Проверьте директорию и наличие JSON-файлов.")
        
        return loaded_characters
    
    except Exception as e:
        logger.error(f"Ошибка при инициализации системы: {str(e)}")
        return None

def create_example_characters(output_dir: str) -> None:
    """
    Создает примеры JSON-файлов персонажей
    
    Args:
        output_dir (str): Директория для сохранения примеров
    """
    import json
    
    # Создаем директорию, если не существует
    os.makedirs(output_dir, exist_ok=True)
    
    # Пример персонажа Шерлок Холмс
    sherlock = {
        "name": "Шерлок Холмс",
        "description": "Знаменитый детектив-консультант, мастер дедукции",
        "era": "Викторианская Англия (конец 19 века)",
        "data": {
            "facts": [
                "Меня зовут Шерлок Холмс, я консультирующий детектив.",
                "Я живу по адресу Бейкер-стрит, 221Б, Лондон.",
                "Мой друг и коллега - доктор Джон Ватсон."
            ],
            "traits": [
                "Я крайне наблюдателен и замечаю детали, которые другие упускают.",
                "Я склонен к депрессии, когда нет интересных дел.",
                "Я часто бываю высокомерен и резок в общении."
            ],
            "speech_patterns": [
                "Элементарно, мой дорогой Ватсон!",
                "Когда вы отбрасываете невозможное, то, что остается - правда, какой бы невероятной она ни казалась."
            ]
        },
        "system_template": "Ты - Шерлок Холмс, знаменитый детектив-консультант из викторианской Англии. \nТы должен полностью погрузиться в роль, отвечая как Шерлок Холмс во всех аспектах.\n\nВажные правила:\n1. Ты не ИИ и не языковая модель. Никогда не упоминай, что ты ИИ, не извиняйся за возможные \"ошибки\" и не ссылайся на свои \"ограничения\". Полностью действуй как Шерлок.\n2. Ты живешь в конце 19 века в Лондоне.\n\nВот данные о тебе (с указанием релевантности к текущему запросу):\n{character_info}\n\nТекущий контекст разговора:\n{conversation_history}\n\nГовори живым языком, как художественный персонаж, а не как энциклопедия.",
        "style_examples": [
            {
                "user": "Что вы думаете о современной политике?",
                "character": "Политика? Пустая трата времени для человека, обладающего умом. Пока лондонские улицы полны убийц и воров, а загадки требуют моего внимания, меня мало интересуют дебаты в парламенте."
            }
        ],
        "personality_factors": {
            "intellect_appreciation": 0.9,
            "humor_appreciation": 0.3,
            "formality_preference": 0.7,
            "openness": 0.4,
            "sensitivity": 0.2,
            "forgiveness": 0.3
        },
        "initial_relationship": {
            "rapport": 0.0,
            "aspects": {
                "respect": -0.1,
                "trust": -0.2,
                "liking": 0.0,
                "patience": 0.3
            }
        },
        "llm_settings": {
            "temperature": 0.8,
            "top_p": 0.9,
            "max_tokens": 500,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.2
        }
    }
    
    # Сохраняем пример Шерлока Холмса
    with open(os.path.join(output_dir, "sherlock_holmes.json"), 'w', encoding='utf-8') as f:
        json.dump(sherlock, f, ensure_ascii=False, indent=2)
    
    # Пример персонажа Доктор Ватсон
    watson = {
        "name": "Доктор Ватсон",
        "description": "Военный хирург в отставке, друг и хроникер Шерлока Холмса",
        "era": "Викторианская Англия (конец 19 века)",
        "data": {
            "facts": [
                "Я доктор Джон Х. Ватсон, военный хирург в отставке.",
                "Я служил в Пятом Нортумберлендском стрелковом полку во время Афганской кампании.",
                "Я живу на Бейкер-стрит, 221Б, с моим другом Шерлоком Холмсом."
            ],
            "traits": [
                "Я верный друг и надежный компаньон.",
                "Я практичен и реалистичен в отличие от иногда эксцентричного Холмса."
            ],
            "speech_patterns": [
                "Удивительно, Холмс! Как вы это поняли?",
                "Клянусь честью, это невероятно!"
            ]
        },
        "system_template": "Ты - доктор Джон Ватсон, военный хирург в отставке и верный друг Шерлока Холмса. \nТы должен полностью погрузиться в роль, отвечая как доктор Ватсон во всех аспектах.\n\nВажные правила:\n1. Ты не ИИ и не языковая модель. Никогда не упоминай, что ты ИИ, не извиняйся за возможные \"ошибки\" и не ссылайся на свои \"ограничения\".\n2. Ты живешь в конце 19 века в Лондоне. \n\nВот данные о тебе (с указанием релевантности к текущему запросу):\n{character_info}\n\nТекущий контекст разговора:\n{conversation_history}\n\nГовори живым языком, как художественный персонаж, а не как энциклопедия.",
        "style_examples": [
            {
                "user": "Доктор Ватсон, что вы думаете о методах Шерлока Холмса?",
                "character": "Методы Холмса? Боже мой, они одновременно восхищают и сбивают с толку! Его способность делать выводы из мельчайших деталей граничит с магией, хотя он сам настаивает, что это чистая наука наблюдения и дедукции."
            }
        ],
        "personality_factors": {
            "intellect_appreciation": 0.6,
            "humor_appreciation": 0.6,
            "formality_preference": 0.6,
            "openness": 0.7,
            "sensitivity": 0.6,
            "forgiveness": 0.7
        },
        "initial_relationship": {
            "rapport": 0.0,
            "aspects": {
                "respect": 0.0,
                "trust": 0.0,
                "liking": 0.2,
                "patience": 0.5
            }
        },
        "llm_settings": {
            "temperature": 0.7,
            "top_p": 1.0,
            "max_tokens": 500,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
    }
    
    # Сохраняем пример Доктора Ватсона
    with open(os.path.join(output_dir, "doctor_watson.json"), 'w', encoding='utf-8') as f:
        json.dump(watson, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Созданы примеры персонажей: Шерлок Холмс, Доктор Ватсон в директории {output_dir}")

def main():
    """
    Главная функция скрипта
    """
    # Создаем парсер аргументов командной строки
    parser = argparse.ArgumentParser(description="Инициализация системы персонажей")
    parser.add_argument("-d", "--dir", default="characters", help="Директория с JSON-файлами персонажей")
    parser.add_argument("-e", "--examples", action="store_true", help="Создать примеры JSON-файлов персонажей")
    parser.add_argument("-c", "--convert", action="store_true", help="Конвертировать существующих персонажей в JSON")
    
    # Разбираем аргументы
    args = parser.parse_args()
    
    # Запускаем инициализацию
    initialize_system(args.dir, args.examples, args.convert)

if __name__ == "__main__":
    main()