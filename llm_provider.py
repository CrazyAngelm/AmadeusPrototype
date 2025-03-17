# llm_provider.py

"""
Модуль для работы с разными провайдерами LLM.
Предоставляет единый интерфейс для взаимодействия с различными моделями.
"""

import os
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from functools import lru_cache
from dotenv import load_dotenv

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env файла
load_dotenv()

# Модели и их характеристики
MODELS_INFO = {
    "openai": {
        "gpt-4.5": {
            "description": "Самая продвинутая модель OpenAI с улучшенным эмоциональным интеллектом и сниженной склонностью к галлюцинациям",
            "max_tokens": 128000,
            "cost_per_1k_input": "$75.00",
            "cost_per_1k_output": "$75.00"
        },
        "gpt-4o": {
            "description": "Мультимодальная модель, способная обрабатывать и генерировать текст, изображения и аудио",
            "max_tokens": 128000,
            "cost_per_1k_input": "$5.00",
            "cost_per_1k_output": "$15.00"
        },
        "gpt-4o-mini": {
            "description": "Упрощенная и более быстрая версия GPT-4o, оптимизированная для быстрого выполнения задач",
            "max_tokens": 4096,
            "cost_per_1k_input": "$0.15",
            "cost_per_1k_output": "$0.60"
        },
        "gpt-3.5-turbo": {
            "description": "Быстрая и экономичная модель для повседневных задач",
            "max_tokens": 4096,
            "cost_per_1k_input": "$0.0005",
            "cost_per_1k_output": "$0.0015"
        },
        "openai-o3-mini": {
            "description": "Компактная модель с расширенными возможностями рассуждений, оптимизированная для задач в области математики, программирования и науки",
            "max_tokens": 4096,
            "cost_per_1k_input": "$0.10",
            "cost_per_1k_output": "$0.40"
        }
    },
    "anthropic": {
        "claude-3.7-sonnet-20250224": {
            "description": "Гибридная модель Claude, объединяющая быстрые ответы и глубокие рассуждения",
            "max_tokens": 128000,
            "cost_per_1k_input": "$3.00",
            "cost_per_1k_output": "$15.00"
        },
        "claude-3.5-sonnet-20250210": {
            "description": "Улучшенная версия Claude с повышенной производительностью, особенно в кодировании",
            "max_tokens": 4096,
            "cost_per_1k_input": "$3.00",
            "cost_per_1k_output": "$15.00"
        },
        "claude-3-haiku-20240307": {
            "description": "Самая быстрая и доступная модель Claude, оптимизированная для мгновенных ответов и повседневных задач",
            "max_tokens": 32000,
            "cost_per_1k_input": "$0.25",
            "cost_per_1k_output": "$1.25"
        }
    },
    "deepseek": {
        "deepseek-chat": {
            "description": "Модель с улучшенными возможностями рассуждений, превосходящая Llama 3.1 и Qwen 2.5, сопоставимая с GPT-4o и Claude 3.5 Sonnet",
            "max_tokens": 128000,
            "cost_per_1k_input": "$2.00",
            "cost_per_1k_output": "$2.00"
        },
        "deepseek-reasoner": {
            "description": "Модель, ориентированная на логическое мышление, математические рассуждения и решение задач в реальном времени, сопоставимая с OpenAI o1",
            "max_tokens": 128000,
            "cost_per_1k_input": "$1.50",
            "cost_per_1k_output": "$1.50"
        }
    }
}


