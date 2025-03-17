# relationship.py

"""
Модуль для управления отношениями персонажа к пользователю.
Отслеживает и изменяет различные аспекты отношений на основе взаимодействий.
"""

import time
import json
import re
from datetime import datetime

class Relationship:
    """
    Класс для отслеживания отношений персонажа к пользователю
    """
    
    def __init__(self, character_name, initial_rapport=0.0, 
                 initial_aspects=None, personality_factors=None):
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
        
        # Аспекты отношений
        self.aspects = initial_aspects or {
            "respect": 0.0,    # уважение
            "trust": 0.0,      # доверие
            "liking": 0.0,     # симпатия
            "patience": 0.0    # терпение
        }
        
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
        
        # Временная метка создания
        self.created_at = time.time()
        self.last_updated = time.time()
        
        # Сохраняем начальное состояние в историю
        self._add_to_history("Начальное состояние", 
                            self.rapport, 
                            self.aspects.copy(), 
                            0.0)
    
    def _add_to_history(self, reason, rapport, aspects, change_magnitude):
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
    
    def update_from_interaction(self, user_message, character_response):
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
        full_interaction = f"{user_text} {response_text}"
        
        # Анализ текста для выявления факторов, влияющих на отношения
        factors = self._analyze_interaction(user_text, response_text)
        
        # Рассчитываем изменения в аспектах отношений
        aspect_changes = self._calculate_aspect_changes(factors)
        
        # Применяем изменения
        old_rapport = self.rapport
        old_aspects = self.aspects.copy()
        
        # Обновляем аспекты
        for aspect, change in aspect_changes.items():
            if aspect in self.aspects:
                self.aspects[aspect] = max(-1.0, min(1.0, self.aspects[aspect] + change))
        
        # Рассчитываем новый общий уровень отношений как взвешенное среднее аспектов
        weights = {
            "respect": 0.3,
            "trust": 0.3,
            "liking": 0.25,
            "patience": 0.15
        }
        
        weighted_sum = sum(self.aspects[aspect] * weights.get(aspect, 0.25) 
                          for aspect in self.aspects)
        total_weight = sum(weights.get(aspect, 0.25) for aspect in self.aspects)
        
        self.rapport = max(-1.0, min(1.0, weighted_sum / total_weight))
        
        # Вычисляем общую величину изменения
        aspect_change_magnitude = sum(abs(change) for change in aspect_changes.values())
        rapport_change = abs(self.rapport - old_rapport)
        change_magnitude = (aspect_change_magnitude + rapport_change) / 2
        
        # Определяем основную причину изменения
        reason = self._determine_change_reason(factors, aspect_changes)
        
        # Добавляем в историю, если произошло значимое изменение
        if change_magnitude > 0.01:
            self._add_to_history(reason, self.rapport, self.aspects, change_magnitude)
        
        # Формируем результат для возврата
        result = {
            "old_rapport": old_rapport,
            "new_rapport": self.rapport,
            "rapport_change": self.rapport - old_rapport,
            "aspect_changes": {
                aspect: self.aspects[aspect] - old_aspects.get(aspect, 0.0)
                for aspect in self.aspects
            },
            "reason": reason,
            "magnitude": change_magnitude
        }
        
        return result
    
    def _analyze_interaction(self, user_text, response_text):
        """
        Анализирует взаимодействие для выявления факторов, влияющих на отношения
        
        Args:
            user_text (str): Сообщение пользователя (в нижнем регистре)
            response_text (str): Ответ персонажа (в нижнем регистре)
            
        Returns:
            dict: Факторы, влияющие на отношения
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
        
        # Проверяем наличие интересных вопросов (для интеллектуальных персонажей)
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
    
    def _calculate_aspect_changes(self, factors):
        """
        Рассчитывает изменения в аспектах отношений на основе выявленных факторов
        
        Args:
            factors (dict): Факторы, влияющие на отношения
            
        Returns:
            dict: Изменения в различных аспектах отношений
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
    
    def _determine_change_reason(self, factors, aspect_changes):
        """
        Определяет основную причину изменения отношений
        
        Args:
            factors (dict): Факторы, влияющие на отношения
            aspect_changes (dict): Изменения в аспектах отношений
            
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
    
    def get_status_description(self):
        """
        Возвращает описание текущего статуса отношений в человекочитаемом формате
        
        Returns:
            dict: Описание статуса отношений
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
        for aspect, value in self.aspects.items():
            if aspect == "respect":
                if value > 0.7:
                    aspect_descriptions[aspect] = "высокое уважение"
                elif value > 0.3:
                    aspect_descriptions[aspect] = "уважение"
                elif value > -0.3:
                    aspect_descriptions[aspect] = "нейтральное отношение"
                elif value > -0.7:
                    aspect_descriptions[aspect] = "неуважение"
                else:
                    aspect_descriptions[aspect] = "презрение"
            
            elif aspect == "trust":
                if value > 0.7:
                    aspect_descriptions[aspect] = "полное доверие"
                elif value > 0.3:
                    aspect_descriptions[aspect] = "доверие"
                elif value > -0.3:
                    aspect_descriptions[aspect] = "осторожность"
                elif value > -0.7:
                    aspect_descriptions[aspect] = "недоверие"
                else:
                    aspect_descriptions[aspect] = "полное недоверие"
            
            elif aspect == "liking":
                if value > 0.7:
                    aspect_descriptions[aspect] = "сильная симпатия"
                elif value > 0.3:
                    aspect_descriptions[aspect] = "симпатия"
                elif value > -0.3:
                    aspect_descriptions[aspect] = "нейтральное отношение"
                elif value > -0.7:
                    aspect_descriptions[aspect] = "неприязнь"
                else:
                    aspect_descriptions[aspect] = "сильная неприязнь"
            
            elif aspect == "patience":
                if value > 0.7:
                    aspect_descriptions[aspect] = "исключительное терпение"
                elif value > 0.3:
                    aspect_descriptions[aspect] = "терпение"
                elif value > -0.3:
                    aspect_descriptions[aspect] = "умеренное терпение"
                elif value > -0.7:
                    aspect_descriptions[aspect] = "нетерпение"
                else:
                    aspect_descriptions[aspect] = "полное нетерпение"
        
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
            "aspect_values": self.aspects,
            "last_change": last_change_desc
        }
    
    def get_relationship_summary_for_prompt(self):
        """
        Возвращает краткое описание отношений для включения в промпт
        
        Returns:
            str: Описание отношений для промпта
        """
        status = self.get_status_description()
        
        summary = f"ТВОЕ ОТНОШЕНИЕ К СОБЕСЕДНИКУ: {status['overall']} (уровень: {status['rapport_value']:.2f})\n\n"
        
        summary += "Аспекты отношений:\n"
        for aspect, desc in status['aspects'].items():
            aspect_name = aspect.capitalize()
            if aspect == "respect":
                aspect_name = "Уважение"
            elif aspect == "trust":
                aspect_name = "Доверие"
            elif aspect == "liking":
                aspect_name = "Симпатия"
            elif aspect == "patience":
                aspect_name = "Терпение"
            
            value = status['aspect_values'][aspect]
            summary += f"- {aspect_name}: {desc} ({value:.2f})\n"
        
        if status['last_change']:
            summary += f"\nПоследнее изменение: {status['last_change']['reason']}\n"
        
        return summary
    
    def to_dict(self):
        """
        Преобразует объект отношений в словарь для сериализации
        
        Returns:
            dict: Словарь с данными отношений
        """
        return {
            "character_name": self.character_name,
            "rapport": self.rapport,
            "aspects": self.aspects,
            "personality_factors": self.personality_factors,
            "history": self.history,
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Создает объект отношений из словаря
        
        Args:
            data (dict): Данные отношений
            
        Returns:
            Relationship: Объект отношений
        """
        relationship = cls(
            character_name=data["character_name"],
            initial_rapport=data["rapport"],
            initial_aspects=data["aspects"],
            personality_factors=data["personality_factors"]
        )
        
        relationship.history = data["history"]
        relationship.created_at = data["created_at"]
        relationship.last_updated = data["last_updated"]
        
        return relationship