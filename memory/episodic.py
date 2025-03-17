# memory/episodic.py

import time
from datetime import datetime
from typing import List, Dict, Any, Optional

class EpisodicMemory:
    """
    Класс для управления эпизодической памятью персонажа
    """
    
    def __init__(self, vector_index):
        """
        Инициализация эпизодической памяти
        
        Args:
            vector_index: Индекс для векторного поиска
        """
        self.vector_index = vector_index
        self.memories = []
        self.settings = {
            'importance_decay_rate': 0.95,  # Скорость затухания важности со временем
            'max_memories': 100,          # Максимальное количество эпизодических воспоминаний
            'recency_weight': 0.3,        # Вес фактора новизны при расчете релевантности
            'importance_weight': 0.7      # Вес фактора важности при расчете релевантности
        }
    
    def sort(self, sort_by="importance"):
        """
        Возвращает отсортированный список воспоминаний по заданному критерию.

        Args:
            sort_by (str): Критерий сортировки ("importance", "recency", "access_count")

        Returns:
            list: Отсортированный список воспоминаний
        """
        # Создаем копию списка воспоминаний, чтобы не изменять оригинал
        memories = self.memories.copy()

        # Сортируем по заданному критерию
        if sort_by == "importance":
            memories.sort(key=lambda x: x["importance"], reverse=True)
        elif sort_by == "recency":
            memories.sort(key=lambda x: x["unix_time"], reverse=True)
        elif sort_by == "access_count":
            memories.sort(key=lambda x: x["access_count"], reverse=True)
        else:
            raise ValueError(f"Неверный критерий сортировки: {sort_by}")

        return memories

    def copy(self):
        """
        Создает глубокую копию объекта эпизодической памяти
        
        Returns:
            EpisodicMemory: Новый объект эпизодической памяти с копией данных
        """
        import copy
        
        # Создаем новый экземпляр EpisodicMemory
        new_episodic_memory = EpisodicMemory(self.vector_index)
        
        # Выполняем глубокое копирование memories и settings
        new_episodic_memory.memories = copy.deepcopy(self.memories)
        new_episodic_memory.settings = copy.deepcopy(self.settings)
        
        return new_episodic_memory

    def add_memory(self, text, importance=0.5, category=None, emotion=None):
        """
        Добавление нового эпизодического воспоминания
        
        Args:
            text (str): Текст воспоминания
            importance (float): Важность воспоминания (0.0-1.0)
            category (str, optional): Категория воспоминания
            emotion (str, optional): Эмоциональный окрас воспоминания
            
        Returns:
            int: Индекс добавленного воспоминания
        """
        memory_entry = {
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "unix_time": time.time(),
            "importance": float(importance),
            "category": category,
            "emotion": emotion,
            "access_count": 0
        }
        
        self.memories.append(memory_entry)
        
        # Обновляем индекс
        self.vector_index.update_index("episodic", [text])
        
        # Удаляем маловажные воспоминания, если превышен лимит
        self._prune_memories()
        
        return len(self.memories) - 1
    
    def update_importance(self, memory_index, new_importance):
        """
        Обновление важности воспоминания
        
        Args:
            memory_index (int): Индекс воспоминания
            new_importance (float): Новая важность (0.0-1.0)
            
        Returns:
            bool: True если обновление успешно, False в противном случае
        """
        if 0 <= memory_index < len(self.memories):
            self.memories[memory_index]["importance"] = float(new_importance)
            return True
        return False
    
    def decay_memories(self):
        """
        Применение затухания важности к воспоминаниям с течением времени
        """
        decay_rate = self.settings['importance_decay_rate']
        current_time = time.time()
        
        for memory in self.memories:
            age_in_days = (current_time - memory["unix_time"]) / 86400.0
            decay_factor = decay_rate ** (age_in_days / 30)
            memory["importance"] = max(0.1, memory["importance"] * decay_factor)
    
    def _prune_memories(self):
        """
        Удаление наименее важных воспоминаний, если их количество превышает лимит
        """
        if len(self.memories) <= self.settings['max_memories']:
            return
        
        # Вычисляем комбинированную оценку для каждого воспоминания
        current_time = time.time()
        memories_with_scores = []
        
        for idx, memory in enumerate(self.memories):
            age = (current_time - memory["unix_time"]) / 86400.0  # Возраст в днях
            importance = memory["importance"]
            access_frequency = memory["access_count"] / (1 + age)
            
            score = 0.7 * importance + 0.2 * (1.0 / (1.0 + age/30)) + 0.1 * min(1.0, access_frequency)
            memories_with_scores.append((idx, score))
        
        # Сортируем и удаляем наименее важные
        memories_with_scores.sort(key=lambda x: x[1])
        to_remove = memories_with_scores[:len(self.memories) - self.settings['max_memories']]
        indices_to_remove = [idx for idx, _ in to_remove]
        
        new_memories = [m for i, m in enumerate(self.memories) if i not in indices_to_remove]
        self.memories = new_memories
        
        # Обновляем индекс
        self.vector_index.rebuild_index("episodic", [m["text"] for m in self.memories])
    
    def retrieve_relevant(self, query, top_k=3, relevance_method='sigmoid', min_relevance=0.2):
        """
        Поиск релевантных эпизодических воспоминаний
        
        Args:
            query (str): Запрос
            top_k (int): Количество результатов
            relevance_method (str): Метод расчета релевантности
            min_relevance (float): Минимальное значение релевантности
            
        Returns:
            list: Список релевантных воспоминаний
        """
        if not self.memories:
            return []
        
        # Получаем релевантные индексы из векторного индекса
        results = self.vector_index.search("episodic", query, top_k * 2, relevance_method)
        
        # Фильтруем и обогащаем результаты метаданными
        relevant_memories = []
        current_time = time.time()
        
        for result in results:
            idx = result["index"]
            if idx < len(self.memories):
                memory = self.memories[idx]
                
                # Базовая релевантность из векторного поиска
                relevance = result["relevance"]
                
                # Учитываем важность воспоминания
                importance = memory["importance"]
                
                # Учитываем новизну воспоминания
                age_in_days = (current_time - memory["unix_time"]) / 86400.0
                recency = 1.0 / (1.0 + age_in_days/30)
                
                # Комбинируем факторы
                semantic_weight = 0.6
                importance_weight = self.settings['importance_weight']
                recency_weight = self.settings['recency_weight']
                
                # Нормализуем веса
                sum_weights = semantic_weight + importance_weight + recency_weight
                semantic_weight /= sum_weights
                importance_weight /= sum_weights
                recency_weight /= sum_weights
                
                # Обновляем релевантность
                combined_relevance = (semantic_weight * relevance + 
                                    importance_weight * importance + 
                                    recency_weight * recency)
                
                # Увеличиваем счетчик обращений
                self.memories[idx]["access_count"] += 1
                
                # Если релевантность достаточная, добавляем в результаты
                if combined_relevance >= min_relevance:
                    memory_result = {
                        "text": memory["text"],
                        "relevance": combined_relevance,
                        "timestamp": memory["timestamp"],
                        "importance": importance,
                        "category": memory["category"],
                        "emotion": memory["emotion"],
                        "age_days": age_in_days
                    }
                    relevant_memories.append(memory_result)
        
        # Сортируем по релевантности и ограничиваем количество
        relevant_memories.sort(key=lambda x: x["relevance"], reverse=True)
        return relevant_memories[:top_k]
    
    def get_all_texts(self):
        """
        Получение всех текстов воспоминаний
        
        Returns:
            list: Список текстов воспоминаний
        """
        return [memory["text"] for memory in self.memories]
    
    def to_dict(self):
        """
        Сериализация эпизодической памяти
        
        Returns:
            dict: Словарь с данными
        """
        return {
            "memories": self.memories,
            "settings": self.settings
        }
    
    def from_dict(self, data):
        """
        Десериализация эпизодической памяти
        
        Args:
            data (dict): Словарь с данными
        """
        self.memories = data.get("memories", [])
        self.settings = data.get("settings", self.settings)
        
        # Обновляем индекс после загрузки
        if self.memories:
            self.vector_index.rebuild_index("episodic", [m["text"] for m in self.memories])
    
    def get_all(self, sort_by="importance"):
        """
        Возвращает все воспоминания, отсортированные по заданному критерию.
        
        Args:
            sort_by (str): Критерий сортировки ("importance", "recency", "access_count")
            
        Returns:
            list: Список всех воспоминаний
        """
        return self.sort(sort_by=sort_by)

    def clear(self):
        """
        Очищает все эпизодические воспоминания
        
        Returns:
            int: Количество удалённых воспоминаний
        """
        count = len(self.memories)  # Подсчитываем количество воспоминаний
        self.memories = []          # Очищаем список воспоминаний
        self.vector_index.rebuild_index("episodic", [])  # Перестраиваем индекс
        return count               # Возвращаем количество удалённых записей
    