class LLMProvider(ABC):
    """
    Абстрактный класс, определяющий интерфейс для провайдеров LLM
    """
    
    def __init__(self, model_name: str, api_key: Optional[str] = None):
        """
        Инициализация базового провайдера
        
        Args:
            model_name (str): Название модели для использования
            api_key (str, optional): API ключ. Если None, берется из переменных окружения
        """
        self.model_name = model_name
        self.api_key = api_key
        self._retry_settings = {
            "max_retries": 3,
            "initial_delay": 2,
            "backoff_factor": 1.5
        }
    
    @abstractmethod
    def _raw_generate(self, messages: List[Dict[str, str]], 
                    temperature: float = 0.7, 
                    max_tokens: int = 500,
                    stop: Optional[List[str]] = None,
                    **kwargs) -> str:
        """
        Непосредственное обращение к API провайдера LLM
        
        Args:
            messages (List[Dict[str, str]]): Список сообщений
            temperature (float): Температура генерации
            max_tokens (int): Максимальное количество токенов
            stop (List[str], optional): Стоп-последовательности
            **kwargs: Дополнительные параметры для передачи в API
            
        Returns:
            str: Сгенерированный текст
        """
        pass
    
    def generate(self, messages: List[Dict[str, str]], 
                temperature: float = 0.7, 
                max_tokens: int = 500,
                stop: Optional[List[str]] = None,
                **kwargs) -> str:
        """
        Генерация ответа на основе сообщений с повторными попытками
        
        Args:
            messages (List[Dict[str, str]]): Список сообщений в формате [{"role": "...", "content": "..."}]
            temperature (float): Температура генерации (0.0-1.0)
            max_tokens (int): Максимальное количество токенов в ответе
            stop (List[str], optional): Список строк, при обнаружении которых генерация останавливается
            **kwargs: Дополнительные параметры для передачи в API
            
        Returns:
            str: Сгенерированный текст
        """
        max_retries = self._retry_settings["max_retries"]
        retry_delay = self._retry_settings["initial_delay"]
        
        for attempt in range(max_retries):
            try:
                return self._raw_generate(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop,
                    **kwargs
                )
                
            except Exception as e:
                error_msg = str(e)
                if "rate limit" in error_msg.lower():
                    if attempt < max_retries - 1:
                        logger.warning(f"Превышен лимит запросов к {self.provider_name}. "
                                      f"Попытка {attempt+1}/{max_retries}, ожидание {retry_delay} сек...")
                        time.sleep(retry_delay)
                        retry_delay *= self._retry_settings["backoff_factor"]
                    else:
                        raise Exception(f"Превышен лимит запросов к {self.provider_name} после {max_retries} попыток. Попробуйте позже.")
                else:
                    # Другие ошибки
                    if attempt < max_retries - 1:
                        logger.warning(f"Ошибка API {self.provider_name}: {error_msg}. "
                                      f"Попытка {attempt+1}/{max_retries}, ожидание {retry_delay} сек...")
                        time.sleep(retry_delay)
                        retry_delay *= self._retry_settings["backoff_factor"]
                    else:
                        raise Exception(f"Ошибка API {self.provider_name} после {max_retries} попыток: {error_msg}")
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Возвращает название провайдера
        """
        pass
    
    @property
    def available_models(self) -> List[str]:
        """
        Возвращает список доступных моделей для данного провайдера
        """
        return list(MODELS_INFO.get(self.provider_name.lower(), {}).keys())
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Возвращает информацию о модели
        
        Args:
            model_name (str): Название модели
            
        Returns:
            Dict[str, Any]: Информация о модели
        """
        provider = self.provider_name.lower()
        if provider in MODELS_INFO and model_name in MODELS_INFO[provider]:
            return MODELS_INFO[provider][model_name]
        return {"description": "Информация о модели недоступна"}

class OpenAIProvider(LLMProvider):
    """
    Провайдер для моделей OpenAI (GPT-4, GPT-3.5, etc.)
    """
    
    def __init__(self, model_name="gpt-4o-mini", api_key=None):
        """
        Инициализация провайдера OpenAI
        
        Args:
            model_name (str): Название модели для использования
            api_key (str, optional): API ключ. Если None, берется из переменной окружения OPENAI_API_KEY
        """
        super().__init__(model_name, api_key)
        
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "OpenAI Python пакет не установлен. Установите его с помощью 'pip install openai'"
            )
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "Не найден API ключ для OpenAI. Укажите его при создании провайдера или "
                "установите переменную окружения OPENAI_API_KEY."
            )
        
        self.client = OpenAI(api_key=self.api_key)
    
    def _raw_generate(self, messages, temperature=0.7, max_tokens=500, stop=None, **kwargs):
        """
        Непосредственное обращение к API OpenAI
        """
        # Создаем параметры для запроса
        request_params = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # Добавляем стоп-последовательности, если они указаны
        if stop:
            request_params["stop"] = stop
        
        # Добавляем дополнительные параметры
        for param, value in kwargs.items():
            # Проверяем, соответствует ли параметр API OpenAI
            if param in ["top_p", "frequency_penalty", "presence_penalty", "top_k"]:
                if param == "top_k":  # OpenAI использует n вместо top_k
                    request_params["n"] = value
                else:
                    request_params[param] = value
        
        # Отправляем запрос к API
        response = self.client.chat.completions.create(**request_params)
        
        return response.choices[0].message.content
    
    @property
    def provider_name(self):
        return "OpenAI"

