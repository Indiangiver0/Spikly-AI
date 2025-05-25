import json
import os
import asyncio
import random
from datetime import datetime
from typing import Dict, List, Any, Tuple
from openai import OpenAI
from config import OPENAI_API_KEY

class ErrorAnalysisAndPracticeSystem:
    def __init__(self, dialog_manager):
        self.dialog_manager = dialog_manager
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.exercise_types = [
            "word_replacement",      # Замени слово
            "translation_en_ru",     # Переведи с английского на русский
            "translation_ru_en",     # Переведи с русского на английский  
            "simple_sentences",      # Составить 5 простых предложений
            "text_composition"       # Написать текст с 2 использованиями слова
        ]
    
    async def run_full_error_analysis_and_practice(self):
        """
        Основная функция для полного анализа ошибок и создания упражнений
        """
        print("🔍 Запуск анализа ошибок и создания упражнений...")
        
        # 1. Анализ последних 3 диалогов на ошибки
        dialog_errors = await self.analyze_recent_dialogs_for_errors()
        
        # 2. Получение переводов которые запрашивал пользователь
        translation_requests = self.get_user_translation_requests()
        
        # 3. Загрузка существующих ошибок из профиля
        existing_errors = self.load_user_error_profile()
        
        # 4. Объединение всех данных и создание упражнений
        practice_session = await self.create_practice_session(
            dialog_errors, translation_requests, existing_errors
        )
        
        return practice_session
    
    async def analyze_recent_dialogs_for_errors(self) -> List[Dict]:
        """
        Анализирует последние 3 диалога на наличие ошибок пользователя
        """
        # Получаем последние 3 диалога
        recent_dialogs = self.dialog_manager.get_recent_dialogs(limit=3)
        all_errors = []
        
        for dialog in recent_dialogs:
            dialog_id = dialog.get("dialog_id", "unknown")
            scenario = dialog.get("scenario", "unknown")
            messages = dialog.get("messages", [])
            
            # Извлекаем только сообщения пользователя
            user_messages = [msg["content"] for msg in messages if msg["role"] == "user"]
            
            if user_messages:
                print(f"📊 Анализируем диалог {dialog_id[:8]}... ({len(user_messages)} сообщений пользователя)")
                
                # Отправляем все сообщения пользователя на анализ к OpenAI
                dialog_errors = await self.analyze_user_messages_for_errors(
                    user_messages, dialog_id, scenario
                )
                all_errors.extend(dialog_errors)
        
        return all_errors
    
    async def analyze_user_messages_for_errors(self, user_messages: List[str], dialog_id: str, scenario: str) -> List[Dict]:
        """
        Анализирует сообщения пользователя на ошибки с помощью OpenAI
        """
        messages_text = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(user_messages)])
        
        analysis_prompt = f"""
        Проанализируй следующие сообщения пользователя на английском языке на наличие ВСЕХ типов ошибок:
        
        Сценарий диалога: {scenario}
        Сообщения пользователя:
        {messages_text}
        
        Найди и классифицируй ВСЕ ошибки:
        1. Грамматические ошибки (времена, артикли, предлоги, порядок слов, согласование)
        2. Лексические ошибки (неправильный выбор слов, коллокации)
        3. Стилистические ошибки (неподходящий стиль для контекста)
        4. Орфографические ошибки (неправильное написание)
        5. Использование русских слов вместо английских
        6. Ненормативная лексика или оскорбления
        7. Неподходящий уровень формальности для ситуации
        
        Ответ должен быть в формате JSON:
        {{
            "errors": [
                {{
                    "original_phrase": "точная фраза с ошибкой",
                    "error_type": "тип ошибки",
                    "explanation": "объяснение ошибки на русском языке",
                    "correction": "правильный вариант на английском",
                    "severity": "low/medium/high",
                    "context": "в каком контексте была ошибка"
                }}
            ]
        }}
        
        Если ошибок нет, верни: {{"errors": []}}
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ты эксперт по анализу ошибок в английском языке. Отвечай ТОЛЬКО в формате JSON."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            analysis_result = json.loads(response.choices[0].message.content)
            errors = analysis_result.get("errors", [])
            
            # Добавляем метаданные к каждой ошибке
            for error in errors:
                error["dialog_id"] = dialog_id
                error["scenario"] = scenario
                error["timestamp"] = datetime.now().isoformat()
            
            print(f"✅ Найдено {len(errors)} ошибок в диалоге")
            return errors
            
        except Exception as e:
            print(f"❌ Ошибка анализа диалога {dialog_id}: {e}")
            return []
    
    def get_user_translation_requests(self) -> List[Dict]:
        """
        Получает переводы, которые запрашивал пользователь
        """
        help_requests_file = os.path.join(self.dialog_manager.logs_dir, "help_requests.json")
        translation_requests = []
        
        if os.path.exists(help_requests_file):
            try:
                with open(help_requests_file, 'r', encoding='utf-8') as f:
                    help_requests = json.load(f)
                
                # Фильтруем только переводы
                for request in help_requests:
                    if request.get("request_type") == "translation" or "перевод" in request.get("user_input", "").lower():
                        # Извлекаем переведенные слова/фразы из ответа AI
                        ai_response = request.get("ai_response", "")
                        translation_requests.append({
                            "original_text": self.extract_original_from_translation(ai_response),
                            "translation": self.extract_translation_from_response(ai_response),
                            "dialog_id": request.get("dialog_id", ""),
                            "timestamp": request.get("timestamp", "")
                        })
                        
            except Exception as e:
                print(f"❌ Ошибка загрузки запросов переводов: {e}")
        
        print(f"📚 Найдено {len(translation_requests)} запросов переводов")
        return translation_requests
    
    def extract_original_from_translation(self, ai_response: str) -> str:
        """Извлекает оригинальный текст из ответа AI с переводом"""
        # Простая эвристика - ищем текст после "ПЕРЕВОД:" до перевода
        lines = ai_response.split('\n')
        for line in lines:
            if 'ПЕРЕВОД:' in line:
                return line.replace('ПЕРЕВОД:', '').strip()
        return ""
    
    def extract_translation_from_response(self, ai_response: str) -> str:
        """Извлекает перевод из ответа AI"""
        lines = ai_response.split('\n')
        for i, line in enumerate(lines):
            if 'ПЕРЕВОД:' in line and i + 1 < len(lines):
                return lines[i + 1].strip()
        return ""
    
    def load_user_error_profile(self) -> Dict:
        """
        Загружает профиль ошибок пользователя
        """
        error_profile_file = os.path.join(self.dialog_manager.logs_dir, "user_error_profile.json")
        
        if os.path.exists(error_profile_file):
            try:
                with open(error_profile_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ Ошибка загрузки профиля ошибок: {e}")
        
        return {}
    
    async def create_practice_session(self, dialog_errors: List[Dict], translation_requests: List[Dict], existing_errors: Dict) -> Dict:
        """
        Создает сессию упражнений на основе всех данных
        """
        # Обновляем профиль ошибок новыми найденными ошибками
        updated_profile = await self.update_error_profile(dialog_errors, existing_errors)
        
        # Выбираем максимум 5 ошибок для отработки
        errors_to_practice = self.select_errors_for_practice(updated_profile, max_errors=5)
        
        # Создаем упражнения для каждой ошибки (по 3 упражнения на ошибку)
        practice_exercises = []
        
        for error_key, error_data in errors_to_practice.items():
            exercises = await self.generate_exercises_for_error(error_data, translation_requests)
            practice_exercises.extend(exercises)
        
        practice_session = {
            "session_id": f"practice_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "total_errors_analyzed": len(dialog_errors),
            "errors_for_practice": len(errors_to_practice),
            "total_exercises": len(practice_exercises),
            "exercises": practice_exercises,
            "error_profile_snapshot": errors_to_practice
        }
        
        # Сохраняем сессию упражнений
        self.save_practice_session(practice_session)
        
        print(f"🎯 Создана сессия упражнений: {len(practice_exercises)} упражнений для {len(errors_to_practice)} ошибок")
        return practice_session
    
    async def update_error_profile(self, new_errors: List[Dict], existing_profile: Dict) -> Dict:
        """
        Обновляет профиль ошибок пользователя
        """
        for error in new_errors:
            error_key = f"{error['error_type']}_{error['original_phrase'].lower().replace(' ', '_')}"
            
            if error_key in existing_profile:
                # Увеличиваем счетчик
                existing_profile[error_key]["count"] += 1
                existing_profile[error_key]["last_seen_timestamp"] = error["timestamp"]
                existing_profile[error_key]["last_seen_dialog_id"] = error["dialog_id"]
                existing_profile[error_key]["history"].append({
                    "dialog_id": error["dialog_id"],
                    "timestamp": error["timestamp"],
                    "context": error.get("context", "")
                })
            else:
                # Новая ошибка
                existing_profile[error_key] = {
                    "original_phrase": error["original_phrase"],
                    "error_type": error["error_type"],
                    "explanation": error["explanation"],
                    "correction": error["correction"],
                    "severity": error.get("severity", "medium"),
                    "count": 1,
                    "exercise_repetition_count": 6,  # X6 - нужно выполнить 6 упражнений
                    "first_seen_timestamp": error["timestamp"],
                    "last_seen_timestamp": error["timestamp"],
                    "first_seen_dialog_id": error["dialog_id"],
                    "last_seen_dialog_id": error["dialog_id"],
                    "history": [{
                        "dialog_id": error["dialog_id"],
                        "timestamp": error["timestamp"],
                        "context": error.get("context", "")
                    }]
                }
        
        # Сохраняем обновленный профиль
        self.save_error_profile(existing_profile)
        return existing_profile
    
    def select_errors_for_practice(self, error_profile: Dict, max_errors: int = 5) -> Dict:
        """
        Выбирает ошибки для отработки (максимум 5)
        """
        # Фильтруем ошибки, которые нужно отрабатывать (exercise_repetition_count > 0)
        eligible_errors = {k: v for k, v in error_profile.items() if v.get("exercise_repetition_count", 0) > 0}
        
        if not eligible_errors:
            return {}
        
        # Сортируем по приоритету: сначала с высоким счетчиком повторений, потом по частоте
        sorted_errors = sorted(
            eligible_errors.items(),
            key=lambda x: (x[1].get("exercise_repetition_count", 0), x[1].get("count", 0)),
            reverse=True
        )
        
        # Берем максимум 5 ошибок
        selected = dict(sorted_errors[:max_errors])
        
        print(f"🎯 Выбрано {len(selected)} ошибок для отработки:")
        for key, data in selected.items():
            print(f"  - {data['original_phrase']} ({data['error_type']}) X{data['exercise_repetition_count']}")
        
        return selected
    
    async def generate_exercises_for_error(self, error_data: Dict, translation_requests: List[Dict]) -> List[Dict]:
        """
        Генерирует 3 упражнения для одной ошибки
        """
        exercises = []
        original_phrase = error_data["original_phrase"]
        correction = error_data["correction"]
        error_type = error_data["error_type"]
        exercise_count = error_data.get("exercise_repetition_count", 6)
        
        # Определяем типы упражнений в зависимости от счетчика
        if exercise_count <= 3:
            # X1, X2, X3 - иногда текстовые упражнения
            exercise_types = self.get_exercise_types_for_low_count()
        else:
            # X4, X5, X6 - обычные упражнения
            exercise_types = self.get_exercise_types_for_high_count()
        
        # Генерируем 3 упражнения
        for i in range(3):
            exercise_type = exercise_types[i % len(exercise_types)]
            exercise = await self.generate_single_exercise(
                original_phrase, correction, error_type, exercise_type, i + 1
            )
            exercises.append(exercise)
        
        return exercises
    
    def get_exercise_types_for_low_count(self) -> List[str]:
        """Типы упражнений для X1-X3 (включая текстовые)"""
        return ["word_replacement", "translation_en_ru", "text_composition"]
    
    def get_exercise_types_for_high_count(self) -> List[str]:
        """Типы упражнений для X4-X6 (обычные)"""
        return ["word_replacement", "translation_en_ru", "translation_ru_en"]
    
    async def generate_single_exercise(self, original_phrase: str, correction: str, error_type: str, exercise_type: str, exercise_num: int) -> Dict:
        """
        Генерирует одно упражнение
        """
        exercise_prompt = self.get_exercise_prompt(original_phrase, correction, error_type, exercise_type)
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты эксперт по созданию упражнений для изучения английского языка."},
                    {"role": "user", "content": exercise_prompt}
                ],
                temperature=0.7
            )
            
            exercise_content = response.choices[0].message.content
            
            return {
                "exercise_id": f"{error_type}_{exercise_type}_{exercise_num}_{datetime.now().strftime('%H%M%S')}",
                "exercise_type": exercise_type,
                "exercise_number": exercise_num,
                "original_error": original_phrase,
                "correct_form": correction,
                "error_type": error_type,
                "content": exercise_content,
                "completed": False,
                "attempts": 0,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Ошибка генерации упражнения: {e}")
            return self.create_fallback_exercise(original_phrase, correction, exercise_type, exercise_num)
    
    def get_exercise_prompt(self, original_phrase: str, correction: str, error_type: str, exercise_type: str) -> str:
        """
        Создает промпт для генерации упражнения
        """
        base_info = f"Ошибка: '{original_phrase}' → Правильно: '{correction}' (Тип: {error_type})"
        
        if exercise_type == "word_replacement":
            return f"""
            {base_info}
            
            Создай упражнение "Замени слово":
            Дай предложение с неправильным словом/фразой и попроси заменить на правильное.
            Формат ответа:
            ЗАДАНИЕ: [предложение с ошибкой, выдели ошибку ***неправильное слово***]
            ПРАВИЛЬНЫЙ ОТВЕТ: [правильное предложение]
            """
            
        elif exercise_type == "translation_en_ru":
            return f"""
            {base_info}
            
            Создай упражнение "Перевод с английского на русский":
            Дай правильное английское предложение для перевода.
            Формат ответа:
            ЗАДАНИЕ: Переведите на русский: "[английское предложение с правильной формой]"
            ПРАВИЛЬНЫЙ ОТВЕТ: [русский перевод]
            """
            
        elif exercise_type == "translation_ru_en":
            return f"""
            {base_info}
            
            Создай упражнение "Перевод с русского на английский":
            Дай русское предложение, требующее использования правильной формы.
            Формат ответа:
            ЗАДАНИЕ: Переведите на английский: "[русское предложение]"
            ПРАВИЛЬНЫЙ ОТВЕТ: [английское предложение с правильной формой]
            """
            
        elif exercise_type == "simple_sentences":
            return f"""
            {base_info}
            
            Создай упражнение "Составьте 5 простых предложений":
            Попроси составить 5 простых предложений, используя правильную форму.
            Формат ответа:
            ЗАДАНИЕ: Составьте 5 простых предложений, используя "[правильная форма]"
            ПРИМЕРЫ ОТВЕТОВ:
            1. [пример предложения]
            2. [пример предложения]
            3. [пример предложения]
            4. [пример предложения]
            5. [пример предложения]
            """
            
        elif exercise_type == "text_composition":
            return f"""
            {base_info}
            
            Создай упражнение "Написание текста":
            Попроси написать связный текст из 3+ предложений с 2 использованиями правильной формы.
            Формат ответа:
            ЗАДАНИЕ: Напишите связный текст из 3-4 предложений, используя "[правильная форма]" ДВА РАЗА. Текст должен быть логически связанным.
            ПРИМЕР ОТВЕТА: [пример текста с двумя использованиями правильной формы]
            """
        
        return f"Создай упражнение для исправления ошибки: {original_phrase} → {correction}"
    
    def create_fallback_exercise(self, original_phrase: str, correction: str, exercise_type: str, exercise_num: int) -> Dict:
        """
        Создает простое упражнение если AI не сработал
        """
        return {
            "exercise_id": f"fallback_{exercise_type}_{exercise_num}_{datetime.now().strftime('%H%M%S')}",
            "exercise_type": exercise_type,
            "exercise_number": exercise_num,
            "original_error": original_phrase,
            "correct_form": correction,
            "error_type": "unknown",
            "content": f"ЗАДАНИЕ: Исправьте ошибку в фразе '{original_phrase}'\nПРАВИЛЬНЫЙ ОТВЕТ: {correction}",
            "completed": False,
            "attempts": 0,
            "timestamp": datetime.now().isoformat()
        }
    
    def save_practice_session(self, session_data: Dict):
        """
        Сохраняет сессию упражнений
        """
        sessions_dir = os.path.join(self.dialog_manager.logs_dir, "practice_sessions")
        if not os.path.exists(sessions_dir):
            os.makedirs(sessions_dir)
        
        session_file = os.path.join(sessions_dir, f"{session_data['session_id']}.json")
        
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=4)
            print(f"💾 Сессия упражнений сохранена: {session_file}")
        except Exception as e:
            print(f"❌ Ошибка сохранения сессии: {e}")
    
    def save_error_profile(self, error_profile: Dict):
        """
        Сохраняет обновленный профиль ошибок
        """
        error_profile_file = os.path.join(self.dialog_manager.logs_dir, "user_error_profile.json")
        
        try:
            with open(error_profile_file, 'w', encoding='utf-8') as f:
                json.dump(error_profile, f, ensure_ascii=False, indent=4)
            print(f"💾 Профиль ошибок обновлен: {len(error_profile)} записей")
        except Exception as e:
            print(f"❌ Ошибка сохранения профиля ошибок: {e}")
    
    def complete_exercise(self, session_id: str, exercise_id: str, user_answer: str, is_correct: bool):
        """
        Отмечает упражнение как выполненное и обновляет счетчики
        """
        # Загружаем сессию
        session_file = os.path.join(self.dialog_manager.logs_dir, "practice_sessions", f"{session_id}.json")
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # Находим упражнение и обновляем его
            for exercise in session_data["exercises"]:
                if exercise["exercise_id"] == exercise_id:
                    exercise["completed"] = True
                    exercise["user_answer"] = user_answer
                    exercise["is_correct"] = is_correct
                    exercise["attempts"] += 1
                    exercise["completion_timestamp"] = datetime.now().isoformat()
                    break
            
            # Сохраняем обновленную сессию
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=4)
            
            # Начисляем монеты за правильный ответ
            if is_correct:
                new_coin_count = self.dialog_manager.add_coins(1, "exercise_completed")
                print(f"🪙 +1 монета за правильное упражнение! Всего: {new_coin_count}")
            
            # Обновляем профиль ошибок
            error_completed = self.update_error_profile_after_exercise(exercise_id, is_correct)
            
            # Дополнительный бонус за полную отработку ошибки
            if error_completed:
                bonus_coins = self.dialog_manager.add_coins(5, "error_mastered")
                print(f"🎉 +5 монет бонус за полную отработку ошибки! Всего: {bonus_coins}")
                return {"coins_earned": 6, "error_mastered": True}  # 1 + 5 монет
            
            return {"coins_earned": 1 if is_correct else 0, "error_mastered": False}
            
        except Exception as e:
            print(f"❌ Ошибка обновления упражнения: {e}")
            return {"coins_earned": 0, "error_mastered": False}
    
    def update_error_profile_after_exercise(self, exercise_id: str, is_correct: bool) -> bool:
        """
        Обновляет профиль ошибок после выполнения упражнения
        Возвращает True если ошибка полностью отработана (достигла X0)
        """
        error_profile = self.load_user_error_profile()
        error_completed = False
        
        # Находим соответствующую ошибку по exercise_id
        for error_key, error_data in error_profile.items():
            if error_key in exercise_id or error_data["original_phrase"].replace(" ", "_") in exercise_id:
                if is_correct:
                    # Упражнение выполнено правильно - уменьшаем счетчик
                    error_data["exercise_repetition_count"] = max(0, error_data["exercise_repetition_count"] - 1)
                    
                    # Если счетчик дошел до 0 - ошибка отработана, можно удалить
                    if error_data["exercise_repetition_count"] == 0:
                        print(f"🎉 Ошибка '{error_data['original_phrase']}' полностью отработана!")
                        # Помечаем для удаления или архивируем
                        error_data["completed"] = True
                        error_data["completion_timestamp"] = datetime.now().isoformat()
                        error_completed = True
                else:
                    # Упражнение выполнено неправильно - увеличиваем счетчик
                    error_data["exercise_repetition_count"] += 1
                    print(f"❌ Ошибка в упражнении. Счетчик увеличен до X{error_data['exercise_repetition_count']}")
                
                error_data["last_exercise_timestamp"] = datetime.now().isoformat()
                break
        
        # Сохраняем обновленный профиль
        self.save_error_profile(error_profile)
        return error_completed
    
    async def check_exercise_answer(self, exercise: Dict, user_answer: str) -> Dict:
        """
        Проверяет ответ пользователя на упражнение с помощью OpenAI
        """
        exercise_content = exercise.get("content", "")
        correct_form = exercise.get("correct_form", "")
        original_error = exercise.get("original_error", "")
        exercise_type = exercise.get("exercise_type", "")
        
        # Создаем промпт для проверки
        check_prompt = f"""
        Проверь ответ пользователя на упражнение по английскому языку.
        
        Тип упражнения: {exercise_type}
        Исходная ошибка: {original_error}
        Правильная форма: {correct_form}
        
        Задание:
        {exercise_content}
        
        Ответ пользователя: "{user_answer}"
        
        Оцени ответ и дай краткую обратную связь на русском языке.
        Ответь в формате JSON:
        {{
            "is_correct": true/false,
            "feedback": "объяснение на русском, почему правильно или что нужно исправить",
            "correct_answer": "правильный ответ, если пользователь ошибся"
        }}
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты эксперт по проверке упражнений английского языка. Отвечай только в JSON формате."},
                    {"role": "user", "content": check_prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"❌ Ошибка проверки ответа: {e}")
            return {
                "is_correct": False,
                "feedback": "Ошибка при проверке ответа. Попробуйте еще раз.",
                "correct_answer": correct_form
            } 