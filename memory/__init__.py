# memory/__init__.py

from .manager import MemoryManager

# Для обратной совместимости
Memory = MemoryManager

__all__ = ["MemoryManager", "Memory"]