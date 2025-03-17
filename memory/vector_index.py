# memory/vector_index.py

import numpy as np
import faiss
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

class VectorIndex:
    """
    Класс для создания и управления векторными индексами FAISS
    """
    
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2', 
                index_type='flat', use_cosine=True):
        """
        Инициализация векторного индекса
        
        Args:
            model_name (str): Название модели sentence-transformers
            index_type (str): Тип индекса FAISS ('flat', 'ivf', 'ivfpq', 'hnsw')
            use_cosine (bool): Использовать ли косинусное сходство вместо евклидова расстояния
        """
        self.model_name = model_name
        self.index_type = index_type
        self.use_cosine = use_cosine
        
        # Загрузка модели для создания эмбеддингов
        logger.info(f"Загрузка модели {model_name}...")
        self.model = SentenceTransformer(model_name)
        logger.info("Модель успешно загружена")
        
        # Словари для хранения индексов и текстов
        self.indexes = {}
        self.texts = {}
    
    def create_index(self, memory_type: str, texts: List[str]) -> None:
        """
        Создание нового индекса для указанного типа памяти
        
        Args:
            memory_type (str): Тип памяти ('facts', 'traits', 'speech_patterns', 'episodic')
            texts (List[str]): Тексты для индексации
        """
        if not texts:
            logger.warning(f"Не удалось создать индекс для {memory_type}: пустой список текстов")
            return
        
        # Создаем эмбеддинги
        embeddings = self.model.encode(texts)
        embeddings_np = np.array(embeddings).astype('float32')
        
        # Создаем индекс
        dimension = embeddings_np.shape[1]
        num_vectors = len(texts)
        
        # Подготовка векторов
        if self.use_cosine:
            # Нормализация для косинусного сходства
            faiss.normalize_L2(embeddings_np)
        
        # Выбор типа индекса в зависимости от параметров и размера данных
        if self.index_type == 'flat' or num_vectors < 1000:
            # Простой индекс на основе полного перебора
            if self.use_cosine:
                logger.info(f"Создание Flat IP индекса для {memory_type} (косинусное сходство)")
                index = faiss.IndexFlatIP(dimension)
            else:
                logger.info(f"Создание Flat L2 индекса для {memory_type} (евклидово расстояние)")
                index = faiss.IndexFlatL2(dimension)
        
        elif self.index_type == 'ivf' and num_vectors >= 1000:
            # IVF (Inverted File) индекс
            logger.info(f"Создание IVF индекса для {memory_type}")
            nlist = min(int(np.sqrt(num_vectors) * 4), num_vectors // 10)
            nlist = max(nlist, 8)  # Минимум 8 кластеров
            
            if self.use_cosine:
                quantizer = faiss.IndexFlatIP(dimension)
                index = faiss.IndexIVFFlat(quantizer, dimension, nlist, faiss.METRIC_INNER_PRODUCT)
            else:
                quantizer = faiss.IndexFlatL2(dimension)
                index = faiss.IndexIVFFlat(quantizer, dimension, nlist, faiss.METRIC_L2)
            
            # Обучение индекса (требуется для IVF)
            if not index.is_trained:
                logger.info(f"Обучение IVF индекса для {memory_type}...")
                index.train(embeddings_np)
            
            # Установка числа проверяемых кластеров
            index.nprobe = min(nlist // 2, 16)
        
        elif self.index_type == 'hnsw' and num_vectors >= 1000:
            # HNSW (Hierarchical Navigable Small World)
            logger.info(f"Создание HNSW индекса для {memory_type}")
            M = 16  # Число исходящих связей в графе (обычно от 8 до 64)
            
            if self.use_cosine:
                index = faiss.IndexHNSWFlat(dimension, M, faiss.METRIC_INNER_PRODUCT)
            else:
                index = faiss.IndexHNSWFlat(dimension, M, faiss.METRIC_L2)
            
            # Настройка параметров построения
            index.hnsw.efConstruction = 40
            index.hnsw.efSearch = 32
        
        else:
            # По умолчанию используем простой индекс
            logger.info(f"Используем Flat индекс для {memory_type} по умолчанию")
            if self.use_cosine:
                index = faiss.IndexFlatIP(dimension)
            else:
                index = faiss.IndexFlatL2(dimension)
        
        # Добавляем векторы в индекс
        index.add(embeddings_np)
        logger.info(f"Индекс для {memory_type} создан, добавлено {num_vectors} векторов")
        
        # Сохраняем индекс и тексты
        self.indexes[memory_type] = index
        self.texts[memory_type] = texts
    
    def update_index(self, memory_type: str, new_texts: List[str]) -> None:
        """
        Обновление существующего индекса новыми текстами
        
        Args:
            memory_type (str): Тип памяти
            new_texts (List[str]): Новые тексты для добавления
        """
        if not new_texts:
            return
        
        # Если индекс еще не существует, создаем новый
        if memory_type not in self.indexes:
            self.create_index(memory_type, new_texts)
            return
        
        # Создаем эмбеддинги для новых текстов
        embeddings = self.model.encode(new_texts)
        embeddings_np = np.array(embeddings).astype('float32')
        
        # Подготовка векторов
        if self.use_cosine:
            faiss.normalize_L2(embeddings_np)
        
        # Добавляем новые векторы в индекс
        self.indexes[memory_type].add(embeddings_np)
        
        # Обновляем список текстов
        if memory_type in self.texts:
            self.texts[memory_type].extend(new_texts)
        else:
            self.texts[memory_type] = new_texts
    
    def rebuild_index(self, memory_type: str, texts: List[str]) -> None:
        """
        Полная перестройка индекса
        
        Args:
            memory_type (str): Тип памяти
            texts (List[str]): Полный список текстов
        """
        if memory_type in self.indexes:
            del self.indexes[memory_type]
        
        self.create_index(memory_type, texts)
    
    def search(self, memory_type: str, query: str, top_k: int = 5, 
              relevance_method: str = 'sigmoid', min_relevance: float = 0.2) -> List[Dict[str, Any]]:
        """
        Поиск релевантных текстов
        
        Args:
            memory_type (str): Тип памяти
            query (str): Текст запроса
            top_k (int): Количество результатов
            relevance_method (str): Метод расчета релевантности
            min_relevance (float): Минимальное значение релевантности
            
        Returns:
            List[Dict[str, Any]]: Список релевантных результатов
        """
        if memory_type not in self.indexes or memory_type not in self.texts:
            return []
        
        # Создаем эмбеддинг запроса
        query_embedding = self.model.encode([query])[0].reshape(1, -1).astype('float32')
        
        # Нормализация для косинусного сходства
        if self.use_cosine:
            faiss.normalize_L2(query_embedding)
        
        # Поиск ближайших соседей
        k = min(top_k, len(self.texts[memory_type]))
        distances, indices = self.indexes[memory_type].search(query_embedding, k)
        
        # Собираем результаты
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.texts[memory_type]):
                text = self.texts[memory_type][idx]
                distance = distances[0][i]
                
                # Рассчитываем релевантность
                relevance = self._calculate_relevance(distance, method=relevance_method)
                
                # Если релевантность достаточная, добавляем в результаты
                if relevance >= min_relevance:
                    results.append({
                        "text": text,
                        "index": idx,
                        "distance": distance,
                        "relevance": relevance
                    })
        
        return results
    
    def _calculate_relevance(self, distance: float, method: str = 'sigmoid') -> float:
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
            steepness = 5.0  # Контролирует крутизну перехода
            midpoint = 1.0   # Точка перегиба (при этом расстоянии релевантность = 0.5)
            return 1.0 / (1.0 + np.exp(steepness * (distance - midpoint)))
        
        else:
            # По умолчанию используем простое преобразование
            return 1.0 / (1.0 + distance)