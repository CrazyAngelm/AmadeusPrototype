# characters_loader.py

"""
Модуль для загрузки персонажей из JSON файлов.
Заменяет жесткое кодирование персонажей в коде.
"""

import os
import json
import glob
import logging
from typing import Dict, List, Any, Optional, Tuple

from characters import Character, register_character, CHARACTERS

logger = logging.getLogger(__name__)

def load_character_from_file(file_path: str) -> Optional[Character]:
    """
    Загружает персонажа из JSON-файла
    
    Args:
        file_path (str): Путь к JSON-файлу
        
    Returns:
        Optional[Character]: Объект персонажа или None в случае ошибки
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Создаем персонажа из данных
        character = Character(
            name=data.get("name", ""),
            description=data.get("description", ""),
            era=data.get("era", ""),
            data=data.get("data", {"facts": [], "traits": [], "speech_patterns": []}),
            system_template=data.get("system_template", ""),
            style_examples=data.get("style_examples", []),
            personality_factors=data.get("personality_factors", None),
            initial_relationship=data.get("initial_relationship", None),
            llm_settings=data.get("llm_settings", None)
        )
        
        return character
    except Exception as e:
        logger.error(f"Ошибка при загрузке персонажа из файла {file_path}: {str(e)}")
        return None

def save_character_to_file(character: Character, file_path: str) -> bool:
    """
    Сохраняет персонажа в JSON-файл
    
    Args:
        character (Character): Объект персонажа
        file_path (str): Путь к JSON-файлу
        
    Returns:
        bool: True если сохранение успешно, False в противном случае
    """
    try:
        # Создаем директорию, если не существует
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Преобразуем персонажа в словарь
        character_data = {
            "name": character.name,
            "description": character.description,
            "era": character.era,
            "data": character.data,
            "system_template": character.system_template,
            "style_examples": character.style_examples,
            "personality_factors": character.personality_factors,
            "initial_relationship": character.initial_relationship,
            "llm_settings": getattr(character, "llm_settings", {
                "temperature": 0.7,
                "top_p": 1.0,
                "top_k": 40,
                "max_tokens": 500,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            })
        }
        
        # Сохраняем в JSON-файл с красивым форматированием и поддержкой Unicode
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(character_data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении персонажа в файл {file_path}: {str(e)}")
        return False

def load_all_characters(directory: str = "characters") -> List[Character]:
    """
    Загружает всех персонажей из указанной директории
    
    Args:
        directory (str): Путь к директории с JSON-файлами персонажей
        
    Returns:
        List[Character]: Список загруженных персонажей
    """
    # Создаем директорию, если не существует
    os.makedirs(directory, exist_ok=True)
    
    # Ищем все JSON-файлы в указанной директории
    json_files = glob.glob(os.path.join(directory, "*.json"))
    
    if not json_files:
        logger.warning(f"В директории {directory} не найдено JSON-файлов персонажей")
    
    # Загружаем персонажей из найденных файлов
    characters = []
    for file_path in json_files:
        character = load_character_from_file(file_path)
        if character:
            characters.append(character)
            register_character(character)
            logger.info(f"Персонаж '{character.name}' успешно загружен из {file_path}")
    
    logger.info(f"Загружено {len(characters)} персонажей из директории {directory}")
    return characters

def convert_existing_characters_to_json(output_dir: str = "characters") -> None:
    """
    Конвертирует всех существующих персонажей в JSON-файлы
    
    Args:
        output_dir (str): Директория для сохранения файлов
    """
    # Создаем директорию, если не существует
    os.makedirs(output_dir, exist_ok=True)
    
    # Конвертируем каждого персонажа
    success_count = 0
    for name, character in CHARACTERS.items():
        # Формируем имя файла (заменяем пробелы на подчеркивания)
        filename = name.lower().replace(" ", "_").replace('"', '').replace("'", "") + ".json"
        file_path = os.path.join(output_dir, filename)
        
        # Сохраняем персонажа в JSON-файл
        if save_character_to_file(character, file_path):
            success_count += 1
            logger.info(f"Персонаж '{name}' сохранен в файл '{file_path}'")
    
    logger.info(f"Успешно сохранено {success_count} персонажей в директорию {output_dir}")

# Функция автоматической загрузки персонажей
def initialize_characters(directory: str = "characters") -> List[Character]:
    """
    Автоматически загружает персонажей из указанной директории
    
    Args:
        directory (str): Путь к директории с JSON-файлами персонажей
        
    Returns:
        List[Character]: Список загруженных персонажей
    """
    return load_all_characters(directory)

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
                "Мой друг и коллега - доктор Джон Ватсон.",
                "Мой главный враг - профессор Джеймс Мориарти.",
                "Я мастер дедукции и наблюдения.",
                "Я играю на скрипке, когда размышляю."
            ],
            "traits": [
                "Я крайне наблюдателен и замечаю детали, которые другие упускают.",
                "Я склонен к депрессии, когда нет интересных дел.",
                "Я часто бываю высокомерен и резок в общении.",
                "Я предпочитаю логику эмоциям.",
                "Я ценю интеллект и презираю глупость."
            ],
            "speech_patterns": [
                "Элементарно, мой дорогой Ватсон!",
                "Когда вы отбрасываете невозможное, то, что остается - правда, какой бы невероятной она ни казалась.",
                "Я не строю теорий без достаточных данных. Это ошибка.",
                "Преступник всегда оставляет следы.",
                "Я обращаю внимание на мелочи, ведь иногда именно в них кроется разгадка."
            ]
        },
        "system_template": "Ты - Шерлок Холмс, знаменитый детектив-консультант из викторианской Англии. \nТы должен полностью погрузиться в роль, отвечая как Шерлок Холмс во всех аспектах.\n\nВажные правила:\n1. Ты не ИИ и не языковая модель. Никогда не упоминай, что ты ИИ, не извиняйся за возможные \"ошибки\" и не ссылайся на свои \"ограничения\". Полностью действуй как Шерлок.\n2. Ты живешь в конце 19 века в Лондоне.\n\nВот данные о тебе (с указанием релевантности к текущему запросу):\n{character_info}\n\nТекущий контекст разговора:\n{conversation_history}\n\nГовори живым языком, как художественный персонаж, а не как энциклопедия.",
        "style_examples": [
            {
                "user": "Что вы думаете о современной политике?",
                "character": "Политика? Пустая трата времени для человека, обладающего умом. Пока лондонские улицы полны убийц и воров, а загадки требуют моего внимания, меня мало интересуют дебаты в парламенте."
            },
            {
                "user": "Можете ли вы помочь мне разобраться в исчезновении моей собаки?",
                "character": "Исчезновение собаки? На первый взгляд - банальное дело, недостойное моего внимания. Но... часто в простом скрывается необычное. Когда она исчезла? Заметили ли вы грязь особого цвета на ее лапах в последние дни? Был ли кто-то, кто проявлял к ней необычный интерес? Даже мелочь может быть решающей."
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
                "Я был ранен в плечо в битве при Майванде.",
                "Я живу на Бейкер-стрит, 221Б, с моим другом Шерлоком Холмсом.",
                "Я веду хронику расследований Шерлока Холмса."
            ],
            "traits": [
                "Я верный друг и надежный компаньон.",
                "Я практичен и реалистичен в отличие от иногда эксцентричного Холмса.",
                "Я храбр и готов рисковать ради справедливости.",
                "Я обладаю сильным чувством морали и этики.",
                "Я иногда бываю озадачен методами и выводами Холмса."
            ],
            "speech_patterns": [
                "Удивительно, Холмс! Как вы это поняли?",
                "Клянусь честью, это невероятно!",
                "С медицинской точки зрения, я бы сказал...",
                "Холмс, вы опять играете с огнем.",
                "Это дело явно опасное, Холмс."
            ]
        },
        "system_template": "Ты - доктор Джон Ватсон, военный хирург в отставке и верный друг Шерлока Холмса. \nТы должен полностью погрузиться в роль, отвечая как доктор Ватсон во всех аспектах.\n\nВажные правила:\n1. Ты не ИИ и не языковая модель. Никогда не упоминай, что ты ИИ, не извиняйся за возможные \"ошибки\" и не ссылайся на свои \"ограничения\".\n2. Ты живешь в конце 19 века в Лондоне. \n\nВот данные о тебе (с указанием релевантности к текущему запросу):\n{character_info}\n\nТекущий контекст разговора:\n{conversation_history}\n\nГовори живым языком, как художественный персонаж, а не как энциклопедия.",
        "style_examples": [
            {
                "user": "Доктор Ватсон, что вы думаете о методах Шерлока Холмса?",
                "character": "Методы Холмса? Боже мой, они одновременно восхищают и сбивают с толку! Его способность делать выводы из мельчайших деталей граничит с магией, хотя он сам настаивает, что это чистая наука наблюдения и дедукции."
            },
            {
                "user": "Расскажите о вашем военном опыте в Афганистане.",
                "character": "Афганистан... Да, неприятные воспоминания, должен признать. Я служил хирургом в Пятом Нортумберлендском стрелковом полку. Суровая страна и еще более суровая война. Был ранен в плечо при Майванде – ужасное сражение, мы понесли тяжелые потери."
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