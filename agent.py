# agent.py

import os
import json
import re
from dotenv import load_dotenv
from memory import Memory
from characters import get_character
from llm_provider import get_provider, list_available_providers
from relationship import Relationship

# Загрузка переменных окружения
load_dotenv()

class CharacterAgent:
    def __init__(self, character_name, user_id="default", load_state=True, 
                 model_name='paraphrase-multilingual-MiniLM-L12-v2', 
                 index_type='flat', use_cosine=True, 
                 style_level='high', custom_style_examples=None,
                 llm_provider='openai', llm_model=None, llm_api_key=None):
        """
        Инициализация агента-персонажа
        
        Args:
            character_name (str): Имя персонажа
            user_id (str): Идентификатор пользователя (для многопользовательских систем)
            load_state (bool): Загружать ли предыдущее состояние, если доступно
            model_name (str): Название модели sentence-transformers
            index_type (str): Тип индекса FAISS ('flat', 'ivf', 'ivfpq', 'hnsw')
            use_cosine (bool): Использовать ли косинусное сходство вместо евклидова расстояния
            style_level (str): Уровень стилизации ('low', 'medium', 'high')
            custom_style_examples (list): Пользовательские примеры стиля
            llm_provider (str): Провайдер LLM ('openai', 'anthropic', 'deepseek')
            llm_model (str): Название модели LLM (если None, используется модель по умолчанию)
            llm_api_key (str): API ключ для LLM (если None, берется из переменных окружения)
        """
        # Получаем персонажа из реестра
        self.character = get_character(character_name)
        if not self.character:
            raise ValueError(f"Персонаж '{character_name}' не найден в системе.")
        
        self.character_name = character_name
        self.user_id = user_id
        print(f"Инициализация агента {character_name} для пользователя {user_id}...")
        
        # Сохраняем параметры
        self.model_name = model_name
        self.index_type = index_type
        self.use_cosine = use_cosine
        self.style_level = style_level
        self.custom_style_examples = custom_style_examples or []
        
        # Формируем безопасное имя файла из имени персонажа и ID пользователя
        safe_character = "".join(c if c.isalnum() else "_" for c in character_name)
        safe_user = "".join(c if c.isalnum() else "_" for c in user_id)
        self.state_dir = os.path.join("character_states", safe_character, safe_user)
        self.memory_file = os.path.join(self.state_dir, "memory.pkl")
        self.style_file = os.path.join(self.state_dir, "custom_style_examples.json")
        self.relationship_file = os.path.join(self.state_dir, "relationship.json")
        
        # Создаем директорию для состояния, если она не существует
        os.makedirs(self.state_dir, exist_ok=True)
        
        # Загружаем или создаем новую память
        if load_state and os.path.exists(self.memory_file):
            # Пытаемся загрузить существующее состояние
            self.memory = Memory.load_from_file(self.memory_file)
            print(f"Загружено состояние агента {character_name} из {self.memory_file}")
        else:
            # Создаем новую память с данными персонажа
            self.memory = Memory(model_name=model_name, index_type=index_type, use_cosine=use_cosine)
            self.memory.initialize_long_term_memory(self.character.data)
            print(f"Создана новая память для агента {character_name}")
        
        # Загружаем пользовательские примеры стиля, если есть
        if custom_style_examples:
            self.custom_style_examples = custom_style_examples
            # Сохраняем пользовательские примеры
            self._save_style_examples()
        elif load_state and os.path.exists(self.style_file):
            # Загружаем существующие примеры стиля
            self._load_style_examples()
        
        # Инициализируем или загружаем отношения
        self._init_relationship(load_state)
        
        # Инициализация провайдера LLM
        self.llm_provider_name = llm_provider
        self.llm_model_name = llm_model
        
        try:
            self.llm = get_provider(
                provider_name=llm_provider, 
                model_name=llm_model,
                api_key=llm_api_key
            )
            print(f"Инициализирован LLM провайдер: {self.llm.provider_name}, модель: {self.llm.model_name}")
        except Exception as e:
            raise ValueError(f"Ошибка при инициализации LLM провайдера: {str(e)}")
        
        # Применяем затухание важности к эпизодическим воспоминаниям
        if hasattr(self.memory, 'episodic_memory') and self.memory.episodic_memory:
            self.memory.decay_episodic_memories()
        
        print(f"Агент {character_name} успешно инициализирован!")
    
    def _init_relationship(self, load_state):
        """
        Инициализирует или загружает отношения персонажа к пользователю
        
        Args:
            load_state (bool): Загружать ли существующие отношения
        """
        if load_state and os.path.exists(self.relationship_file):
            # Загружаем существующие отношения
            try:
                with open(self.relationship_file, 'r', encoding='utf-8') as f:
                    relationship_data = json.load(f)
                self.relationship = Relationship.from_dict(relationship_data)
                print(f"Загружены отношения персонажа {self.character_name} к пользователю {self.user_id}")
            except Exception as e:
                print(f"Ошибка при загрузке отношений: {str(e)}")
                self._create_new_relationship()
        else:
            # Создаем новые отношения с учетом личности персонажа
            self._create_new_relationship()
    
    def _create_new_relationship(self):
        """
        Создает новые отношения с учетом личности персонажа
        """
        # Получаем персонажа из реестра
        character = get_character(self.character_name)
        
        # Получаем факторы личности из данных персонажа
        personality_factors = character.personality_factors
        
        # Получаем начальные параметры отношений из данных персонажа
        initial_rapport = character.initial_relationship.get("rapport", 0.0)
        initial_aspects = character.initial_relationship.get("aspects", {
            "respect": 0.0,    # уважение
            "trust": 0.0,      # доверие
            "liking": 0.0,     # симпатия
            "patience": 0.3    # начинаем с небольшого запаса терпения
        })
        
        # Создаем объект отношений с параметрами из персонажа
        self.relationship = Relationship(
            character_name=self.character_name,
            initial_rapport=initial_rapport,
            initial_aspects=initial_aspects,
            personality_factors=personality_factors
        )
        
        print(f"Созданы новые отношения персонажа {self.character_name} к пользователю {self.user_id}")
    
    def _save_relationship(self):
        """
        Сохраняет текущие отношения в файл
        """
        try:
            with open(self.relationship_file, 'w', encoding='utf-8') as f:
                json.dump(self.relationship.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Ошибка при сохранении отношений: {str(e)}")
            return False
    
    def _save_style_examples(self):
        """Сохранение пользовательских примеров стиля в JSON файл"""
        try:
            with open(self.style_file, 'w', encoding='utf-8') as f:
                json.dump(self.custom_style_examples, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка при сохранении примеров стиля: {str(e)}")
    
    def _load_style_examples(self):
        """Загрузка пользовательских примеров стиля из JSON файла"""
        try:
            with open(self.style_file, 'r', encoding='utf-8') as f:
                self.custom_style_examples = json.load(f)
        except Exception as e:
            print(f"Ошибка при загрузке примеров стиля: {str(e)}")
            self.custom_style_examples = []
    
    def add_style_example(self, user_message, character_response):
        """
        Добавление нового примера стиля
        
        Args:
            user_message (str): Сообщение пользователя
            character_response (str): Ответ персонажа
        """
        self.custom_style_examples.append({
            "user": user_message,
            "character": character_response
        })
        
        # Сохраняем обновленные примеры
        self._save_style_examples()
        print(f"Добавлен новый пример стиля (всего пользовательских: {len(self.custom_style_examples)})")
    
    def _detect_important_event(self, user_message, character_response):
        """
        Определяет, является ли взаимодействие важным событием, и оценивает его важность
        
        Args:
            user_message (str): Сообщение пользователя
            character_response (str): Ответ персонажа
            
        Returns:
            tuple: (is_important, importance, category, emotion)
        """
        # Список ключевых слов, указывающих на потенциально важное взаимодействие
        important_keywords = [
            'помни', 'запомни', 'важно', 'ключевой', 'никогда', 'всегда', 'обещаю', 'клянусь',
            'личный', 'секрет', 'тайна', 'договорились', 'обещаешь', 'никому', 'доверяю', 'признаюсь',
            'должен знать', 'между нами', 'правда'
        ]
        
        # Список эмоциональных ключевых слов
        emotional_keywords = {
            'радость': ['рад', 'счастлив', 'восторг', 'доволен', 'приятно', 'замечательно'],
            'грусть': ['грустно', 'печально', 'жаль', 'сожалею', 'тоскливо', 'огорчен'],
            'злость': ['зол', 'раздражен', 'злюсь', 'бешенство', 'возмущен', 'ненавижу'],
            'страх': ['боюсь', 'страшно', 'ужас', 'опасаюсь', 'тревожно', 'паника'],
            'удивление': ['удивлен', 'поражен', 'шокирован', 'не ожидал', 'невероятно']
        }
        
        # Категории взаимодействий
        categories = {
            'личное': ['я', 'мой', 'моя', 'мне', 'меня', 'моей', 'моего', 'мои', 'моих', 'люблю', 'чувствую'],
            'отношения': ['друг', 'семья', 'любовь', 'отношения', 'близкий', 'доверие', 'мы'],
            'работа': ['работа', 'дело', 'расследование', 'проект', 'поручение', 'задача'],
            'обещание': ['обещаю', 'клянусь', 'обязуюсь', 'гарантирую', 'даю слово'],
            'тайна': ['секрет', 'тайна', 'конфиденциально', 'между нами', 'никому'],
            'опасность': ['опасно', 'угроза', 'риск', 'предупреждаю', 'осторожно', 'берегись']
        }
        
        # Объединяем сообщение и ответ для анализа
        full_interaction = f"{user_message} {character_response}".lower()
        
        # Проверяем на наличие ключевых слов, указывающих на важность
        importance_score = 0.0
        for keyword in important_keywords:
            if keyword.lower() in full_interaction:
                importance_score += 0.1  # Увеличиваем оценку за каждое ключевое слово
        
        # Ограничиваем важность диапазоном 0.3-0.9
        importance_score = min(0.9, max(0.3, importance_score))
        
        # Длина взаимодействия также может указывать на важность
        total_length = len(user_message) + len(character_response)
        if total_length > 500:  # Если взаимодействие длинное
            importance_score = min(0.9, importance_score + 0.1)
        
        # Определяем эмоцию, если есть
        emotion = None
        for emotion_name, keywords in emotional_keywords.items():
            for keyword in keywords:
                if keyword.lower() in full_interaction:
                    emotion = emotion_name
                    # Эмоциональные взаимодействия часто важнее
                    importance_score = min(0.9, importance_score + 0.1)
                    break
            if emotion:
                break
        
        # Определяем категорию, если есть
        category = None
        for cat_name, keywords in categories.items():
            for keyword in keywords:
                if keyword.lower() in full_interaction:
                    category = cat_name
                    break
            if category:
                break
        
        # Определяем, является ли взаимодействие важным
        is_important = importance_score >= 0.4
        
        # Вопросы о персонаже часто важны
        if self.character_name.lower() in user_message.lower() and '?' in user_message:
            is_important = True
            importance_score = max(importance_score, 0.6)
            if not category:
                category = 'личное'
        
        # Если взаимодействие содержит прямое обращение к персонажу, оно важнее
        if re.search(rf'\b{self.character_name}\b', user_message, re.IGNORECASE):
            importance_score = min(0.9, importance_score + 0.1)
        
        return is_important, importance_score, category, emotion
    
    def _format_memory_for_prompt(self, relevant_memories):
        """
        Форматирование релевантных воспоминаний для промпта
        
        Args:
            relevant_memories (dict): Релевантные воспоминания из разных типов памяти
            
        Returns:
            str: Отформатированная информация о персонаже
        """
        character_info = ""
        
        # Группировка воспоминаний по типу с учетом релевантности
        memory_sections = {
            "facts": "ФАКТЫ О ТЕБЕ:",
            "traits": "ТВОИ ЧЕРТЫ ХАРАКТЕРА:",
            "speech_patterns": "ТВОИ ХАРАКТЕРНЫЕ ВЫРАЖЕНИЯ И МАНЕРА РЕЧИ:"
        }
        
        for memory_type, section_title in memory_sections.items():
            if memory_type in relevant_memories and relevant_memories[memory_type]:
                # Сортируем по релевантности
                memories = sorted(relevant_memories[memory_type], 
                                  key=lambda x: x['relevance'], reverse=True)
                
                character_info += f"\n{section_title}\n"
                
                # Добавляем информацию о релевантности, если уровень стиля высокий
                if self.style_level == 'high':
                    for mem in memories:
                        relevance_indicator = "★" * int(mem['relevance'] * 5)  # визуальный индикатор
                        character_info += f"- {mem['text']} {relevance_indicator}\n"
                else:
                    # Для низкого и среднего уровня просто перечисляем факты
                    character_info += "\n".join([f"- {mem['text']}" for mem in memories]) + "\n"
                
                character_info += "\n"
        
        # Добавляем эпизодические воспоминания, если они есть
        if "episodic" in relevant_memories and relevant_memories["episodic"]:
            # Сортируем по релевантности
            memories = sorted(relevant_memories["episodic"], 
                              key=lambda x: x['relevance'], reverse=True)
            
            character_info += "\nВАЖНЫЕ ВОСПОМИНАНИЯ:\n"
            
            # Форматируем эпизодические воспоминания с дополнительной информацией
            for mem in memories:
                relevance_indicator = "★" * int(mem['relevance'] * 5)  # визуальный индикатор
                
                # Добавляем базовую информацию
                memory_entry = f"- {mem['text']} {relevance_indicator}"
                
                # Добавляем метаданные для высокого уровня стилизации
                if self.style_level == 'high':
                    # Получаем возраст воспоминания в читаемом формате
                    age_days = mem.get('age_days', 0)
                    if age_days < 1:
                        age_str = "сегодня"
                    elif age_days < 2:
                        age_str = "вчера"
                    elif age_days < 7:
                        age_str = f"{int(age_days)} дней назад"
                    elif age_days < 30:
                        age_str = f"{int(age_days/7)} недель назад"
                    else:
                        age_str = f"{int(age_days/30)} месяцев назад"
                    
                    # Добавляем временную информацию
                    memory_entry += f" (произошло {age_str})"
                    
                    # Добавляем категорию, если есть
                    if mem.get('category'):
                        memory_entry += f", категория: {mem['category']}"
                    
                    # Добавляем эмоцию, если есть
                    if mem.get('emotion'):
                        memory_entry += f", эмоция: {mem['emotion']}"
                
                character_info += memory_entry + "\n"
            
            character_info += "\n"
        
        # Добавляем информацию об отношениях к пользователю
        character_info += self.relationship.get_relationship_summary_for_prompt() + "\n"
        
        return character_info.strip()
    
    def _build_prompt(self, user_message, relevant_memories):
        """
        Построение промпта для генеративной модели
        
        Args:
            user_message (str): Сообщение пользователя
            relevant_memories (dict): Релевантные воспоминания из разных типов памяти
            
        Returns:
            list: Список сообщений для отправки в LLM API
        """
        # Форматируем информацию о персонаже
        character_info = self._format_memory_for_prompt(relevant_memories)
        
        # Получаем историю разговора
        conversation_history = self.memory.get_conversation_context()
        
        # Объединяем встроенные примеры персонажа и пользовательские примеры
        all_style_examples = self.character.style_examples.copy()
        all_style_examples.extend(self.custom_style_examples)
        
        # Создаем системный промпт с помощью класса Character
        system_content = self.character.get_system_prompt(
            character_info,
            conversation_history,
            all_style_examples,
            self.style_level
        )
        
        # Дополнительные инструкции по отношениям
        relationship_status = self.relationship.get_status_description()
        
        # Добавляем инструкции об отношениях в зависимости от их уровня
        relationship_instructions = "\n\nТвои ответы должны отражать твое текущее отношение к собеседнику. "
        
        if relationship_status['rapport_value'] > 0.7:
            relationship_instructions += "Ты очень хорошо относишься к собеседнику, проявляй дружелюбие и готовность помочь."
        elif relationship_status['rapport_value'] > 0.3:
            relationship_instructions += "Ты положительно относишься к собеседнику, будь доброжелателен."
        elif relationship_status['rapport_value'] > -0.3:
            relationship_instructions += "Ты нейтрально относишься к собеседнику, будь вежлив, но сдержан."
        elif relationship_status['rapport_value'] > -0.7:
            relationship_instructions += "Ты плохо относишься к собеседнику, проявляй сдержанное раздражение и нетерпение."
        else:
            relationship_instructions += "Ты очень плохо относишься к собеседнику, будь холоден и демонстрируй явное неодобрение."
        
        # Добавляем инструкции по аспектам отношений
        if relationship_status['aspect_values'].get('trust', 0) < -0.5:
            relationship_instructions += " Ты не доверяешь собеседнику, будь осторожен и подозрителен."
        if relationship_status['aspect_values'].get('respect', 0) < -0.5:
            relationship_instructions += " Ты не уважаешь собеседника, можешь проявлять снисходительность."
        if relationship_status['aspect_values'].get('patience', 0) < -0.5:
            relationship_instructions += " Твое терпение на исходе, ты можешь обрывать собеседника и отвечать короче."
        
        system_content += relationship_instructions
        
        # Собираем сообщения для отправки
        messages = [{"role": "system", "content": system_content}]
        
        # Добавляем текущий запрос пользователя
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def process_message(self, user_message, top_k=3, relevance_method='sigmoid', min_relevance=0.2,
                        remember_interactions=True, update_relationship=True):
        """
        Обработка сообщения пользователя и генерация ответа персонажа
        
        Args:
            user_message (str): Сообщение пользователя
            top_k (int): Количество результатов для каждого типа памяти
            relevance_method (str): Метод расчета релевантности ('inverse', 'exponential', 'sigmoid')
            min_relevance (float): Минимальное значение релевантности для включения в результаты
            remember_interactions (bool): Сохранять ли важные взаимодействия в эпизодическую память
            update_relationship (bool): Обновлять ли отношения на основе взаимодействия
            
        Returns:
            str: Ответ персонажа
        """
        print(f"\nОбработка сообщения: \"{user_message}\"")
        
        # Получаем релевантные воспоминания с использованием улучшенных параметров
        relevant_memories = self.memory.retrieve_relevant_memories(
            user_message, 
            memory_types=["facts", "traits", "speech_patterns", "episodic"],
            top_k=top_k,
            relevance_method=relevance_method,
            min_relevance=min_relevance
        )
        
        print("Найдены релевантные воспоминания:")
        for memory_type, memories in relevant_memories.items():
            print(f"- {memory_type}:")
            for mem in memories:
                print(f"  * {mem['text']} (релевантность: {mem['relevance']:.2f})")
        
        # Строим промпт (сообщения для чата)
        messages = self._build_prompt(user_message, relevant_memories)
        
        print(f"Отправка запроса в {self.llm.provider_name} ({self.llm.model_name})...")
        
        # Добавляем сообщение в кратковременную память перед отправкой запроса
        self.memory.add_to_short_term_memory(f"Пользователь: {user_message}")
        
        # Генерация ответа с использованием выбранного LLM провайдера
        try:
            # Настройка температуры в зависимости от уровня стилизации
            temperature_map = {'low': 0.5, 'medium': 0.7, 'high': 0.85}
            temperature = temperature_map.get(self.style_level, 0.7)
            
            # Стоп-последовательности, чтобы избежать шаблонных фраз
            stop_sequences = ["Я AI", "Я искусственный интеллект", "Как ИИ", "Как языковая модель"]
            
            # Генерация ответа
            answer = self.llm.generate(
                messages=messages,
                temperature=temperature,
                max_tokens=500,
                stop=stop_sequences
            )
            
            # Пост-обработка ответа для удаления нежелательных фраз
            unwanted_phrases = [
                "Я не могу", "Я должен отметить", "Я не имею", "Я бы хотел отметить",
                f"Как {self.character_name}", f"Будучи {self.character_name}", f"В роли {self.character_name}"
            ]
            
            for phrase in unwanted_phrases:
                if answer.startswith(phrase):
                    answer = answer[len(phrase):].lstrip(",.! ")
            
            # Добавляем ответ в кратковременную память
            self.memory.add_to_short_term_memory(f"{self.character_name}: {answer}")
            
            # Если включено обновление отношений, обновляем их
            if update_relationship:
                relationship_changes = self.relationship.update_from_interaction(user_message, answer)
                self._save_relationship()  # Сохраняем обновленные отношения
                
                # Выводим информацию об изменении отношений
                if abs(relationship_changes['rapport_change']) > 0.01:
                    direction = "улучшилось" if relationship_changes['rapport_change'] > 0 else "ухудшилось"
                    print(f"Отношение {direction} на {abs(relationship_changes['rapport_change']):.2f}: {relationship_changes['reason']}")
            
            # Если включено запоминание взаимодействий, проверяем, является ли это важным событием
            if remember_interactions:
                is_important, importance, category, emotion = self._detect_important_event(user_message, answer)
                
                if is_important:
                    # Форматируем взаимодействие для сохранения
                    interaction = f"[Взаимодействие]: Пользователь: '{user_message}'. {self.character_name}: '{answer}'"
                    
                    # Добавляем в эпизодическую память
                    memory_idx = self.memory.add_episodic_memory(
                        interaction, 
                        importance=importance, 
                        category=category, 
                        emotion=emotion
                    )
                    
                    print(f"Сохранено важное взаимодействие в эпизодическую память (важность: {importance:.2f})")
            
            print(f"Получен ответ от {self.llm.provider_name} ({len(answer)} символов)")
            return answer
            
        except Exception as e:
            error_message = f"Ошибка при обращении к LLM API: {str(e)}"
            print(error_message)
            return error_message

    def add_episodic_memory(self, text, importance=0.5, category=None, emotion=None):
        """
        Добавляет новое эпизодическое воспоминание
        
        Args:
            text (str): Текст воспоминания
            importance (float): Важность (0.0-1.0)
            category (str, optional): Категория воспоминания
            emotion (str, optional): Эмоция, связанная с воспоминанием
            
        Returns:
            int: Индекс добавленного воспоминания
        """
        return self.memory.add_episodic_memory(text, importance, category, emotion)
    
    def update_episodic_memory_importance(self, memory_index, new_importance):
        """
        Обновляет важность эпизодического воспоминания
        
        Args:
            memory_index (int): Индекс воспоминания
            new_importance (float): Новая важность (0.0-1.0)
            
        Returns:
            bool: True если обновление успешно, False в противном случае
        """
        return self.memory.update_episodic_memory_importance(memory_index, new_importance)
    
    def get_episodic_memories(self, sort_by="importance"):
        if not hasattr(self.memory, 'episodic_memory'):
            return []
        return self.memory.episodic_memory.sort(sort_by=sort_by)
    
    def get_relationship_status(self):
        """
        Возвращает текущий статус отношений
        
        Returns:
            dict: Статус отношений
        """
        return self.relationship.get_status_description()
    
    def update_relationship_manually(self, aspect, change):
        """
        Позволяет вручную изменить аспект отношений
        
        Args:
            aspect (str): Аспект отношений ('rapport', 'respect', 'trust', 'liking', 'patience')
            change (float): Величина изменения (-1.0 - 1.0)
            
        Returns:
            bool: True если обновление успешно, False в противном случае
        """
        try:
            if aspect == 'rapport':
                old_value = self.relationship.rapport
                self.relationship.rapport = max(-1.0, min(1.0, old_value + change))
                
                # Добавляем в историю
                self.relationship._add_to_history(
                    "Ручное изменение общего отношения", 
                    self.relationship.rapport, 
                    self.relationship.aspects,
                    abs(change)
                )
            elif aspect in self.relationship.aspects:
                old_value = self.relationship.aspects[aspect]
                self.relationship.aspects[aspect] = max(-1.0, min(1.0, old_value + change))
                
                # Добавляем в историю
                self.relationship._add_to_history(
                    f"Ручное изменение аспекта {aspect}", 
                    self.relationship.rapport, 
                    self.relationship.aspects,
                    abs(change)
                )
            else:
                return False
            
            # Сохраняем обновленные отношения
            self._save_relationship()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении отношений: {str(e)}")
            return False
    
    def clear_episodic_memories(self):
        """
        Очищает все эпизодические воспоминания
        
        Returns:
            int: Количество удалённых воспоминаний
        """
        return self.memory.clear_episodic_memories()  # Вызываем метод MemoryManager
            
    def save_state(self):
        """
        Сохранение текущего состояния агента
        """
        print(f"Сохранение состояния агента {self.character_name}...")
        
        # Сохраняем память
        self.memory.save_to_file(self.memory_file)
        
        # Сохраняем пользовательские примеры стиля
        if self.custom_style_examples:
            self._save_style_examples()
        
        # Сохраняем отношения
        self._save_relationship()
        
        print(f"Состояние агента {self.character_name} успешно сохранено")

    def setup_llm(self, provider_name=None, model_name=None, api_key=None):
        """
        Инициализирует или переинициализирует LLM провайдера с новыми параметрами
        
        Args:
            provider_name (str, optional): Имя провайдера. Если None, используется текущий.
            model_name (str, optional): Название модели. Если None, используется текущая или по умолчанию.
            api_key (str, optional): API ключ. Если None, используется из переменных окружения.
            
        Returns:
            bool: True если инициализация успешна, иначе False
        """
        from llm_provider import get_provider
        
        try:
            # Используем текущие значения, если новые не предоставлены
            provider = provider_name or self.llm_provider_name
            model = model_name or self.llm_model_name
            
            # Обновляем атрибуты
            self.llm_provider_name = provider
            self.llm_model_name = model
            
            # Переинициализируем LLM провайдера
            self.llm = get_provider(
                provider_name=provider,
                model_name=model,
                api_key=api_key
            )
            
            print(f"LLM провайдер переинициализирован: {self.llm.provider_name}, модель: {self.llm.model_name}")
            return True
        
        except Exception as e:
            import logging
            logging.error(f"Ошибка при инициализации LLM: {str(e)}")
            print(f"Ошибка при инициализации LLM: {str(e)}")
            return False

    @classmethod
    def load_or_create(cls, character_name, user_id="default", model_name='paraphrase-multilingual-MiniLM-L12-v2', 
                       index_type='flat', use_cosine=True, style_level='high',
                       llm_provider='openai', llm_model=None, llm_api_key=None):
        """
        Загрузка существующего агента или создание нового
        
        Args:
            character_name (str): Имя персонажа
            user_id (str): Идентификатор пользователя
            model_name (str): Название модели sentence-transformers
            index_type (str): Тип индекса FAISS ('flat', 'ivf', 'ivfpq', 'hnsw')
            use_cosine (bool): Использовать ли косинусное сходство
            style_level (str): Уровень стилизации ('low', 'medium', 'high')
            llm_provider (str): Провайдер LLM ('openai', 'anthropic', 'deepseek')
            llm_model (str): Название модели LLM (если None, используется модель по умолчанию)
            llm_api_key (str): API ключ для LLM
            
        Returns:
            CharacterAgent: Загруженный или новый агент
        """
        # Формируем безопасное имя файла из имени персонажа и ID пользователя
        safe_character = "".join(c if c.isalnum() else "_" for c in character_name)
        safe_user = "".join(c if c.isalnum() else "_" for c in user_id)
        state_dir = os.path.join("character_states", safe_character, safe_user)
        memory_file = os.path.join(state_dir, "memory.pkl")
        
        if os.path.exists(memory_file):
            print(f"Найдено состояние агента {character_name} для пользователя {user_id}")
            return cls(character_name, user_id, load_state=True, model_name=model_name, 
                       index_type=index_type, use_cosine=use_cosine, style_level=style_level,
                       llm_provider=llm_provider, llm_model=llm_model, llm_api_key=llm_api_key)
        else:
            print(f"Создание нового агента {character_name} для пользователя {user_id}")
            return cls(character_name, user_id, load_state=False, model_name=model_name, 
                       index_type=index_type, use_cosine=use_cosine, style_level=style_level,
                       llm_provider=llm_provider, llm_model=llm_model, llm_api_key=llm_api_key)