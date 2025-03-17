# setup_directories.py

import os
import logging

logger = logging.getLogger(__name__)

def setup_directories():
    """
    Создание необходимых директорий для хранения состояний персонажей
    """
    # Директория для хранения состояний персонажей
    os.makedirs("character_states", exist_ok=True)
    logger.info("Директория для хранения состояний персонажей создана: character_states/")
    
    # Перечень персонажей для создания поддиректорий (опционально)
    try:
        from characters import list_characters
        
        characters = list_characters()
        for name, _ in characters:
            # Формируем безопасное имя файла
            safe_name = "".join(c if c.isalnum() else "_" for c in name)
            char_dir = os.path.join("character_states", safe_name)
            os.makedirs(char_dir, exist_ok=True)
            logger.info(f"Создана директория для персонажа '{name}': {char_dir}")
    except ImportError:
        logger.warning("Не удалось импортировать модуль персонажей")
    except Exception as e:
        logger.error(f"Ошибка при создании директорий персонажей: {str(e)}")

if __name__ == "__main__":
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    setup_directories()
    print("\nВсе необходимые директории успешно созданы!")
    print("Теперь вы можете запустить персонажного агента командой:")
    print("python main.py [--character ИМЯ_ПЕРСОНАЖА] [другие параметры]")
    print("\nДля получения справки по доступным параметрам используйте:")
    print("python main.py --help")
    print("\nДля просмотра списка доступных персонажей используйте:")
    print("python main.py --list")