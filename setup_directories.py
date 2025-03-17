# setup_directories.py

import os

def setup_directories():
    """
    Создание необходимых директорий для хранения состояний персонажей
    """
    # Директория для хранения состояний персонажей
    os.makedirs("character_states", exist_ok=True)
    print("Директория для хранения состояний персонажей создана: character_states/")
    
    # Перечень персонажей для создания поддиректорий (опционально)
    from characters import list_characters
    
    characters = list_characters()
    for name, _ in characters:
        # Формируем безопасное имя файла
        safe_name = "".join(c if c.isalnum() else "_" for c in name)
        char_dir = os.path.join("character_states", safe_name)
        os.makedirs(char_dir, exist_ok=True)
        print(f"Создана директория для персонажа '{name}': {char_dir}")

if __name__ == "__main__":
    setup_directories()
    print("\nВсе необходимые директории успешно созданы!")
    print("Теперь вы можете запустить персонажный агент командой:")
    print("python main.py [--character ИМЯ_ПЕРСОНАЖА] [другие параметры]")
    print("\nДля получения справки по доступным параметрам используйте:")
    print("python main.py --help")
    print("\nДля просмотра списка доступных персонажей используйте:")
    print("python main.py --list")