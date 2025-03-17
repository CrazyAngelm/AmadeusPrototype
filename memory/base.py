# memory/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseMemory(ABC):
    """
    Базовый абстрактный класс для всех типов памяти
    """
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует память в словарь для сериализации
        
        Returns:
            Dict: Словарь с данными
        """
        pass
    
    @abstractmethod
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Загружает данные памяти из словаря
        
        Args:
            data (Dict): Словарь с данными
        """
        pass