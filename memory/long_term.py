# memory/long_term.py

from typing import List, Dict, Any, Optional
from .base import BaseMemory

class LongTermMemory(BaseMemory):
    """
    Класс для долговременной памяти (факты, черты характера, паттерны речи)
    """
    
    def __init__(self, vector_index):
        """
        Инициализация долговременной памяти
        
        Args:
            vector_index: Индекс для векторного поиска
        """
        self.vector_index = vector_index
        self.memory = {
            "facts": [],       # Факты о персонаже
            "traits": [],      # Черты характера
            "speech_patterns": []  # Особенности речи
        }
    
    def initialize(self, character_data: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Инициализация долговременной памяти данными о персонаже
        
        Args:
            character_data (Dict[str, List[str]]): Данные о персонаже
            
        Returns:
            Dict[str, List[str]]: Словарь с текстами для каждого типа памяти
        """
        # Заполняем долговременную память
        self.memory["facts"] = character_data.get("facts", [])
        self.memory["traits"] = character_data.get("traits", [])
        self.memory["speech_patterns"] = character_data.get("speech_patterns", [])
        
        # Создаем индексы для каждого типа памяти
        for memory_type in ["facts", "traits", "speech_patterns"]:
            if self.memory[memory_type]:
                self.vector_index.create_index(memory_type, self.memory[memory_type])
        
        # Возвращаем тексты для совместимости
        return {
            "facts": self.memory["facts"],
            "traits": self.memory["traits"],
            "speech_patterns": self.memory["speech_patterns"],
            "episodic": []  # Пустой список для эпизодической памяти
        }
    
    def add_fact(self, fact: str) -> None:
        """
        Добавление нового факта
        
        Args:
            fact (str): Текст факта
        """
        self.memory["facts"].append(fact)
        self.vector_index.update_index("facts", [fact])
    
    def add_trait(self, trait: str) -> None:
        """
        Добавление новой черты характера
        
        Args:
            trait (str): Текст черты характера
        """
        self.memory["traits"].append(trait)
        self.vector_index.update_index("traits", [trait])
    
    def add_speech_pattern(self, pattern: str) -> None:
        """
        Добавление нового паттерна речи
        
        Args:
            pattern (str): Текст паттерна речи
        """
        self.memory["speech_patterns"].append(pattern)
        self.vector_index.update_index("speech_patterns", [pattern])
    
    def get_memory_texts(self, memory_type: str) -> List[str]:
        """
        Получение текстов для указанного типа памяти
        
        Args:
            memory_type (str): Тип памяти ('facts', 'traits', 'speech_patterns')
            
        Returns:
            List[str]: Список текстов
        """
        return self.memory.get(memory_type, [])
    
    def retrieve_relevant(self, query: str, memory_types: List[str], top_k: int = 3,
                         relevance_method: str = 'sigmoid', min_relevance: float = 0.2) -> Dict[str, List[Dict[str, Any]]]:
        """
        Поиск релевантных воспоминаний для указанных типов памяти
        
        Args:
            query (str): Текст запроса
            memory_types (List[str]): Типы памяти для поиска
            top_k (int): Количество результатов для каждого типа
            relevance_method (str): Метод расчета релевантности
            min_relevance (float): Минимальное значение релевантности
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Словарь с релевантными воспоминаниями
        """
        relevant_memories = {}
        
        for memory_type in memory_types:
            if memory_type in self.memory and self.memory[memory_type]:
                # Поиск в индексе
                results = self.vector_index.search(
                    memory_type, query, top_k, relevance_method, min_relevance
                )
                
                # Если есть результаты, добавляем их
                if results:
                    relevant_memories[memory_type] = [
                        {"text": r["text"], "relevance": r["relevance"]} 
                        for r in results
                    ]
        
        return relevant_memories
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование памяти в словарь для сериализации
        
        Returns:
            Dict: Словарь с данными
        """
        return self.memory
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Загрузка данных памяти из словаря
        
        Args:
            data (Dict): Словарь с данными
        """
        for memory_type in ["facts", "traits", "speech_patterns"]:
            self.memory[memory_type] = data.get(memory_type, [])
            
            # Пересоздаем индексы
            if self.memory[memory_type]:
                self.vector_index.rebuild_index(memory_type, self.memory[memory_type])