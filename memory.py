# memory.py

import os
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from datetime import datetime
import time

class Memory:
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2', index_type='flat', use_cosine=True):
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
        
        # Загрузка модели для создания эмбеддингов
        print(f"Загрузка модели {model_name}...")
        self.model = SentenceTransformer(model_name)
        print("Модель загружена!")
        
        # Структуры для различных типов долгосрочной памяти
        self.long_term_memory = {
            "facts": [],       # Факты о персонаже
            "traits": [],      # Черты характера
            "speech_patterns": []  # Особенности речи
        }
        
        # Краткосрочная память (последние сообщения в разговоре)
        self.short_term_memory = []
        
        # Эпизодическая память (важные события и взаимодействия)
        self.episodic_memory = []
        
        # Индексы FAISS для каждого типа долгосрочной памяти
        self.indexes = {}
        
        # Хранение текстов, соответствующих эмбеддингам в индексах
        self.memory_texts = {
            "facts": [],
            "traits": [],
            "speech_patterns": [],
            "episodic": []  # Добавляем эпизодическую память
        }
        
        # Настройки эпизодической памяти
        self.episodic_settings = {
            'importance_decay_rate': 0.95,  # Скорость затухания важности со временем
            'max_memories': 100,          # Максимальное количество эпизодических воспоминаний
            'recency_weight': 0.3,        # Вес фактора новизны при расчете релевантности
            'importance_weight': 0.7      # Вес фактора важности при расчете релевантности
        }
    
    def _create_index(self, vectors, memory_type):
        """
        Создание индекса FAISS заданного типа
        
        Args:
            vectors (numpy.ndarray): Векторные представления текстов
            memory_type (str): Тип памяти (для логирования)
            
        Returns:
            faiss.Index: Созданный индекс FAISS
        """
        dimension = vectors.shape[1]
        num_vectors = vectors.shape[0]
        
        # Подготовка векторов
        if self.use_cosine:
            # Нормализация для косинусного сходства
            faiss.normalize_L2(vectors)
        
        # Выбор типа индекса в зависимости от параметров и размера данных
        if self.index_type == 'flat' or num_vectors < 1000:
            # Простой индекс на основе полного перебора, эффективен для малых наборов данных
            if self.use_cosine:
                print(f"Создание Flat IP индекса для {memory_type} (косинусное сходство)")
                index = faiss.IndexFlatIP(dimension)  # IP - внутреннее произведение (косинусное сходство)
            else:
                print(f"Создание Flat L2 индекса для {memory_type} (евклидово расстояние)")
                index = faiss.IndexFlatL2(dimension)  # L2 - евклидово расстояние
        
        elif self.index_type == 'ivf' and num_vectors >= 1000:
            # IVF (Inverted File) индекс, разбивает пространство на кластеры для быстрого поиска
            # Хорошо подходит для средних и больших наборов данных
            print(f"Создание IVF индекса для {memory_type}")
            nlist = min(int(np.sqrt(num_vectors) * 4), num_vectors // 10)  # Рекомендуемое число кластеров
            nlist = max(nlist, 8)  # Минимум 8 кластеров
            
            # Создаем квантователь (quantizer)
            if self.use_cosine:
                quantizer = faiss.IndexFlatIP(dimension)
                index = faiss.IndexIVFFlat(quantizer, dimension, nlist, faiss.METRIC_INNER_PRODUCT)
            else:
                quantizer = faiss.IndexFlatL2(dimension)
                index = faiss.IndexIVFFlat(quantizer, dimension, nlist, faiss.METRIC_L2)
            
            # Обучение индекса (требуется для IVF)
            if not index.is_trained:
                print(f"Обучение IVF индекса для {memory_type}...")
                index.train(vectors)
            
            # Установка числа проверяемых кластеров при поиске (компромисс между скоростью и точностью)
            index.nprobe = min(nlist // 2, 16)  # Рекомендуемое значение
        
        elif self.index_type == 'ivfpq' and num_vectors >= 5000:
            # IVF с Product Quantization - более компактное хранение и быстрый поиск
            # Хорошо подходит для больших наборов данных
            print(f"Создание IVFPQ индекса для {memory_type}")
            nlist = min(int(np.sqrt(num_vectors) * 4), num_vectors // 10)
            nlist = max(nlist, 8)  # Минимум 8 кластеров
            
            # Число подквантователей для PQ (обычно от 8 до 64, должно делить dimension)
            subquantizers = 8
            while dimension % subquantizers != 0 and subquantizers > 1:
                subquantizers -= 1
            
            # Создаем квантователь и индекс
            if self.use_cosine:
                quantizer = faiss.IndexFlatIP(dimension)
                index = faiss.IndexIVFPQ(quantizer, dimension, nlist, subquantizers, 8, faiss.METRIC_INNER_PRODUCT)
            else:
                quantizer = faiss.IndexFlatL2(dimension)
                index = faiss.IndexIVFPQ(quantizer, dimension, nlist, subquantizers, 8, faiss.METRIC_L2)
            
            # Обучение индекса
            if not index.is_trained:
                print(f"Обучение IVFPQ индекса для {memory_type}...")
                index.train(vectors)
            
            # Установка числа проверяемых кластеров
            index.nprobe = min(nlist // 2, 16)
        
        elif self.index_type == 'hnsw' and num_vectors >= 1000:
            # HNSW (Hierarchical Navigable Small World) - граф близости для быстрого поиска
            # Очень эффективен для многомерных данных
            print(f"Создание HNSW индекса для {memory_type}")
            M = 16  # Число исходящих связей в графе (обычно от 8 до 64)
            
            if self.use_cosine:
                index = faiss.IndexHNSWFlat(dimension, M, faiss.METRIC_INNER_PRODUCT)
            else:
                index = faiss.IndexHNSWFlat(dimension, M, faiss.METRIC_L2)
            
            # Настройка параметров построения
            index.hnsw.efConstruction = 40  # Влияет на качество построения графа (выше = лучше, но медленнее)
            index.hnsw.efSearch = 32  # Влияет на точность поиска (выше = точнее, но медленнее)
        
        else:
            # По умолчанию используем простой индекс
            print(f"Используем Flat индекс для {memory_type} по умолчанию")
            if self.use_cosine:
                index = faiss.IndexFlatIP(dimension)
            else:
                index = faiss.IndexFlatL2(dimension)
        
        # Добавляем векторы в индекс
        index.add(vectors)
        print(f"Индекс для {memory_type} создан, добавлено {num_vectors} векторов")
        
        return index
    
    def initialize_long_term_memory(self, character_data):
        """
        Инициализация долгосрочной памяти персонажа и создание индексов
        
        Args:
            character_data (dict): Словарь с данными о персонаже
        """
        print("Инициализация долгосрочной памяти...")
        
        # Заполняем долгосрочную память
        self.long_term_memory["facts"] = character_data.get("facts", [])
        self.long_term_memory["traits"] = character_data.get("traits", [])
        self.long_term_memory["speech_patterns"] = character_data.get("speech_patterns", [])
        
        # Сохраняем тексты для каждого типа памяти
        self.memory_texts["facts"] = self.long_term_memory["facts"]
        self.memory_texts["traits"] = self.long_term_memory["traits"]
        self.memory_texts["speech_patterns"] = self.long_term_memory["speech_patterns"]
        self.memory_texts["episodic"] = []  # Инициализируем пустой список для эпизодической памяти
        
        # Создаем индексы FAISS для каждого типа памяти
        for memory_type in ["facts", "traits", "speech_patterns"]:
            if self.long_term_memory[memory_type]:
                # Создаем эмбеддинги
                embeddings = self.model.encode(self.long_term_memory[memory_type])
                embeddings_np = np.array(embeddings).astype('float32')
                
                # Создаем индекс соответствующего типа
                self.indexes[memory_type] = self._create_index(embeddings_np, memory_type)
    
    def add_to_short_term_memory(self, message):
        """
        Добавление сообщения в краткосрочную память (контекст разговора)
        
        Args:
            message (str): Сообщение для добавления
        """
        # Добавляем новое сообщение
        self.short_term_memory.append(message)
        
        # Ограничиваем размер кратковременной памяти
        max_short_term_memory = 10  # Хранить последние 10 сообщений
        if len(self.short_term_memory) > max_short_term_memory:
            self.short_term_memory = self.short_term_memory[-max_short_term_memory:]
    
    def get_conversation_context(self):
        """
        Получение текущего контекста разговора из краткосрочной памяти
        
        Returns:
            str: Строка с последними сообщениями
        """
        return "\n".join(self.short_term_memory)
    
    def add_episodic_memory(self, text, importance=0.5, category=None, emotion=None):
        """
        Добавление нового эпизодического воспоминания
        
        Args:
            text (str): Текст воспоминания
            importance (float): Важность воспоминания (0.0-1.0)
            category (str, optional): Категория воспоминания (например, "личное", "работа", "отношения")
            emotion (str, optional): Эмоциональный окрас воспоминания
            
        Returns:
            int: Индекс добавленного воспоминания
        """
        # Создаем новое воспоминание
        memory_entry = {
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "unix_time": time.time(),  # Добавляем unix-время для удобства сортировки
            "importance": float(importance),
            "category": category,
            "emotion": emotion,
            "access_count": 0  # Счетчик обращений к воспоминанию
        }
        
        # Добавляем в список эпизодических воспоминаний
        self.episodic_memory.append(memory_entry)
        
        # Добавляем текст воспоминания в список текстов
        self.memory_texts["episodic"].append(text)
        
        # Создаем или обновляем индекс для эпизодической памяти
        self._update_episodic_index()
        
        # Проверяем и при необходимости выполняем очистку от маловажных воспоминаний
        self._prune_episodic_memories()
        
        # Возвращаем индекс добавленного воспоминания
        return len(self.episodic_memory) - 1
    
    def _update_episodic_index(self):
        """
        Создает или обновляет индекс FAISS для эпизодической памяти
        """
        if not self.memory_texts["episodic"]:
            return  # Нет эпизодических воспоминаний для индексации
        
        # Создаем эмбеддинги для всех эпизодических воспоминаний
        embeddings = self.model.encode(self.memory_texts["episodic"])
        embeddings_np = np.array(embeddings).astype('float32')
        
        # Создаем новый индекс
        self.indexes["episodic"] = self._create_index(embeddings_np, "episodic")
    
    def _prune_episodic_memories(self):
        """
        Удаляет наименее важные эпизодические воспоминания, если их количество превышает лимит
        """
        max_memories = self.episodic_settings['max_memories']
        
        # Если количество воспоминаний не превышает лимит, ничего не делаем
        if len(self.episodic_memory) <= max_memories:
            return
        
        # Вычисляем комбинированную оценку для каждого воспоминания
        # Комбинируем важность, новизну и частоту доступа
        current_time = time.time()
        
        # Сортируем воспоминания по их "сохраняемости" (комбинация важности и новизны)
        memories_with_scores = []
        for idx, memory in enumerate(self.episodic_memory):
            age = (current_time - memory["unix_time"]) / 86400.0  # Возраст в днях
            importance = memory["importance"]
            access_frequency = memory["access_count"] / (1 + age)  # Частота доступа с учетом возраста
            
            # Комбинированная оценка: 70% важность + 20% новизна + 10% частота доступа
            score = 0.7 * importance + 0.2 * (1.0 / (1.0 + age/30)) + 0.1 * min(1.0, access_frequency)
            
            memories_with_scores.append((idx, score))
        
        # Сортируем по оценке (от наименьшей к наибольшей)
        memories_with_scores.sort(key=lambda x: x[1])
        
        # Получаем индексы воспоминаний для удаления
        to_remove = memories_with_scores[:len(self.episodic_memory) - max_memories]
        indices_to_remove = [idx for idx, _ in to_remove]
        
        # Удаляем наименее важные воспоминания
        new_episodic_memory = []
        new_memory_texts = []
        
        for idx, memory in enumerate(self.episodic_memory):
            if idx not in indices_to_remove:
                new_episodic_memory.append(memory)
                new_memory_texts.append(self.memory_texts["episodic"][idx])
        
        # Обновляем списки
        self.episodic_memory = new_episodic_memory
        self.memory_texts["episodic"] = new_memory_texts
        
        # Создаем новый индекс
        self._update_episodic_index()
    
    def update_episodic_memory_importance(self, memory_index, new_importance):
        """
        Обновляет важность эпизодического воспоминания
        
        Args:
            memory_index (int): Индекс воспоминания
            new_importance (float): Новая важность (0.0-1.0)
            
        Returns:
            bool: True если обновление успешно, False в противном случае
        """
        if 0 <= memory_index < len(self.episodic_memory):
            self.episodic_memory[memory_index]["importance"] = float(new_importance)
            return True
        return False
    
    def decay_episodic_memories(self):
        """
        Применяет затухание важности к эпизодическим воспоминаниям с течением времени
        """
        decay_rate = self.episodic_settings['importance_decay_rate']
        current_time = time.time()
        
        for memory in self.episodic_memory:
            age_in_days = (current_time - memory["unix_time"]) / 86400.0
            
            # Применяем экспоненциальное затухание на основе возраста
            # Более старые воспоминания затухают быстрее
            decay_factor = decay_rate ** (age_in_days / 30)  # Затухание за каждый месяц
            
            # Но важность не может упасть ниже 0.1 для сохранения некоторых воспоминаний
            memory["importance"] = max(0.1, memory["importance"] * decay_factor)
    
    def _calculate_relevance(self, distance, method='sigmoid'):
        """
        Преобразование расстояния в значение релевантности
        
        Args:
            distance (float): Расстояние между векторами
            method (str): Метод расчета ('inverse', 'exponential', 'sigmoid')
            
        Returns:
            float: Значение релевантности (от 0 до 1)
        """
        if method == 'inverse':
            # Простое преобразование: релевантность = 1 / (1 + расстояние)
            return 1.0 / (1.0 + distance)
        
        elif method == 'exponential':
            # Экспоненциальное преобразование: быстрее убывает с расстоянием
            return np.exp(-distance)
        
        elif method == 'sigmoid':
            # Сигмоидное преобразование: более гладкий переход
            # Настраиваем сигмоиду так, чтобы небольшие расстояния давали высокую релевантность,
            # а большие - низкую
            steepness = 5.0  # Контролирует крутизну перехода
            midpoint = 1.0   # Точка перегиба (при этом расстоянии релевантность = 0.5)
            return 1.0 / (1.0 + np.exp(steepness * (distance - midpoint)))
        
        else:
            # По умолчанию используем простое преобразование
            return 1.0 / (1.0 + distance)
    
    def retrieve_relevant_memories(self, query, memory_types=None, top_k=3, relevance_method='sigmoid', min_relevance=0.2):
        """
        Поиск релевантных воспоминаний для заданного запроса
        
        Args:
            query (str): Текст запроса
            memory_types (list): Список типов памяти для поиска (None - все типы)
            top_k (int): Количество результатов для каждого типа памяти
            relevance_method (str): Метод расчета релевантности
            min_relevance (float): Минимальное значение релевантности для включения в результаты
            
        Returns:
            dict: Словарь с релевантными воспоминаниями по типам памяти
        """
        if memory_types is None:
            memory_types = ["facts", "traits", "speech_patterns", "episodic"]
        
        # Создаем эмбеддинг запроса
        query_embedding = self.model.encode([query])[0].reshape(1, -1).astype('float32')
        
        # Нормализация для косинусного сходства
        if self.use_cosine:
            faiss.normalize_L2(query_embedding)
        
        relevant_memories = {}
        
        # Поиск по каждому типу памяти
        for memory_type in memory_types:
            if memory_type in self.indexes and len(self.memory_texts[memory_type]) > 0:
                # Поиск в индексе
                k = min(top_k * 2, len(self.memory_texts[memory_type]))  # Получаем больше результатов для фильтрации
                distances, indices = self.indexes[memory_type].search(query_embedding, k)
                
                # Собираем и фильтруем результаты
                results = []
                for i, idx in enumerate(indices[0]):
                    if idx < len(self.memory_texts[memory_type]):
                        memory_text = self.memory_texts[memory_type][idx]
                        distance = distances[0][i]
                        
                        # Рассчитываем релевантность
                        relevance = self._calculate_relevance(distance, method=relevance_method)
                        
                        # Для эпизодических воспоминаний учитываем также важность и новизну
                        if memory_type == "episodic" and idx < len(self.episodic_memory):
                            # Получаем метаданные воспоминания
                            memory_meta = self.episodic_memory[idx]
                            
                            # Учитываем важность воспоминания
                            importance = memory_meta["importance"]
                            
                            # Учитываем новизну воспоминания
                            current_time = time.time()
                            age_in_days = (current_time - memory_meta["unix_time"]) / 86400.0
                            recency = 1.0 / (1.0 + age_in_days/30)  # Новизна: 1.0 для новых, убывает для старых
                            
                            # Комбинируем релевантность, важность и новизну
                            semantic_weight = 0.6  # Вес семантической релевантности
                            importance_weight = self.episodic_settings['importance_weight']  # Вес важности
                            recency_weight = self.episodic_settings['recency_weight']  # Вес новизны
                            
                            # Нормализуем веса
                            sum_weights = semantic_weight + importance_weight + recency_weight
                            semantic_weight /= sum_weights
                            importance_weight /= sum_weights
                            recency_weight /= sum_weights
                            
                            # Обновленная релевантность с учетом важности и новизны
                            relevance = (semantic_weight * relevance + 
                                         importance_weight * importance + 
                                         recency_weight * recency)
                            
                            # Увеличиваем счетчик обращений
                            self.episodic_memory[idx]["access_count"] += 1
                            
                            # Добавляем метаданные воспоминания к результату
                            extra_meta = {
                                "timestamp": memory_meta["timestamp"],
                                "importance": importance,
                                "category": memory_meta["category"],
                                "emotion": memory_meta["emotion"],
                                "age_days": age_in_days
                            }
                        else:
                            extra_meta = None
                        
                        # Фильтруем по минимальной релевантности
                        if relevance >= min_relevance:
                            result = {
                                "text": memory_text,
                                "relevance": relevance
                            }
                            
                            if extra_meta:
                                result.update(extra_meta)
                                
                            results.append(result)
                
                # Сортируем по релевантности и берем top_k результатов
                results = sorted(results, key=lambda x: x["relevance"], reverse=True)[:top_k]
                
                if results:  # Добавляем только если есть результаты
                    relevant_memories[memory_type] = results
        
        return relevant_memories
    
    def save_to_file(self, file_path):
        """
        Сохранение состояния памяти в файл
        
        Args:
            file_path (str): Путь к файлу для сохранения
        """
        print(f"Сохранение памяти в файл {file_path}...")
        
        # Создаем директорию, если она не существует
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Подготавливаем данные для сериализации
        # Мы не можем напрямую сериализовать объекты FAISS и модель,
        # поэтому сохраняем только необходимые данные
        memory_data = {
            'long_term_memory': self.long_term_memory,
            'short_term_memory': self.short_term_memory,
            'episodic_memory': self.episodic_memory,
            'memory_texts': self.memory_texts,
            'model_name': self.model_name,
            'index_type': self.index_type,
            'use_cosine': self.use_cosine,
            'episodic_settings': self.episodic_settings
        }
        
        # Сериализуем и сохраняем данные
        with open(file_path, 'wb') as f:
            pickle.dump(memory_data, f)
        
        print(f"Память успешно сохранена в {file_path}")
    
    @classmethod
    def load_from_file(cls, file_path):
        """
        Загрузка состояния памяти из файла
        
        Args:
            file_path (str): Путь к файлу для загрузки
            
        Returns:
            Memory: Объект памяти с загруженным состоянием
        """
        print(f"Загрузка памяти из файла {file_path}...")
        
        # Проверяем существование файла
        if not os.path.exists(file_path):
            print(f"Файл {file_path} не найден. Создаем новую память.")
            return cls()
        
        try:
            # Загружаем сериализованные данные
            with open(file_path, 'rb') as f:
                memory_data = pickle.load(f)
            
            # Извлекаем параметры
            model_name = memory_data.get('model_name', 'paraphrase-multilingual-MiniLM-L12-v2')
            index_type = memory_data.get('index_type', 'flat')
            use_cosine = memory_data.get('use_cosine', True)
            
            # Создаем новый экземпляр памяти с загруженными параметрами
            memory = cls(model_name, index_type, use_cosine)
            
            # Восстанавливаем данные памяти
            memory.long_term_memory = memory_data['long_term_memory']
            memory.short_term_memory = memory_data['short_term_memory']
            memory.memory_texts = memory_data['memory_texts']
            
            # Восстанавливаем эпизодическую память, если она есть
            if 'episodic_memory' in memory_data:
                memory.episodic_memory = memory_data['episodic_memory']
            else:
                memory.episodic_memory = []
                
            # Восстанавливаем настройки эпизодической памяти, если они есть
            if 'episodic_settings' in memory_data:
                memory.episodic_settings = memory_data['episodic_settings']
            
            # Восстанавливаем индексы FAISS
            for memory_type in ["facts", "traits", "speech_patterns", "episodic"]:
                if memory_type in memory.memory_texts and memory.memory_texts[memory_type]:
                    # Создаем эмбеддинги
                    embeddings = memory.model.encode(memory.memory_texts[memory_type])
                    embeddings_np = np.array(embeddings).astype('float32')
                    
                    # Создаем индекс
                    memory.indexes[memory_type] = memory._create_index(embeddings_np, memory_type)
            
            print(f"Память успешно загружена из {file_path}")
            return memory
            
        except Exception as e:
            print(f"Ошибка при загрузке памяти: {str(e)}")
            print("Создаем новую память.")
            return cls()