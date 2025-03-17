from sentence_transformers import SentenceTransformer

# Загрузка модели (одной из лучших на текущий момент)
model = SentenceTransformer('all-MiniLM-L6-v2')  # Легкая и быстрая модель
# Или используйте более мощную: model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Создание эмбеддингов для предложений
sentences = [
    "Как работает искусственный интеллект?",
    "Принципы работы нейронных сетей",
    "Рецепт приготовления борща",
    "Методы машинного обучения в NLP"
]

# Получение эмбеддингов
embeddings = model.encode(sentences)
print(f"Форма эмбеддингов: {embeddings.shape}")  # Например: (4, 384)