# relationship.py

"""
Модуль для управления отношениями персонажа к пользователю.
Отслеживает и изменяет различные аспекты отношений на основе взаимодействий.
"""

import time
import json
import re
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class RelationshipAspect:
    """
    Представляет один аспект отношений (уважение, доверие, симпатия, терпение)
    """
    
    def __init__(self, name: str, initial_value: float = 0.0, weight: float = 0.25):
        """
        Инициализация аспекта отношений
        
        Args:
            name (str): Название аспекта
            initial_value (float): Начальное значение (-1.0 до 1.0)
            weight (float): Вес аспекта в общей оценке отношений
        """
        self.name = name
        self.value = max(-1.0, min(1.0, initial_value))
        self.weight = weight
    
    def update(self, change: float) -> float:
        """
        Обновление значения аспекта
        
        Args:
            change (float): Величина изменения
            
        Returns:
            float: Новое значение
        """
        old_value = self.value
        self.value = max(-1.0, min(1.0, self.value + change))
        return self.value - old_value
    
    def get_description(self) -> str:
        """
        Получение текстового описания аспекта
        
        Returns:
            str: Описание аспекта
        """
        if self.value > 0.7:
            return f"очень высокое {self.name}"
        elif self.value > 0.3:
            return f"высокое {self.name}"
        elif self.value > -0.3:
            return f"нейтральное {self.name}"
        elif self.value > -0.7:
            return f"низкое {self.name}"
        else:
            return f"очень низкое {self.name}"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Сериализация аспекта
        
        Returns:
            Dict: Словарь с данными
        """
        return {
            "name": self.name,
            "value": self.value,
            "weight": self.weight
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RelationshipAspect':
        """
        Десериализация аспекта
        
        Args:
            data (Dict): Словарь с данными
            
        Returns:
            RelationshipAspect: Объект аспекта
        """
        return cls(
            name=data.get("name", ""),
            initial_value=data.get("value", 0.0),
            weight=data.get("weight", 0.25)
        )


class Relationship:
    """
    Класс для отслеживания отношений персонажа к пользователю
    """
    
    def __init__(self, character_name: str, initial_rapport: float = 0.0, 
                 initial_aspects: Optional[Dict[str, float]] = None, 
                 personality_factors: Optional[Dict[str, float]] = None):
        """
        Инициализация отношений
        
        Args:
            character_name (str): Имя персонажа
            initial_rapport (float): Начальный уровень общего отношения (-1.0 до 1.0)
            initial_aspects (dict): Начальные значения различных аспектов отношений
            personality_factors (dict): Факторы личности, влияющие на изменение отношений
        """
        self.character_name = character_name
        
        # Общий уровень отношений (от -1.0 до 1.0)
        self.rapport = initial_rapport
        
        # Инициализация аспектов отношений с весами
        aspect_weights = {
            "respect": 0.3,    # уважение
            "trust": 0.3,      # доверие
            "liking": 0.25,    # симпатия
            "patience": 0.15   # терпение
        }
        
        init_values = initial_aspects or {
            "respect": 0.0,
            "trust": 0.0,
            "liking": 0.0,
            "patience": 0.0
        }
        
        self.aspects = {}
        for name, weight in aspect_weights.items():
            value = init_values.get(name, 0.0)
            self.aspects[name] = RelationshipAspect(name, value, weight)
        
        # Факторы личности персонажа, влияющие на изменение отношений
        self.personality_factors = personality_factors or {
            "intellect_appreciation": 0.5,  # ценит интеллект
            "humor_appreciation": 0.5,      # ценит юмор
            "formality_preference": 0.5,    # предпочитает формальность
            "openness": 0.5,                # открытость к новому
            "sensitivity": 0.5,             # чувствительность к обидам
            "forgiveness": 0.5              # склонность прощать
        }
        
        # История изменений отношений
        self.history = []
        
        # Временные метки
        self.created_at = time.time()
        self.last_updated = time.time()
        
        # Сохраняем начальное состояние в историю
        self._add_to_history("Начальное состояние", self.rapport, self._get_aspect_values(), 0.0)
    
    def _get_aspect_values(self) -> Dict[str, float]:
        """
        Получение текущих значений всех аспектов
        
        Returns:
            Dict[str, float]: Словарь с значениями аспектов
        """
        return {name: aspect.value for name, aspect in self.aspects.items()}
    
    def _add_to_history(self, reason: str, rapport: float, aspects: Dict[str, float], 
                       change_magnitude: float) -> None:
        """
        Добавляет изменение отношений в историю
        
        Args:
            reason (str): Причина изменения
            rapport (float): Новое значение общего отношения
            aspects (dict): Новые значения аспектов
            change_magnitude (float): Величина изменения (для определения важности)
        """
        timestamp = time.time()
        
        entry = {
            "timestamp": timestamp,
            "datetime": datetime.fromtimestamp(timestamp).isoformat(),
            "reason": reason,
            "rapport": rapport,
            "aspects": aspects.copy(),
            "change_magnitude": change_magnitude
        }
        
        self.history.append(entry)
        self.last_updated = timestamp
        
        # Ограничиваем размер истории
        if len(self.history) > 50:
            self.history = self.history[-50:]
    
    def update_from_interaction(self, user_message: str, character_response: str) -> Dict[str, Any]:
        """
        Обновляет отношения на основе взаимодействия
        
        Args:
            user_message (str): Сообщение пользователя
            character_response (str): Ответ персонажа
            
        Returns:
            dict: Информация об изменении отношений
        """
        # Нормализуем текст для анализа
        user_text = user_message.lower()
        response_text = character_response.lower()
        
        # Анализ текста для выявления факторов, влияющих на отношения
        factors = self._analyze_interaction(user_text, response_text)
        
        # Рассчитываем изменения в аспектах отношений
        aspect_changes = self._calculate_aspect_changes(factors)
        
        # Сохраняем старые значения для расчета изменений
        old_rapport = self.rapport
        old_aspects = self._get_aspect_values()
        
        # Обновляем аспекты
        for aspect_name, change in aspect_changes.items():
            if aspect_name in self.aspects:
                self.aspects[aspect_name].update(change)
        
        # Рассчитываем новый общий уровень отношений как взвешенное среднее аспектов
        weighted_sum = sum(aspect.value * aspect.weight for aspect in self.aspects.values())
        total_weight = sum(aspect.weight for aspect in self.aspects.values())
        
        self.rapport = max(-1.0, min(1.0, weighted_sum / total_weight))
        
        # Вычисляем общую величину изменения
        aspect_change_magnitude = sum(abs(change) for change in aspect_changes.values())
        rapport_change = abs(self.rapport - old_rapport)
        change_magnitude = (aspect_change_magnitude + rapport_change) / 2
        
        # Определяем основную причину изменения
        reason = self._determine_change_reason(factors, aspect_changes)
        
        # Добавляем в историю, если произошло значимое изменение
        if change_magnitude > 0.01:
            self._add_to_history(reason, self.rapport, self._get_aspect_values(), change_magnitude)
        
        # Формируем результат для возврата
        new_aspects = self._get_aspect_values()
        
        result = {
            "old_rapport": old_rapport,
            "new_rapport": self.rapport,
            "rapport_change": self.rapport - old_rapport,
            "aspect_changes": {
                aspect: new_aspects[aspect] - old_aspects[aspect]
                for aspect in new_aspects
            },
            "reason": reason,
            "magnitude": change_magnitude
        }
        
        return result
    
    def _analyze_interaction(self, user_text: str, response_text: str) -> Dict[str, float]:
        """
        Анализирует взаимодействие для выявления факторов, влияющих на отношения
        
        Args:
            user_text (str): Сообщение пользователя (в нижнем регистре)
            response_text (str): Ответ персонажа (в нижнем регистре)
            
        Returns:
            Dict[str, float]: Факторы, влияющие на отношения
        """
        factors = {}
        
        # Анализ тональности
        factors["positive_tone"] = 0.0
        factors["negative_tone"] = 0.0
        
        # Позитивные индикаторы
        positive_indicators = [
            "спасибо", "благодарю", "отлично", "прекрасно", "здорово", 
            "великолепно", "удивительно", "интересно", "умный", "гениальный"
        ]
        
        # Негативные индикаторы
        negative_indicators = [
            "глупый", "бесполезный", "плохой", "ужасный", "разочарован", 
            "идиот", "дурак", "злой", "ненавижу", "раздражает"
        ]
        
        # Считаем количество позитивных и негативных индикаторов в обеих частях беседы
        for indicator in positive_indicators:
            if indicator in user_text:
                factors["positive_tone"] += 0.1
            if indicator in response_text:
                factors["positive_tone"] += 0.05
                
        for indicator in negative_indicators:
            if indicator in user_text:
                factors["negative_tone"] += 0.1
            if indicator in response_text:
                factors["negative_tone"] += 0.15  # Негативный ответ персонажа влияет сильнее
        
        # Проверяем наличие вежливости
        factors["politeness"] = 0.0
        politeness_indicators = ["пожалуйста", "будьте добры", "извините", "простите", "с уважением"]
        for indicator in politeness_indicators:
            if indicator in user_text:
                factors["politeness"] += 0.1
        
        # Проверяем наличие интересных вопросов
        factors["intellectual_stimulation"] = 0.0
        intellectual_indicators = [
            "почему", "как вы думаете", "что вы считаете", "ваше мнение",
            "интересный случай", "сложный вопрос", "загадка", "логика"
        ]
        for indicator in intellectual_indicators:
            if indicator in user_text:
                factors["intellectual_stimulation"] += 0.1
        
        # Длина и сложность сообщений
        factors["user_effort"] = min(0.3, len(user_text) / 500)  # Длинные сообщения показывают усилия
        
        # Персональные обращения
        factors["personal_address"] = 0.0
        if re.search(fr'\b{self.character_name}\b', user_text, re.IGNORECASE):
            factors["personal_address"] += 0.1
        
        # Проверка на повторяющиеся вопросы (раздражающий фактор)
        factors["repetitive"] = 0.0
        
        # Флирт (это может быть воспринято по-разному в зависимости от персонажа)
        factors["flirtation"] = 0.0
        flirt_indicators = ["красивый", "симпатичный", "привлекательный", "умный", "сильный"]
        for indicator in flirt_indicators:
            if indicator in user_text and re.search(r'\bвы\b|\bты\b', user_text):
                factors["flirtation"] += 0.1
        
        # Нормализуем факторы
        for key in factors:
            factors[key] = min(1.0, factors[key])
        
        return factors
    
    def _calculate_aspect_changes(self, factors: Dict[str, float]) -> Dict[str, float]:
        """
        Рассчитывает изменения в аспектах отношений на основе выявленных факторов
        
        Args:
            factors (Dict[str, float]): Факторы, влияющие на отношения
            
        Returns:
            Dict[str, float]: Изменения в различных аспектах отношений
        """
        changes = {
            "respect": 0.0,
            "trust": 0.0,
            "liking": 0.0,
            "patience": 0.0
        }
        
        # Уважение увеличивается от интеллектуальной стимуляции и усилий пользователя
        changes["respect"] += factors.get("intellectual_stimulation", 0.0) * 0.05
        changes["respect"] += factors.get("user_effort", 0.0) * 0.03
        
        # Доверие медленно растет со временем и увеличивается от позитивной тональности
        time_factor = min(0.01, (time.time() - self.created_at) / (86400 * 30))  # Максимум 0.01 в месяц
        changes["trust"] += time_factor
        changes["trust"] += factors.get("positive_tone", 0.0) * 0.03
        changes["trust"] -= factors.get("negative_tone", 0.0) * 0.05
        
        # Симпатия зависит от вежливости, позитивной тональности и персональных обращений
        changes["liking"] += factors.get("politeness", 0.0) * 0.04
        changes["liking"] += factors.get("positive_tone", 0.0) * 0.05
        changes["liking"] -= factors.get("negative_tone", 0.0) * 0.06
        changes["liking"] += factors.get("personal_address", 0.0) * 0.02
        
        # Флирт влияет на симпатию в зависимости от персонажа
        flirt_impact = factors.get("flirtation", 0.0) * (2.0 * self.personality_factors.get("openness", 0.5) - 1.0)
        # Для закрытых персонажей флирт может иметь негативное влияние
        changes["liking"] += flirt_impact * 0.03
        
        # Терпение истощается от повторяющихся вопросов и восстанавливается со временем
        changes["patience"] -= factors.get("repetitive", 0.0) * 0.1
        time_since_update = time.time() - self.last_updated
        patience_recovery = min(0.05, time_since_update / 3600)  # До 0.05 в час
        changes["patience"] += patience_recovery
        
        # Применяем факторы личности персонажа
        # Персонажи, ценящие интеллект, сильнее реагируют на интеллектуальную стимуляцию
        intellect_factor = self.personality_factors.get("intellect_appreciation", 0.5)
        changes["respect"] *= 1.0 + intellect_factor
        
        # Персонажи с высокой чувствительностью сильнее реагируют на негативную тональность
        sensitivity_factor = self.personality_factors.get("sensitivity", 0.5)
        if factors.get("negative_tone", 0.0) > 0:
            for aspect in changes:
                changes[aspect] -= factors.get("negative_tone", 0.0) * 0.02 * sensitivity_factor
        
        # Персонажи, высоко ценящие формальность, сильнее реагируют на вежливость
        formality_factor = self.personality_factors.get("formality_preference", 0.5)
        changes["respect"] += factors.get("politeness", 0.0) * 0.03 * formality_factor
        
        # Масштабируем изменения, чтобы они были небольшими за одно взаимодействие
        for aspect in changes:
            changes[aspect] = max(-0.1, min(0.1, changes[aspect]))
        
        return changes
    
    def _determine_change_reason(self, factors: Dict[str, float], 
                                aspect_changes: Dict[str, float]) -> str:
        """
        Определяет основную причину изменения отношений
        
        Args:
            factors (Dict[str, float]): Факторы, влияющие на отношения
            aspect_changes (Dict[str, float]): Изменения в аспектах отношений
            
        Returns:
            str: Основная причина изменения
        """
        # Определяем наиболее значимый фактор
        significant_factor = max(factors.items(), key=lambda x: abs(x[1]))
        
        # Определяем аспект с наибольшим изменением
        significant_aspect = max(aspect_changes.items(), key=lambda x: abs(x[1]))
        
        # Формируем причину изменения
        if abs(significant_aspect[1]) < 0.01:
            return "Незначительное взаимодействие"
        
        direction = "увеличение" if significant_aspect[1] > 0 else "уменьшение"
        
        aspect_names = {
            "respect": "уважения",
            "trust": "доверия",
            "liking": "симпатии",
            "patience": "терпения"
        }
        
        factor_descriptions = {
            "positive_tone": "позитивный тон разговора",
            "negative_tone": "негативный тон разговора",
            "politeness": "проявленная вежливость",
            "intellectual_stimulation": "интеллектуальная стимуляция",
            "user_effort": "усилия в общении",
            "personal_address": "личное обращение",
            "repetitive": "повторяющиеся вопросы",
            "flirtation": "элементы флирта"
        }
        
        aspect_name = aspect_names.get(significant_aspect[0], significant_aspect[0])
        factor_desc = factor_descriptions.get(significant_factor[0], significant_factor[0])
        
        return f"{direction} {aspect_name} из-за фактора: {factor_desc}"
    
    def get_status_description(self) -> Dict[str, Any]:
        """
        Возвращает описание текущего статуса отношений в человекочитаемом формате
        
        Returns:
            Dict[str, Any]: Описание статуса отношений
        """
        # Определяем общий уровень отношений
        if self.rapport > 0.8:
            rapport_desc = "превосходные"
        elif self.rapport > 0.6:
            rapport_desc = "очень хорошие"
        elif self.rapport > 0.3:
            rapport_desc = "хорошие"
        elif self.rapport > 0.1:
            rapport_desc = "положительные"
        elif self.rapport > -0.1:
            rapport_desc = "нейтральные"
        elif self.rapport > -0.3:
            rapport_desc = "напряженные"
        elif self.rapport > -0.6:
            rapport_desc = "плохие"
        elif self.rapport > -0.8:
            rapport_desc = "очень плохие"
        else:
            rapport_desc = "враждебные"
        
        # Определяем описания аспектов
        aspect_descriptions = {}
        aspect_values = self._get_aspect_values()
        
        for aspect_name, aspect in self.aspects.items():
            aspect_descriptions[aspect_name] = aspect.get_description()
        
        # Получаем последнее изменение
        last_change = self.history[-1] if self.history else None
        last_change_desc = None
        if last_change and last_change["change_magnitude"] > 0.01:
            last_change_desc = {
                "when": last_change["datetime"],
                "reason": last_change["reason"],
                "magnitude": last_change["change_magnitude"]
            }
        
        return {
            "overall": rapport_desc,
            "rapport_value": self.rapport,
            "aspects": aspect_descriptions,
            "aspect_values": aspect_values,
            "last_change": last_change_desc
        }
    
    def get_relationship_summary_for_prompt(self) -> str:
        """
        Возвращает краткое описание отношений для включения в промпт
        
        Returns:
            str: Описание отношений для промпта
        """
        status = self.get_status_description()
        
        summary = f"ТВОЕ ОТНОШЕНИЕ К СОБЕСЕДНИКУ: {status['overall']} (уровень: {self.rapport:.2f})\n\n"
        
        summary += "Аспекты отношений:\n"
        for aspect_name, desc in status['aspects'].items():
            aspect_name_rus = {
                "respect": "Уважение",
                "trust": "Доверие",
                "liking": "Симпатия",
                "patience": "Терпение"
            }.get(aspect_name, aspect_name.capitalize())
            
            value = status['aspect_values'][aspect_name]
            summary += f"- {aspect_name_rus}: {desc} ({value:.2f})\n"
        
        if status['last_change']:
            summary += f"\nПоследнее изменение: {status['last_change']['reason']}\n"
        
        return summary
    
    def update_aspect(self, aspect_name: str, change: float) -> bool:
        """
        Вручную изменяет указанный аспект отношений
        
        Args:
            aspect_name (str): Название аспекта ('rapport', 'respect', 'trust', 'liking', 'patience')
            change (float): Величина изменения (-1.0 до 1.0)
            
        Returns:
            bool: True если обновление успешно, False в противном случае
        """
        if aspect_name == 'rapport':
            old_value = self.rapport
            self.rapport = max(-1.0, min(1.0, old_value + change))
            
            # Добавляем в историю
            self._add_to_history(
                "Ручное изменение общего отношения", 
                self.rapport, 
                self._get_aspect_values(),
                abs(change)
            )
            return True
        elif aspect_name in self.aspects:
            # Обновляем аспект
            actual_change = self.aspects[aspect_name].update(change)
            
            # Обновляем общее отношение
            weighted_sum = sum(aspect.value * aspect.weight for aspect in self.aspects.values())
            total_weight = sum(aspect.weight for aspect in self.aspects.values())
            self.rapport = max(-1.0, min(1.0, weighted_sum / total_weight))
            
            # Добавляем в историю
            self._add_to_history(
                f"Ручное изменение аспекта {aspect_name}", 
                self.rapport, 
                self._get_aspect_values(),
                abs(actual_change)
            )
            return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует объект отношений в словарь для сериализации
        
        Returns:
            Dict[str, Any]: Словарь с данными отношений
        """
        return {
            "character_name": self.character_name,
            "rapport": self.rapport,
            "aspects": {name: aspect.to_dict() for name, aspect in self.aspects.items()},
            "personality_factors": self.personality_factors,
            "history": self.history,
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relationship':
        """
        Создает объект отношений из словаря
        
        Args:
            data (Dict[str, Any]): Данные отношений
            
        Returns:
            Relationship: Объект отношений
        """
        relationship = cls(
            character_name=data.get("character_name", "Unknown"),
            initial_rapport=data.get("rapport", 0.0),
            personality_factors=data.get("personality_factors", {})
        )
        
        # Загружаем аспекты
        if "aspects" in data:
            for name, aspect_data in data["aspects"].items():
                if isinstance(aspect_data, dict):
                    relationship.aspects[name] = RelationshipAspect.from_dict(aspect_data)
                else:
                    # Обратная совместимость со старым форматом
                    relationship.aspects[name] = RelationshipAspect(name, aspect_data)
        
        relationship.history = data.get("history", [])
        relationship.created_at = data.get("created_at", time.time())
        relationship.last_updated = data.get("last_updated", time.time())
        
        return relationship