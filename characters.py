# characters.py

"""
Единый модуль для работы с персонажами.
Содержит класс Character и базовые функции для работы с персонажами.
Персонажи загружаются из JSON-файлов с помощью characters_loader.py.
"""

import random
from typing import Dict, List, Any, Optional

class Character:
    """
    Класс, представляющий персонажа со всеми его данными и настройками.
    """
    
    def __init__(self, name, data, system_template, style_examples=None, era=None, description=None,
                 personality_factors=None, initial_relationship=None, llm_settings=None):
        """
        Инициализация персонажа
        
        Args:
            name (str): Имя персонажа
            data (dict): Данные о персонаже (факты, черты, речевые паттерны)
            system_template (str): Шаблон системного промпта
            style_examples (list, optional): Примеры стиля для few-shot промптинга
            era (str, optional): Эпоха персонажа (напр., "19 век", "современность")
            description (str, optional): Краткое описание персонажа
            personality_factors (dict, optional): Факторы личности, влияющие на изменение отношений
            initial_relationship (dict, optional): Начальные параметры отношений
            llm_settings (dict, optional): Настройки LLM (температура, top_p, и т.д.)
        """
        self.name = name
        self.data = data
        self.system_template = system_template
        self.style_examples = style_examples or []
        self.era = era
        self.description = description
        
        # Факторы личности, влияющие на отношения (значения от 0.0 до 1.0)
        self.personality_factors = personality_factors or {
            "intellect_appreciation": 0.5,  # ценит интеллект
            "humor_appreciation": 0.5,      # ценит юмор
            "formality_preference": 0.5,    # предпочитает формальность
            "openness": 0.5,                # открытость к новому
            "sensitivity": 0.5,             # чувствительность к обидам
            "forgiveness": 0.5              # склонность прощать
        }
        
        # Начальные параметры отношений
        self.initial_relationship = initial_relationship or {
            "rapport": 0.0,  # Общее отношение
            "aspects": {
                "respect": 0.0,    # уважение
                "trust": 0.0,      # доверие
                "liking": 0.0,     # симпатия
                "patience": 0.3    # начинаем с небольшого запаса терпения
            }
        }
        
        # Настройки LLM для данного персонажа
        self.llm_settings = llm_settings or {
            "temperature": 0.7,
            "top_p": 1.0,
            "top_k": 40,
            "max_tokens": 500,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
    
    def get_system_prompt(self, character_info, conversation_history, style_examples=None, style_level='high'):
        """
        Создает полный системный промпт для персонажа
        
        Args:
            character_info (str): Отформатированная информация о персонаже
            conversation_history (str): История разговора
            style_examples (list, optional): Дополнительные примеры стиля
            style_level (str): Уровень стилизации ('low', 'medium', 'high')
            
        Returns:
            str: Полный системный промпт
        """
        # Заполняем шаблон данными
        system_prompt = self.system_template.format(
            character_info=character_info,
            conversation_history=conversation_history
        )
        
        # Если есть примеры стиля, добавляем их
        examples_to_use = style_examples if style_examples else self.style_examples
        if examples_to_use:
            # Выбираем количество примеров в зависимости от уровня стилизации
            count_map = {'low': 1, 'medium': 2, 'high': 3}
            count = min(count_map.get(style_level, 2), len(examples_to_use))
            
            few_shot_examples = self._format_examples(examples_to_use, count)
            
            # Добавляем примеры в промпт
            system_prompt += "\n\n" + """
Примеры ответов в твоем стиле:

{examples}
""".format(examples=few_shot_examples)
        
        # Добавляем инструкции по уровню стилизации
        style_instructions = {
            'low': "Отвечай кратко и по существу, сохраняя основные черты характера.",
            'medium': "Сохраняй баланс между информативностью и стилем персонажа.",
            'high': "Максимально погрузись в роль, используя все характерные обороты и манеру речи."
        }
        
        if style_level in style_instructions:
            system_prompt += f"\n\nУровень стилизации: {style_instructions[style_level]}"
        
        return system_prompt
    
    def _format_examples(self, examples, count=2):
        """
        Форматирует примеры диалогов в текст для few-shot промпта
        
        Args:
            examples (list): Список примеров в формате словарей {user, character}
            count (int): Количество примеров для включения
            
        Returns:
            str: Отформатированный текст примеров
        """
        # Выбираем случайные примеры, если их больше чем нужно
        if len(examples) > count:
            selected_examples = random.sample(examples, count)
        else:
            selected_examples = examples
        
        formatted_text = ""
        for i, example in enumerate(selected_examples):
            formatted_text += f"Пользователь: {example['user']}\n"
            formatted_text += f"Ты ({self.name}): {example['character']}\n\n"
        
        return formatted_text.strip()


# Регистрация персонажей
CHARACTERS = {}

def register_character(character):
    """
    Регистрирует персонажа в системе
    
    Args:
        character (Character): Объект персонажа
    """
    CHARACTERS[character.name] = character

def get_character(name):
    """
    Получает персонажа по имени
    
    Args:
        name (str): Имя персонажа
        
    Returns:
        Character: Объект персонажа или None
    """
    return CHARACTERS.get(name)

def list_characters():
    """
    Возвращает список доступных персонажей
    
    Returns:
        list: Список кортежей (имя, описание)
    """
    return [(name, char.description or "Нет описания") for name, char in CHARACTERS.items()]

# Регистрация персонажей
CHARACTERS = {}

def register_character(character):
    """
    Регистрирует персонажа в системе
    
    Args:
        character (Character): Объект персонажа
    """
    CHARACTERS[character.name] = character

def get_character(name):
    """
    Получает персонажа по имени
    
    Args:
        name (str): Имя персонажа
        
    Returns:
        Character: Объект персонажа или None
    """
    return CHARACTERS.get(name)

def list_characters():
    """
    Возвращает список доступных персонажей
    
    Returns:
        list: Список кортежей (имя, описание)
    """
    return [(name, char.description or "Нет описания") for name, char in CHARACTERS.items()]

# Функция для добавления новых персонажей (пример для разработчиков)
def add_new_character(name, data, system_template, style_examples=None, era=None, description=None,
                     personality_factors=None, initial_relationship=None):
    """
    Добавляет нового персонажа в систему
    
    Args:
        name (str): Имя персонажа
        data (dict): Данные о персонаже (факты, черты, речевые паттерны)
        system_template (str): Шаблон системного промпта
        style_examples (list, optional): Примеры стиля
        era (str, optional): Эпоха персонажа
        description (str, optional): Краткое описание персонажа
        personality_factors (dict, optional): Факторы личности персонажа
        initial_relationship (dict, optional): Начальные параметры отношений
    """
    character = Character(
        name=name,
        data=data,
        system_template=system_template,
        style_examples=style_examples,
        era=era,
        description=description,
        personality_factors=personality_factors,
        initial_relationship=initial_relationship
    )
    register_character(character)
    
    return character