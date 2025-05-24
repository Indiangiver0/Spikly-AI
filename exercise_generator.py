import json
import os
from typing import List, Dict, Any

class ExerciseGenerator:
    def __init__(self, dialog_manager):
        self.dialog_manager = dialog_manager

    def _get_recent_dialog_errors(self) -> List[Dict]:
        """Получает недавние ошибки пользователя из логов."""
        # Используем файл ошибок из dialog_manager
        errors_file = f"{self.dialog_manager.logs_dir}/errors.json"

        all_errors = []
        try:
            with open(errors_file, 'r', encoding='utf-8') as f:
                all_errors = json.load(f)
        except FileNotFoundError:
            print(f"Файл ошибок {errors_file} не найден.")
            return []
        except json.JSONDecodeError:
            print(f"Ошибка декодирования JSON в файле {errors_file}.")
            return []
        
        # Фильтруем ошибки, которые подходят для генерации упражнений
        relevant_errors = []
        for error in all_errors:
            is_dialog_summary = error.get("type") == "dialog_error_summary"
            has_detailed_context = error.get("context") and isinstance(error["context"], dict) and \
                                   (error["context"].get("user_message") and \
                                    (error["context"].get("corrections") or error["context"].get("explanation") or error["context"].get("detected_keywords")))
            
            if is_dialog_summary or has_detailed_context:
                relevant_errors.append(error)
        
        # Возвращаем последние 5 релевантных ошибок
        return relevant_errors[-5:] 

    def _get_recent_dialogs_content(self) -> List[Dict]:
        """Получает содержимое недавних диалогов."""
        # Заглушка. Реальная функция будет читать сохраненные диалоги.
        # Можно использовать существующие методы DialogManager для получения путей к файлам диалогов.
        dialog_files_info = []
        dialog_dir = self.dialog_manager.logs_dir if self.dialog_manager.logs_dir else "dialog_logs"
        try:
            for filename in sorted(os.listdir(dialog_dir), reverse=True):
                if filename.startswith("dialog_") and filename.endswith(".json"):
                    filepath = os.path.join(dialog_dir, filename)
                    dialog_files_info.append(filepath)
                    if len(dialog_files_info) >= 3: # Берем последние 3 диалога
                        break
        except FileNotFoundError:
            print(f"Директория логов диалогов {dialog_dir} не найдена.")
            return []

        dialogs_content = []
        for filepath in dialog_files_info:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    dialogs_content.append(json.load(f))
            except Exception as e:
                print(f"Ошибка чтения файла диалога {filepath}: {e}")
        return dialogs_content

    def generate_exercises(self, num_exercises: int = 3) -> List[Dict[str, Any]]:
        """Генерирует список упражнений на основе ошибок и диалогов."""
        print("Генерация упражнений на основе ошибок и диалогов...")
        user_errors = self._get_recent_dialog_errors()

        exercises = []

        if not user_errors:
            exercises.append({
                "type": "info",
                "question": "Не найдено достаточно ошибок для генерации персонализированных упражнений. Пожалуйста, пройдите несколько диалогов.",
                "answer": "-"
            })
            return exercises

        for i, error_entry in enumerate(user_errors):
            if len(exercises) >= num_exercises:
                break

            exercise = None
            if error_entry.get("type") == "dialog_error_summary":
                # Упражнение на основе тем из dialog_error_summary
                themes_str = error_entry.get("message", "").split("ТЕМЫ_ДЛЯ_ЗАДАНИЙ:")[-1].split("РЕКОМЕНДАЦИИ:")[0].strip()
                if themes_str and themes_str != "Н/Д":
                    first_theme = themes_str.split('\n')[0].strip()
                    if first_theme:
                        exercise = {
                            "type": "topic_review",
                            "question": f"Давайте повторим тему: '{first_theme}'. Можете привести пример предложения с этой конструкцией или на эту тему?",
                            "answer_format": "open_ended_text",
                            "related_error": error_entry
                        }
            elif error_entry.get("context") and error_entry["context"].get("user_message") and error_entry["context"].get("corrections"):
                # Упражнение на исправление ошибки
                context = error_entry["context"]
                exercise = {
                    "type": "correction",
                    "question": f"Вы написали: '{context['user_message']}'. Как можно это исправить или улучшить?",
                    "hint": f"Исправленный вариант мог бы быть: '{context['corrections']}'",
                    "explanation": context.get("explanation", "Попробуйте исправить ошибку."),
                    "answer_format": "text_input",
                    "correct_answer": context["corrections"],
                    "related_error": error_entry
                }
            elif error_entry.get("type") == "aggressive_language":
                 context = error_entry.get("context", {})
                 exercise = {
                    "type": "reflection",
                    "question": f"В одном из диалогов вы использовали фразу: '{context.get('user_message', '...')}'. Это было воспринято как агрессивное. Почему такое общение может быть неэффективным?",
                    "answer_format": "open_ended_text",
                    "related_error": error_entry
                 }

            if exercise:
                exercises.append(exercise)
        
        if not exercises:
             exercises.append({
                "type": "info",
                "question": "Не удалось сгенерировать упражнения на основе последних ошибок. Возможно, они были недостаточно детализированы.",
                "answer": "-"
            })

        return exercises[:num_exercises]

    def check_exercise_answer(self, exercise: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
        """Проверяет ответ пользователя на упражнение."""
        print(f"Проверка ответа '{user_answer}' для упражнения: {exercise.get('question')}")
        is_correct = False
        feedback = "Пока не могу проверить этот тип ответа, но спасибо за попытку!"

        if exercise.get("type") == "correction":
            # Простое сравнение для примера
            if user_answer.strip().lower() == exercise.get("correct_answer", "").strip().lower():
                is_correct = True
                feedback = "Отлично, это правильный ответ!"
            else:
                is_correct = False
                feedback = f"Не совсем. Правильный ответ: '{exercise.get('correct_answer', '')}'. {exercise.get('explanation', '')}"
        elif exercise.get("type") in ["topic_review", "reflection"]:
            # Для открытых вопросов любой ответ приемлем
            is_correct = True
            feedback = "Спасибо за ваш развернутый ответ! Важно размышлять над этими темами."
            
        return {"is_correct": is_correct, "feedback": feedback}

# Пример использования:
if __name__ == '__main__':
    import os
    # Для теста нужно создать DialogManager и, возможно, фейковые логи
    class MockDialogManager:
        def __init__(self):
            self.logs_dir = "dialog_logs_test"
            self.errors_file = os.path.join(self.logs_dir, "errors.json")
            os.makedirs(self.logs_dir, exist_ok=True)
            # Создадим фейковый errors.json для теста
            test_errors = [
                {
                    "timestamp": "2023-10-27T10:00:00", "type": "grammar_mistake", "message": "User said I has a book",
                    "context": {"user_message": "I has a book", "corrections": "I have a book", "explanation": "Use 'have' with I."}
                },
                {
                    "timestamp": "2023-10-27T11:00:00", "type": "dialog_error_summary", 
                    "message": "ОБЩИЕ_ОШИБКИ: Несколько ошибок с артиклями.\nКОНКРЕТНЫЕ_ОШИБКИ: ...\nРЕКОМЕНДАЦИИ: Повторить использование артиклей a/an/the.\nТЕМЫ_ДЛЯ_ЗАДАНИЙ: Использование неопределенного артикля\nИспользование определенного артикля the"
                },
                {
                    "timestamp": "2023-10-27T12:00:00", "type": "aggressive_language", 
                    "message": "User used aggressive language: дурак",
                    "context": {"user_message": "ты дурак", "detected_keywords": ["дурак"], "ai_reaction": "Please be respectful."}
                }
            ]
            with open(self.errors_file, 'w', encoding='utf-8') as f:
                json.dump(test_errors, f, ensure_ascii=False, indent=2)

    mock_dm = MockDialogManager()
    generator = ExerciseGenerator(dialog_manager=mock_dm)
    
    print("\n--- Получение ошибок (тест) ---")
    retrieved_errors = generator._get_recent_dialog_errors()
    print(f"Получено {len(retrieved_errors)} ошибок для генерации:")
    for err in retrieved_errors:
        print(f"  Тип: {err.get('type')}, Сообщение/Контекст: {err.get('message', err.get('context'))}")

    print("\n--- Генерация упражнений (тест) ---")
    exercises = generator.generate_exercises(num_exercises=5)
    for i, ex in enumerate(exercises):
        print(f"Упражнение {i+1}: ({ex.get('type')}) {ex.get('question')}")
        if ex.get('hint'): print(f"  Подсказка: {ex.get('hint')}")
        if ex.get('correct_answer'): print(f"  Ожидаемый ответ: {ex.get('correct_answer')}")

    print("\n--- Проверка ответа (тест) ---")
    if exercises and exercises[0].get("type") not in ["info", "topic_review", "reflection"] :
        if exercises[0].get("correct_answer"):
            test_answer = exercises[0]["correct_answer"] # Используем правильный ответ для теста
            result = generator.check_exercise_answer(exercises[0], test_answer)
            print(f"Результат проверки для '{test_answer}': {result}")
            
            test_answer_wrong = "I did went there."
            result_wrong = generator.check_exercise_answer(exercises[0], test_answer_wrong)
            print(f"Результат проверки для '{test_answer_wrong}': {result_wrong}")
    elif exercises and exercises[0].get("type") == "topic_review":
        result = generator.check_exercise_answer(exercises[0], "A cat sat on the mat.")
        print(f"Результат проверки для открытого ответа: {result}")
        
    # Удаление тестовой директории
    # import shutil
    # shutil.rmtree(mock_dm.logs_dir) 