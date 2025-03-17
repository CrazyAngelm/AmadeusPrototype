# llm_provider.py

"""
Модуль для работы с разными провайдерами LLM.
Предоставляет единый интерфейс для взаимодействия с различными моделями.
"""

import os
import json
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Кэш LLM клиентов для повторного использования
_LLM_CLIENT_CACHE = {}

class LLMProvider(ABC):
    """
    Абстрактный класс, определяющий интерфейс для провайдеров LLM
    """
    
    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], 
                temperature: float = 0.7, 
                max_tokens: int = 500,
                stop: Optional[List[str]] = None) -> str:
        """
        Генерация ответа на основе сообщений
        
        Args:
            messages (List[Dict[str, str]]): Список сообщений в формате [{"role": "...", "content": "..."}]
            temperature (float): Температура генерации (0.0-1.0)
            max_tokens (int): Максимальное количество токенов в ответе
            stop (List[str], optional): Список строк, при обнаружении которых генерация останавливается
            
        Returns:
            str: Сгенерированный текст
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Возвращает название провайдера
        """
        pass
    
    @property
    @abstractmethod
    def available_models(self) -> List[str]:
        """
        Возвращает список доступных моделей
        """
        pass
    
    @abstractmethod
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Возвращает информацию о модели
        
        Args:
            model_name (str): Название модели
            
        Returns:
            Dict[str, Any]: Информация о модели
        """
        pass

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
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "OpenAI Python пакет не установлен. Установите его с помощью 'pip install openai'"
            )
        
        self.model_name = model_name
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError(
                "Не найден API ключ для OpenAI. Укажите его при создании провайдера или "
                "установите переменную окружения OPENAI_API_KEY."
            )
        
        self.client = OpenAI(api_key=api_key)
        
        # Словарь с информацией о моделях
        self._models_info = {
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
        }

    
    def generate(self, messages, temperature=0.7, max_tokens=500, stop=None):
        """
        Генерация ответа с использованием API OpenAI с повторными попытками
        """
        max_retries = 3
        retry_delay = 2  # начальная задержка в секундах
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                error_msg = str(e)
                if "rate limit" in error_msg.lower():
                    if attempt < max_retries - 1:
                        print(f"Превышен лимит запросов к OpenAI. Попытка {attempt+1}/{max_retries}, ожидание {retry_delay} сек...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Экспоненциальное увеличение задержки
                    else:
                        raise Exception(f"Превышен лимит запросов к OpenAI после {max_retries} попыток. Попробуйте позже.")
                else:
                    # Другие ошибки
                    if attempt < max_retries - 1:
                        print(f"Ошибка API OpenAI: {error_msg}. Попытка {attempt+1}/{max_retries}, ожидание {retry_delay} сек...")
                        time.sleep(retry_delay)
                        retry_delay *= 1.5
                    else:
                        raise Exception(f"Ошибка API OpenAI после {max_retries} попыток: {error_msg}")
    
    @property
    def provider_name(self):
        return "OpenAI"
    
    @property
    def available_models(self):
        return list(self._models_info.keys())
    
    def get_model_info(self, model_name):
        return self._models_info.get(model_name, {"description": "Информация о модели недоступна"})

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
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "Anthropic Python пакет не установлен. Установите его с помощью 'pip install anthropic'"
            )
        
        self.model_name = model_name
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            raise ValueError(
                "Не найден API ключ для Anthropic. Укажите его при создании провайдера или "
                "установите переменную окружения ANTHROPIC_API_KEY."
            )
        
        self.client = Anthropic(api_key=api_key)
        
        # Словарь с информацией о моделях
        self._models_info = {
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
}

    
    def generate(self, messages, temperature=0.7, max_tokens=500, stop=None):
        """
        Генерация ответа с использованием API Anthropic с повторными попытками
        """
        max_retries = 3
        retry_delay = 2  # начальная задержка в секундах
        
        for attempt in range(max_retries):
            try:
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
                
                response = self.client.messages.create(
                    model=self.model_name,
                    system=system_message,
                    messages=anthropic_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop_sequences=stop
                )
                
                return response.content[0].text
                
            except Exception as e:
                error_msg = str(e)
                if "rate limit" in error_msg.lower():
                    if attempt < max_retries - 1:
                        print(f"Превышен лимит запросов к Anthropic. Попытка {attempt+1}/{max_retries}, ожидание {retry_delay} сек...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Экспоненциальное увеличение задержки
                    else:
                        raise Exception(f"Превышен лимит запросов к Anthropic после {max_retries} попыток. Попробуйте позже.")
                else:
                    # Другие ошибки
                    if attempt < max_retries - 1:
                        print(f"Ошибка API Anthropic: {error_msg}. Попытка {attempt+1}/{max_retries}, ожидание {retry_delay} сек...")
                        time.sleep(retry_delay)
                        retry_delay *= 1.5
                    else:
                        raise Exception(f"Ошибка API Anthropic после {max_retries} попыток: {error_msg}")
    
    @property
    def provider_name(self):
        return "Anthropic"
    
    @property
    def available_models(self):
        return list(self._models_info.keys())
    
    def get_model_info(self, model_name):
        return self._models_info.get(model_name, {"description": "Информация о модели недоступна"})

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
        try:
            import requests
        except ImportError:
            raise ImportError(
                "Requests пакет не установлен. Установите его с помощью 'pip install requests'"
            )
        
        self.model_name = model_name
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "Не найден API ключ для DeepSeek. Укажите его при создании провайдера или "
                "установите переменную окружения DEEPSEEK_API_KEY."
            )
        
        self.api_base = "https://api.deepseek.com/v1"
        
        # Словарь с информацией о моделях
        self._models_info = {
        "deepseek-chat": {
            "description": "Модель с улучшенными возможностями рассуждений, превосходящая Llama 3.1 и Qwen 2.5, сопоставимая с GPT-4o и Claude 3.5 Sonnet",
            "max_tokens": 128000,
            "cost_per_1k_input": "$2.00",
            "cost_per_1k_output": "$2.00"
        },
        "deepseek-r1": {
            "description": "Модель, ориентированная на логическое мышление, математические рассуждения и решение задач в реальном времени, сопоставимая с OpenAI o1",
            "max_tokens": 128000,
            "cost_per_1k_input": "$1.50",
            "cost_per_1k_output": "$1.50"
        }
    }

    
    def generate(self, messages, temperature=0.7, max_tokens=500, stop=None):
        """
        Генерация ответа с использованием API DeepSeek с повторными попытками
        """
        import requests
        
        max_retries = 3
        retry_delay = 2  # начальная задержка в секундах
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if stop:
            data["stop"] = stop
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30  # Добавляем таймаут для запроса
                )
                
                if response.status_code != 200:
                    error_msg = f"HTTP ошибка: {response.status_code} - {response.text}"
                    if response.status_code in [429, 500, 502, 503, 504]:  # Повторяемые ошибки
                        if attempt < max_retries - 1:
                            print(f"{error_msg}. Попытка {attempt+1}/{max_retries}, ожидание {retry_delay} сек...")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                    raise Exception(error_msg)
                
                return response.json()["choices"][0]["message"]["content"]
                
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"Ошибка соединения с DeepSeek API: {str(e)}. Попытка {attempt+1}/{max_retries}, ожидание {retry_delay} сек...")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                else:
                    raise Exception(f"Не удалось соединиться с DeepSeek API после {max_retries} попыток: {str(e)}")
    
    @property
    def provider_name(self):
        return "DeepSeek"
    
    @property
    def available_models(self):
        return list(self._models_info.keys())
    
    def get_model_info(self, model_name):
        return self._models_info.get(model_name, {"description": "Информация о модели недоступна"})

def get_provider(provider_name, model_name=None, api_key=None):
    """
    Создает и возвращает провайдера LLM по имени
    
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
    
    # Формируем ключ кэша
    cache_key = f"{provider_name}:{model_name}:{api_key}"
    
    # Проверяем, есть ли уже готовый клиент в кэше
    if cache_key in _LLM_CLIENT_CACHE:
        print(f"Используем кэшированного клиента {provider_name}/{model_name}")
        return _LLM_CLIENT_CACHE[cache_key]
    
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
        
        # Сохраняем в кэш
        _LLM_CLIENT_CACHE[cache_key] = provider
        print(f"Создан новый клиент {provider_name}/{model_name} и добавлен в кэш")
        
        return provider
    except Exception as e:
        error_msg = f"Не удалось инициализировать провайдер {provider_name}: {str(e)}"
        print(error_msg)
        
        # В случае ошибки пытаемся использовать OpenAI как запасной вариант
        if provider_name != "openai":
            print(f"Пытаемся использовать OpenAI в качестве запасного варианта...")
            return get_provider("openai", None, None)
        else:
            raise ValueError(error_msg)

def list_available_providers():
    """
    Возвращает список доступных провайдеров и их моделей
    
    Returns:
        Dict: Информация о провайдерах и моделях
    """
    providers = {
        "openai": {
            "description": "Провайдер для моделей OpenAI",
            "models": [
                "gpt-4.5",
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-3.5-turbo",
                "openai-o3-mini"
            ]
        },
        "anthropic": {
            "description": "Провайдер для моделей Anthropic Claude",
            "models": [
                "claude-3.7-sonnet-20250224",
                "claude-3.5-sonnet-20250210",
                "claude-3-haiku-20240307"
            ]
        },
        "deepseek": {
            "description": "Провайдер для моделей DeepSeek",
            "models": [
                "deepseek-chat",
                "deepseek-r1"
            ]
        }
    }

    
    return providers

def clear_provider_cache():
    """
    Очищает кэш LLM провайдеров
    """
    global _LLM_CLIENT_CACHE
    _LLM_CLIENT_CACHE = {}
    print("Кэш LLM провайдеров очищен")