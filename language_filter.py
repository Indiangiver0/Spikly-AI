class LanguageFilter:
    def __init__(self):
        # В будущем здесь можно будет загрузить словари или модели
        self.aggressive_keywords = [
            # Примеры ключевых слов (нужно будет расширить и улучшить)
            "дурак", "идиот", "тупой", "черт", "блин", 
            "сволочь", "урод", "дебил", 
            # ... и другие обсценные выражения и оскорбления
            # Важно: этот список должен быть тщательно подобран
            # и учитывать контекст, чтобы избежать ложных срабатываний.
        ]

    def is_aggressive(self, text: str) -> bool:
        """
        Проверяет текст на наличие агрессивных ключевых слов.
        Возвращает True, если найдено агрессивное слово, иначе False.
        """
        if not text:
            return False
        
        text_lower = text.lower()
        for keyword in self.aggressive_keywords:
            if keyword in text_lower:
                return True
        return False

    def get_detected_keywords(self, text: str) -> list[str]:
        """
        Возвращает список обнаруженных агрессивных ключевых слов.
        """
        if not text:
            return []
            
        text_lower = text.lower()
        detected = []
        for keyword in self.aggressive_keywords:
            if keyword in text_lower:
                detected.append(keyword)
        return detected

# Пример использования (для тестирования):
if __name__ == '__main__':
    filter = LanguageFilter()
    
    test_phrases = [
        "Это нормально.",
        "Ты дурак какой-то.",
        "Ну что за черт!",
        "Я очень зол, блин.",
        "Все хорошо."
    ]
    
    for phrase in test_phrases:
        is_agg = filter.is_aggressive(phrase)
        detected_words = filter.get_detected_keywords(phrase)
        print(f"Фраза: '{phrase}' -> Агрессивно: {is_agg}, Обнаружено: {detected_words}") 