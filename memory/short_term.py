# memory/short_term.py

from typing import List, Dict, Any
from .base import BaseMemory

class ShortTermMemory(BaseMemory):
    """
    Класс для хранения краткосрочной памяти (контекста разговора)
    """
    
    def __init__(self, max_messages: int = 10):
        """
        Инициализация краткосрочной памяти
        
        Args:
            max_messages (int): Максимальное количество сообщений
        """
        self.max_messages = max_messages
        self.messages = []
    
    def add_message(self, message: str) -> None:
        """
        Добавление сообщения в краткосрочную память
        
        Args:
            message (str): Текст сообщения
        """
        self.messages.append(message)
        
        # Удаляем старые сообщения, если превышен лимит
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_messages(self) -> List[str]:
        """
        Получение всех сообщений
        
        Returns:
            List[str]: Список сообщений
        """
        return self.messages
    
    def get_context(self) -> str:
        """
        Получение контекста разговора в виде строки
        
        Returns:
            str: Контекст разговора
        """
        return "\n".join(self.messages)
    
    def clear(self) -> None:
        """
        Очистка краткосрочной памяти
        """
        self.messages = []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование памяти в словарь для сериализации
        
        Returns:
            Dict: Словарь с данными
        """
        return {
            "max_messages": self.max_messages,
            "messages": self.messages
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Загрузка данных памяти из словаря
        
        Args:
            data (Dict): Словарь с данными
        """
        self.max_messages = data.get("max_messages", 10)
        self.messages = data.get("messages", [])