# convert_characters.py

"""
Скрипт для конвертации существующих персонажей из Python кода в JSON файлы.
"""

import os
import sys
import logging

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("conversion.log")
    ]
)

# Импортируем модули после настройки логирования
try:
    # Сначала импортируем существующие персонажи
    from characters import CHARACTERS, list_characters
    
    # Затем наш загрузчик для конвертации
    from characters_loader import convert_existing_characters_to_json
except ImportError as e:
    logging.error(f"Ошибка импорта: {e}")
    sys.exit(1)

def main():
    """
    Основная функция для конвертации персонажей
    """
    try:
        # Выводим список имеющихся персонажей
        existing_characters = list_characters()
        logging.info(f"Найдено {len(existing_characters)} существующих персонажей:")
        for name, desc in existing_characters:
            logging.info(f"- {name}: {desc}")
        
        # Запрашиваем директорию для сохранения (по умолчанию "characters")
        output_dir = input("Введите директорию для сохранения JSON-файлов [characters]: ").strip()
        if not output_dir:
            output_dir = "characters"
        
        # Выполняем конвертацию
        logging.info(f"Начинаем конвертацию персонажей в директорию {output_dir}...")
        convert_existing_characters_to_json(output_dir)
        
        # Сообщаем о завершении
        logging.info("Конвертация завершена успешно!")
        
    except Exception as e:
        logging.error(f"Произошла ошибка при конвертации: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())