class AnthropicProvider(LLMProvider):
    """
    Провайдер для моделей Anthropic (Claude)
    """
    
    def __init__(self, model_name="claude-3-haiku-20240307", api_key=None):
        """
        Инициализация провайдера Anthropic
        
        Args:
            model_name (str): Название модели для использования
            api_key (str, optional): API ключ. Если None, берется из переменной окружения ANTHROPIC_API_KEY
        """
        super().__init__(model_name, api_key)
        
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "Anthropic Python пакет не установлен. Установите его с помощью 'pip install anthropic'"
            )
        
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "Не найден API ключ для Anthropic. Укажите его при создании провайдера или "
                "установите переменную окружения ANTHROPIC_API_KEY."
            )
        
        self.client = Anthropic(api_key=self.api_key)
    
    def _raw_generate(self, messages, temperature=0.7, max_tokens=500, stop=None, **kwargs):
        """
        Непосредственное обращение к API Anthropic
        """
        # Преобразуем формат сообщений из OpenAI в формат Anthropic
        system_message = None
        anthropic_messages = []
        
        for message in messages:
            if message["role"] == "system":
                system_message = message["content"]
            else:
                anthropic_messages.append({
                    "role": message["role"],
                    "content": message["content"]
                })
        
        # Создаем параметры для запроса
        request_params = {
            "model": self.model_name,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # Добавляем системное сообщение, если оно есть
        if system_message:
            request_params["system"] = system_message
        
        # Добавляем стоп-последовательности, если они указаны
        if stop:
            request_params["stop_sequences"] = stop
        
        # Добавляем дополнительные параметры
        for param, value in kwargs.items():
            # Проверяем, соответствует ли параметр API Anthropic
            if param in ["top_p", "top_k"]:
                request_params[param] = value
        
        # Отправляем запрос к API
        response = self.client.messages.create(**request_params)
        
        return response.content[0].text
    
    @property
    def provider_name(self):
        return "Anthropic"

class DeepSeekProvider(LLMProvider):
    """
    Провайдер для моделей DeepSeek
    """
    
    def __init__(self, model_name="deepseek-chat", api_key=None):
        """
        Инициализация провайдера DeepSeek
        
        Args:
            model_name (str): Название модели для использования
            api_key (str, optional): API ключ. Если None, берется из переменной окружения DEEPSEEK_API_KEY
        """
        super().__init__(model_name, api_key)
        
        try:
            import requests
        except ImportError:
            raise ImportError(
                "Requests пакет не установлен. Установите его с помощью 'pip install requests'"
            )
        
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "Не найден API ключ для DeepSeek. Укажите его при создании провайдера или "
                "установите переменную окружения DEEPSEEK_API_KEY."
            )
        
        self.api_base = "https://api.deepseek.com/v1"
    
    def _raw_generate(self, messages, temperature=0.7, max_tokens=500, stop=None, **kwargs):
        """
        Непосредственное обращение к API DeepSeek
        """
        import requests
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Создаем параметры для запроса
        data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Добавляем стоп-последовательности, если они указаны
        if stop:
            data["stop"] = stop
        
        # Добавляем дополнительные параметры
        for param, value in kwargs.items():
            # Проверяем, соответствует ли параметр API DeepSeek
            if param in ["top_p", "top_k", "presence_penalty", "frequency_penalty"]:
                data[param] = value
        
        response = requests.post(
            f"{self.api_base}/chat/completions",
            headers=headers,
            json=data,
            timeout=60  # Увеличиваем таймаут до 60 секунд
        )
        
        if response.status_code != 200:
            raise Exception(f"HTTP ошибка: {response.status_code} - {response.text}")
        
        return response.json()["choices"][0]["message"]["content"]
    
    @property
    def provider_name(self):
        return "DeepSeek"

@lru_cache(maxsize=32)
def get_provider(provider_name, model_name=None, api_key=None):
    """
    Создает и возвращает провайдера LLM по имени с использованием кэширования
    
    Args:
        provider_name (str): Название провайдера ("openai", "anthropic", "deepseek")
        model_name (str, optional): Название модели
        api_key (str, optional): API ключ
        
    Returns:
        LLMProvider: Объект провайдера
    """
    provider_name = provider_name.lower()
    
    # Определяем модель по умолчанию для провайдера, если не указана
    if model_name is None:
        if provider_name == "openai":
            model_name = "gpt-4o-mini"
        elif provider_name == "anthropic":
            model_name = "claude-3-haiku-20240307"
        elif provider_name == "deepseek":
            model_name = "deepseek-chat"
    
    # Если клиента нет в кэше, создаем нового
    try:
        if provider_name == "openai":
            provider = OpenAIProvider(model_name=model_name, api_key=api_key)
        elif provider_name == "anthropic":
            provider = AnthropicProvider(model_name=model_name, api_key=api_key)
        elif provider_name == "deepseek":
            provider = DeepSeekProvider(model_name=model_name, api_key=api_key)
        else:
            raise ValueError(f"Неизвестный провайдер: {provider_name}")
        
        logger.info(f"Создан новый клиент {provider_name}/{model_name}")
        return provider
    except Exception as e:
        error_msg = f"Не удалось инициализировать провайдер {provider_name}: {str(e)}"
        logger.error(error_msg)
        
        # В случае ошибки пытаемся использовать OpenAI как запасной вариант
        if provider_name != "openai":
            logger.warning(f"Пытаемся использовать OpenAI в качестве запасного варианта...")
            return get_provider("openai", None, None)
        else:
            raise ValueError(error_msg)

def list_available_providers():
    """
    Возвращает список доступных провайдеров и их моделей
    
    Returns:
        Dict: Информация о провайдерах и моделях
    """
    providers = {}
    
    for provider_name, models in MODELS_INFO.items():
        providers[provider_name] = {
            "description": f"Провайдер для моделей {provider_name.capitalize()}",
            "models": list(models.keys())
        }
    
    return providers

def clear_provider_cache():
    """
    Очищает кэш LLM провайдеров
    """
    # Получаем доступ к внутреннему кэшу декоратора lru_cache
    get_provider.cache_clear()
    logger.info("Кэш LLM провайдеров очищен")