# session_manager.py

"""
Менеджер сессий для работы с несколькими пользователями в Telegram боте.
Хранит и управляет экземплярами CharacterAgent для каждого пользователя.
"""

import os
import json
import time
from agent import CharacterAgent
from characters import list_characters, get_character

class SessionManager:
    """
    Управляет сессиями пользователей для Telegram бота
    """
    
    def __init__(self, config_path="config/bot_config.json"):
        """
        Инициализация менеджера сессий
        
        Args:
            config_path (str): Путь к файлу конфигурации
        """
        self.config_path = config_path
        self.active_sessions = {}  # user_id -> {character_name, agent, last_active}
        self.default_character = "Шерлок Холмс"
        self.config = self._load_config()
        
        # Создаем директорию для сессий, если она не существует
        os.makedirs("character_states", exist_ok=True)
        
        # Загружаем активные сессии, если они есть
        self._load_active_sessions()
        
        print(f"Инициализирован менеджер сессий. Загружено {len(self.active_sessions)} активных сессий.")
    
    def _load_config(self):
        """
        Загружает конфигурацию бота
        
        Returns:
            dict: Конфигурация
        """
        config = {
            "default_character": "Шерлок Холмс",
            "default_llm_provider": "openai",
            "default_llm_model": "gpt-4o-mini",
            "default_style_level": "high",
            "default_index_type": "flat",
            "session_timeout": 86400,  # 24 часа
            "auto_save_interval": 600,  # 10 минут
            "max_inactive_sessions": 100
        }
        
        try:
            # Проверяем, существует ли директория конфигурации
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Проверяем, существует ли файл конфигурации
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    config.update(loaded_config)
            else:
                # Если файл не существует, создаем его с настройками по умолчанию
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка при загрузке конфигурации: {str(e)}")
        
        self.default_character = config["default_character"]
        return config
    
    def _save_config(self):
        """
        Сохраняет конфигурацию бота
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка при сохранении конфигурации: {str(e)}")
    
    def _load_active_sessions(self):
        """
        Загружает информацию об активных сессиях из файла
        """
        sessions_file = "config/active_sessions.json"
        try:
            if os.path.exists(sessions_file):
                with open(sessions_file, 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)
                
                # Загружаем информацию о сессиях, но не создаем агентов
                for user_id, session_info in sessions_data.items():
                    character_name = session_info.get("character_name", self.default_character)
                    last_active = session_info.get("last_active", 0)
                    
                    # Проверяем, не устарела ли сессия
                    if time.time() - last_active < self.config["session_timeout"]:
                        self.active_sessions[user_id] = {
                            "character_name": character_name,
                            "agent": None,  # Агент будет создан при первом обращении
                            "last_active": last_active
                        }
        except Exception as e:
            print(f"Ошибка при загрузке активных сессий: {str(e)}")
    
    def _save_active_sessions(self):
        """
        Сохраняет информацию об активных сессиях в файл
        """
        sessions_file = "config/active_sessions.json"
        try:
            # Создаем директорию, если она не существует
            os.makedirs(os.path.dirname(sessions_file), exist_ok=True)
            
            # Подготавливаем данные для сохранения
            sessions_data = {}
            for user_id, session in self.active_sessions.items():
                sessions_data[user_id] = {
                    "character_name": session["character_name"],
                    "last_active": session["last_active"]
                }
            
            # Сохраняем данные в файл
            with open(sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка при сохранении активных сессий: {str(e)}")
    
    def get_agent_for_user(self, user_id, character_name=None):
        """
        Получает или создает агента для пользователя
        
        Args:
            user_id (str): Идентификатор пользователя
            character_name (str, optional): Имя персонажа (если None, используется текущий или по умолчанию)
            
        Returns:
            CharacterAgent: Агент
        """
        # Если имя персонажа не указано, используем текущего или по умолчанию
        if character_name is None:
            if user_id in self.active_sessions:
                character_name = self.active_sessions[user_id]["character_name"]
            else:
                character_name = self.default_character
        
        # Проверяем, существует ли персонаж
        if not get_character(character_name):
            print(f"Персонаж '{character_name}' не найден. Используем '{self.default_character}'")
            character_name = self.default_character
        
        # Проверяем, есть ли сессия для этого пользователя
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            
            # Если нужно сменить персонажа
            if character_name != session["character_name"]:
                # Сохраняем текущего агента, если он есть
                if session["agent"] is not None:
                    session["agent"].save_state()
                
                # Создаем нового агента
                session["agent"] = self._create_agent(character_name, user_id)
                session["character_name"] = character_name
            
            # Если агент еще не создан, создаем его
            elif session["agent"] is None:
                session["agent"] = self._create_agent(character_name, user_id)
            
            # Обновляем время последней активности
            session["last_active"] = time.time()
        else:
            # Создаем новую сессию
            agent = self._create_agent(character_name, user_id)
            self.active_sessions[user_id] = {
                "character_name": character_name,
                "agent": agent,
                "last_active": time.time()
            }
        
        # Периодически чистим неактивные сессии и сохраняем состояние
        self._cleanup_sessions()
        
        return self.active_sessions[user_id]["agent"]
    
    def _create_agent(self, character_name, user_id):
        """
        Создает нового агента
        
        Args:
            character_name (str): Имя персонажа
            user_id (str): Идентификатор пользователя
            
        Returns:
            CharacterAgent: Созданный агент
        """
        try:
            return CharacterAgent.load_or_create(
                character_name=character_name,
                user_id=user_id,
                model_name=self.config.get("default_embedding_model", "paraphrase-multilingual-MiniLM-L12-v2"),
                index_type=self.config.get("default_index_type", "flat"),
                use_cosine=True,
                style_level=self.config.get("default_style_level", "high"),
                llm_provider=self.config.get("default_llm_provider", "openai"),
                llm_model=self.config.get("default_llm_model", "gpt-4o-mini")
            )
        except Exception as e:
            print(f"Ошибка при создании агента: {str(e)}")
            # Пытаемся создать агента с дефолтными параметрами в случае ошибки
            return CharacterAgent.load_or_create(
                character_name=self.default_character,
                user_id=user_id
            )
    
    def process_message(self, user_id, message_text, character_name=None):
        """
        Обрабатывает сообщение пользователя
        
        Args:
            user_id (str): Идентификатор пользователя
            message_text (str): Текст сообщения
            character_name (str, optional): Имя персонажа (если None, используется текущий)
            
        Returns:
            str: Ответ персонажа
        """
        # Получаем агента для пользователя
        agent = self.get_agent_for_user(user_id, character_name)
        
        # Обрабатываем сообщение
        response = agent.process_message(message_text)
        
        # Обновляем время последней активности
        self.active_sessions[user_id]["last_active"] = time.time()
        
        return response
    
    def change_character(self, user_id, character_name):
        """
        Меняет персонажа для пользователя
        
        Args:
            user_id (str): Идентификатор пользователя
            character_name (str): Имя нового персонажа
            
        Returns:
            bool: True если успешно, False если персонаж не найден
        """
        # Проверяем, существует ли персонаж
        if not get_character(character_name):
            return False
        
        # Получаем агента для нового персонажа (это автоматически сменит персонажа)
        self.get_agent_for_user(user_id, character_name)
        self._save_active_sessions()
        
        return True
    
    def save_all_sessions(self):
        """
        Сохраняет состояние всех активных сессий
        """
        for user_id, session in self.active_sessions.items():
            if session["agent"] is not None:
                session["agent"].save_state()
        
        self._save_active_sessions()
        print(f"Сохранены все активные сессии ({len(self.active_sessions)})")
    
    def _cleanup_sessions(self):
        """
        Очищает неактивные сессии и сохраняет остальные
        """
        current_time = time.time()
        sessions_to_remove = []
        
        # Находим устаревшие сессии
        for user_id, session in self.active_sessions.items():
            if current_time - session["last_active"] > self.config["session_timeout"]:
                sessions_to_remove.append(user_id)
        
        # Удаляем устаревшие сессии
        for user_id in sessions_to_remove:
            if self.active_sessions[user_id]["agent"] is not None:
                self.active_sessions[user_id]["agent"].save_state()
            del self.active_sessions[user_id]
        
        # Ограничиваем общее количество сессий
        if len(self.active_sessions) > self.config["max_inactive_sessions"]:
            # Сортируем сессии по времени последней активности
            sorted_sessions = sorted(
                self.active_sessions.items(), 
                key=lambda x: x[1]["last_active"]
            )
            
            # Удаляем наименее активные сессии
            excess_count = len(self.active_sessions) - self.config["max_inactive_sessions"]
            for i in range(excess_count):
                user_id, session = sorted_sessions[i]
                if session["agent"] is not None:
                    session["agent"].save_state()
                del self.active_sessions[user_id]
        
        # Сохраняем активные сессии
        if sessions_to_remove or len(self.active_sessions) > self.config["max_inactive_sessions"]:
            self._save_active_sessions()
    
    def get_available_characters(self):
        """
        Возвращает список доступных персонажей
        
        Returns:
            list: Список кортежей (имя, описание)
        """
        return list_characters()