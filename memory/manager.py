# memory/manager.py

from typing import Dict, List, Any, Optional
import os
import pickle
from datetime import datetime
import logging

from .base import BaseMemory
from .episodic import EpisodicMemory
from .long_term import LongTermMemory
from .short_term import ShortTermMemory
from .vector_index import VectorIndex

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Управляет всеми типами памяти персонажа и предоставляет единый интерфейс
    """
    
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2', 
                 index_type='flat', use_cosine=True):
        """
        Инициализация системы памяти персонажа
        
        Args:
            model_name (str): Название модели sentence-transformers для создания эмбеддингов
            index_type (str): Тип индекса FAISS ('flat', 'ivf', 'ivfpq', 'hnsw')
            use_cosine (bool): Использовать ли косинусное сходство вместо евклидова расстояния
        """
        # Сохраняем параметры
        self.model_name = model_name
        self.index_type = index_type
        self.use_cosine = use_cosine
        
        # Инициализируем компоненты памяти
        self.vector_index = VectorIndex(model_name, index_type, use_cosine)
        self.long_term_memory = LongTermMemory(self.vector_index)
        self.short_term_memory = ShortTermMemory()
        self.episodic_memory = EpisodicMemory(self.vector_index)
        
        # Для совместимости со старым кодом
        self.memory_texts = {}
        
    # Для совместимости со старым кодом
    @property
    def episodic_memories(self):
        return self.episodic_memory.episodic_memories
    
    def initialize_long_term_memory(self, character_data):
        """Инициализация долгосрочной памяти персонажа"""
        self.memory_texts = self.long_term_memory.initialize(character_data)
    
    def add_to_short_term_memory(self, message):
        """Добавление сообщения в краткосрочную память"""
        self.short_term_memory.add_message(message)
        return self.short_term_memory.get_messages()
    
    def get_conversation_context(self):
        """Получение текущего контекста разговора"""
        return self.short_term_memory.get_context()
    
    def add_episodic_memory(self, text, importance=0.5, category=None, emotion=None):
        """Добавление нового эпизодического воспоминания"""
        memory_idx = self.episodic_memory.add_memory(text, importance, category, emotion)
        # Обновляем списки для совместимости
        self.memory_texts["episodic"] = self.episodic_memory.get_all_texts()
        return memory_idx
    
    def update_episodic_memory_importance(self, memory_index, new_importance):
        """Обновление важности эпизодического воспоминания"""
        return self.episodic_memory.update_importance(memory_index, new_importance)
    
    def decay_episodic_memories(self):
        """Применение затухания важности к эпизодическим воспоминаниям"""
        self.episodic_memory.decay_memories()
    
    def get_memory_texts(self, memory_type):
        """Получение текстов для указанного типа памяти"""
        if memory_type in ["facts", "traits", "speech_patterns"]:
            return self.long_term_memory.get_memory_texts(memory_type)
        elif memory_type == "episodic":
            return self.episodic_memory.get_all_texts()
        return []
    
    def retrieve_relevant_memories(self, query, memory_types=None, top_k=3, 
                                  relevance_method='sigmoid', min_relevance=0.2):
        """Поиск релевантных воспоминаний"""
        if memory_types is None:
            memory_types = ["facts", "traits", "speech_patterns", "episodic"]
        
        relevant_memories = {}
        
        # Поиск в долговременной памяти
        lt_types = [t for t in memory_types if t in ["facts", "traits", "speech_patterns"]]
        if lt_types:
            lt_memories = self.long_term_memory.retrieve_relevant(
                query, lt_types, top_k, relevance_method, min_relevance
            )
            relevant_memories.update(lt_memories)
        
        # Поиск в эпизодической памяти
        if "episodic" in memory_types:
            episodic_memories = self.episodic_memory.retrieve_relevant(
                query, top_k, relevance_method, min_relevance
            )
            if episodic_memories:
                relevant_memories["episodic"] = episodic_memories
        
        return relevant_memories
    
    def get_episodic_memories(self, sort_by="importance"):
        """Получение всех эпизодических воспоминаний"""
        return self.episodic_memory.get_all(sort_by)
    
    def clear_episodic_memories(self):
        """
        Очищает все эпизодические воспоминания
        
        Returns:
            int: Количество удалённых воспоминаний
        """
        return self.episodic_memory.clear()  # Вызываем метод EpisodicMemory
    
    def save_to_file(self, file_path):
        """Сохранение состояния памяти в файл"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        memory_data = {
            'long_term_memory': self.long_term_memory.to_dict(),
            'short_term_memory': self.short_term_memory.to_dict(),
            'episodic_memory': self.episodic_memory.to_dict(),
            'memory_texts': self.memory_texts,
            'model_name': self.model_name,
            'index_type': self.index_type,
            'use_cosine': self.use_cosine
        }
        
        with open(file_path, 'wb') as f:
            pickle.dump(memory_data, f)
        
        logger.info(f"Память успешно сохранена в {file_path}")
    
    @classmethod
    def load_from_file(cls, file_path):
        """Загрузка состояния памяти из файла"""
        if not os.path.exists(file_path):
            logger.warning(f"Файл {file_path} не найден. Создаем новую память.")
            return cls()
        
        try:
            with open(file_path, 'rb') as f:
                memory_data = pickle.load(f)
            
            # Создаем новый экземпляр
            manager = cls(
                model_name=memory_data.get('model_name', 'paraphrase-multilingual-MiniLM-L12-v2'),
                index_type=memory_data.get('index_type', 'flat'),
                use_cosine=memory_data.get('use_cosine', True)
            )
            
            # Восстанавливаем компоненты
            manager.long_term_memory.from_dict(memory_data.get('long_term_memory', {}))
            manager.short_term_memory.from_dict(memory_data.get('short_term_memory', {}))
            manager.episodic_memory.from_dict(memory_data.get('episodic_memory', {}))
            manager.memory_texts = memory_data.get('memory_texts', {
                "facts": [], "traits": [], "speech_patterns": [], "episodic": []
            })
            
            logger.info(f"Память успешно загружена из {file_path}")
            return manager
        except Exception as e:
            logger.error(f"Ошибка при загрузке памяти: {str(e)}")
            return cls()