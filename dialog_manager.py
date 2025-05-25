import os
import json
import datetime
import uuid # Для генерации уникальных ID
from typing import Dict, List, Any
import asyncio # Для асинхронных операций с OpenAI
from openai import OpenAI # Убедимся, что OpenAI импортирован

class DialogManager:
    def __init__(self, client: OpenAI = None): # Принимаем OpenAI клиент опционально
        self.logs_dir = "dialog_logs"
        self.user_errors_raw_file = os.path.join(self.logs_dir, "user_errors_raw.json")
        self.user_error_profile_file = os.path.join(self.logs_dir, "user_error_profile.json")
        self.user_coins_file = os.path.join(self.logs_dir, "user_coins.json")  # Новый файл для монет
        self.ensure_logs_directory()
        self.ensure_log_files()
        self.client = client # Сохраняем клиент OpenAI, если передан
        
    def ensure_logs_directory(self):
        """Создает папку для логов если её нет"""
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
            
    def ensure_log_files(self):
        """Создает JSON файлы для логов, если их нет."""
        for file_path in [self.user_errors_raw_file, self.user_error_profile_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f) # Инициализируем пустым списком или словарем, user_error_profile лучше {} если это будет словарь профилей
                    # Исправим user_error_profile.json на {} при создании
                    if file_path == self.user_error_profile_file:
                        f.seek(0)
                        json.dump({}, f)
                print(f"Created log file: {file_path}")
        
        # Создаем файл для монет, если его нет
        if not os.path.exists(self.user_coins_file):
            with open(self.user_coins_file, 'w', encoding='utf-8') as f:
                json.dump({"coins": 0, "total_earned": 0, "last_updated": datetime.datetime.now().isoformat()}, f)
            print(f"Created coins file: {self.user_coins_file}")
    
    def get_user_coins(self) -> int:
        """Получает текущее количество монет пользователя"""
        try:
            with open(self.user_coins_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("coins", 0)
        except Exception as e:
            print(f"Error loading user coins: {e}")
            return 0
    
    def add_coins(self, amount: int, reason: str = "exercise_completed") -> int:
        """Добавляет монеты пользователю и возвращает новое количество"""
        try:
            current_data = {"coins": 0, "total_earned": 0}
            if os.path.exists(self.user_coins_file):
                with open(self.user_coins_file, 'r', encoding='utf-8') as f:
                    current_data = json.load(f)
            
            current_data["coins"] += amount
            current_data["total_earned"] = current_data.get("total_earned", 0) + amount
            current_data["last_updated"] = datetime.datetime.now().isoformat()
            current_data["last_reason"] = reason
            
            with open(self.user_coins_file, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
            
            print(f"💰 Added {amount} coins for '{reason}'. Total: {current_data['coins']}")
            return current_data["coins"]
            
        except Exception as e:
            print(f"Error adding coins: {e}")
            return self.get_user_coins()
    
    def get_coins_data(self) -> Dict:
        """Получает полную информацию о монетах пользователя"""
        try:
            with open(self.user_coins_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading coins data: {e}")
            return {"coins": 0, "total_earned": 0}
            
    def generate_dialog_id(self):
        """Генерирует уникальный ID для диалога."""
        # Этот метод больше не будет основным источником ID для save_dialog,
        # ID будет приходить от ChatScreen. Оставляем его как вспомогательный, если понадобится.
        return str(uuid.uuid4())

    def save_dialog(self, dialog_id: str, scenario: str, difficulty: str, messages: List[Dict]):
        """Сохраняет диалог с предоставленным ID и поддерживает только последние 3 диалога."""
        # dialog_id теперь приходит как аргумент
        timestamp_dt = datetime.datetime.now()
        timestamp_str_file = timestamp_dt.strftime("%Y%m%d_%H%M%S")
        timestamp_iso = timestamp_dt.isoformat()
        
        filename = f"dialog_{timestamp_str_file}_{dialog_id}.json"
        filepath = os.path.join(self.logs_dir, filename)
        
        dialog_data = {
            "dialog_id": dialog_id, 
            "timestamp_iso": timestamp_iso,
            "scenario": scenario,
            "difficulty": difficulty,
            "messages": messages,
            "message_count": len(messages) - 1,  # исключаем system message
            "duration_minutes": None  # TODO: можно добавить время диалога
        }
        
        # Сохраняем новый диалог
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dialog_data, f, ensure_ascii=False, indent=2)
            
        # Удаляем старые диалоги, оставляем только последние 3
        self.cleanup_old_dialogs()
        
    def cleanup_old_dialogs(self):
        """Удаляет старые диалоги, оставляет только последние 3"""
        dialog_files = []
        for filename in os.listdir(self.logs_dir):
            if filename.startswith("dialog_") and filename.endswith(".json"):
                filepath = os.path.join(self.logs_dir, filename)
                dialog_files.append((filepath, os.path.getctime(filepath)))
        
        # Сортируем по времени создания (новые первые)
        dialog_files.sort(key=lambda x: x[1], reverse=True)
        
        # Удаляем файлы старше 3-х последних
        for filepath, _ in dialog_files[3:]:
            try:
                os.remove(filepath)
                print(f"Deleted old dialog: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"Error deleting dialog {filepath}: {e}")
                
    def save_error(self, error_type: str, error_message: str, context: Dict = None):
        """Сохраняет системную или API ошибку в общий файл ошибок"""
        errors_file = os.path.join(self.logs_dir, "errors.json")
        
        error_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": error_type,
            "message": error_message,
            "context": context or {}
        }
        
        # Загружаем существующие ошибки или создаем новый список
        errors = []
        if os.path.exists(errors_file):
            try:
                with open(errors_file, 'r', encoding='utf-8') as f:
                    errors = json.load(f)
            except Exception as e:
                print(f"Error loading errors file: {e}")
                errors = []
        
        # Добавляем новую ошибку
        errors.append(error_entry)
        
        # Сохраняем обратно
        with open(errors_file, 'w', encoding='utf-8') as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
            
    def log_raw_user_error(self, dialog_id: str, user_message_text: str, detected_error_type: str, raw_error_details: Any, context: Dict = None):
        """Логирует "сырую" ошибку пользователя, обнаруженную до анализа AI."""
        error_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "dialog_id": dialog_id,
            "user_message": user_message_text,
            "error_type": detected_error_type, # e.g., "russian_word", "profanity", "potential_typo"
            "details": raw_error_details, # e.g., the specific word or phrase
            "context": context or {}
        }
        
        raw_errors = []
        if os.path.exists(self.user_errors_raw_file):
            try:
                with open(self.user_errors_raw_file, 'r', encoding='utf-8') as f:
                    raw_errors = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: {self.user_errors_raw_file} is corrupted or not valid JSON. Initializing as empty list.")
                raw_errors = []
            except Exception as e:
                print(f"Error loading {self.user_errors_raw_file}: {e}")
                raw_errors = [] # Fallback to empty list
        
        raw_errors.append(error_entry)
        
        try:
            with open(self.user_errors_raw_file, 'w', encoding='utf-8') as f:
                json.dump(raw_errors, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error writing to {self.user_errors_raw_file}: {e}")

    def save_help_request(self, dialog_id: str, request_type: str, user_input: str, ai_response: str, context: Dict = None):
        """Сохраняет запросы помощи: переводы, культурные вопросы, варианты ответов"""
        help_file = os.path.join(self.logs_dir, "help_requests.json")
        
        entry_context = context or {}
        entry_context['dialog_id'] = dialog_id # Убедимся, что ID диалога есть в контексте

        help_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "dialog_id": dialog_id, # Явное поле для ID диалога
            "type": request_type,  # "translation", "cultural", "answer_options", "assistant_question"
            "user_input": user_input,
            "ai_response": ai_response,
            "context": entry_context # Обновленный контекст
        }
        
        # Загружаем существующие запросы или создаем новый список
        help_requests = []
        if os.path.exists(help_file):
            try:
                with open(help_file, 'r', encoding='utf-8') as f:
                    help_requests = json.load(f)
            except Exception as e:
                print(f"Error loading help requests file: {e}")
                help_requests = []
        
        # Добавляем новый запрос
        help_requests.append(help_entry)
        
        # Сохраняем обратно
        with open(help_file, 'w', encoding='utf-8') as f:
            json.dump(help_requests, f, ensure_ascii=False, indent=2)
            
    def save_aggressive_language_incident(self, dialog_id: str, user_message: str, detected_keywords: List[str], role_reaction: str, scenario: str, difficulty: str):
        """Сохраняет инцидент с использованием агрессивного языка пользователем."""
        incidents_file = os.path.join(self.logs_dir, "aggressive_incidents.json")
        
        incident_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "dialog_id": dialog_id, # Добавляем ID диалога
            "user_message": user_message,
            "detected_keywords": detected_keywords,
            "role_reaction": role_reaction, # Как отреагировала роль ИИ
            "scenario": scenario,
            "difficulty": difficulty
        }
        
        incidents = []
        if os.path.exists(incidents_file):
            try:
                with open(incidents_file, 'r', encoding='utf-8') as f:
                    incidents = json.load(f)
            except Exception as e:
                print(f"Error loading aggressive_incidents.json: {e}")
                incidents = []
        
        incidents.append(incident_entry)
        
        with open(incidents_file, 'w', encoding='utf-8') as f:
            json.dump(incidents, f, ensure_ascii=False, indent=2)
            
    def get_dialog_stats(self) -> Dict[str, Any]:
        """Возвращает статистику по диалогам"""
        stats = {
            "total_dialogs": 0,
            "total_errors": 0,
            "total_help_requests": 0,
            "scenarios_used": {},
            "difficulty_distribution": {}
        }
        
        # Подсчет диалогов
        for filename in os.listdir(self.logs_dir):
            if filename.startswith("dialog_") and filename.endswith(".json"):
                stats["total_dialogs"] += 1
                try:
                    with open(os.path.join(self.logs_dir, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        scenario = data.get("scenario", "unknown")
                        difficulty = data.get("difficulty", "unknown")
                        stats["scenarios_used"][scenario] = stats["scenarios_used"].get(scenario, 0) + 1
                        stats["difficulty_distribution"][difficulty] = stats["difficulty_distribution"].get(difficulty, 0) + 1
                except Exception as e:
                    print(f"Error reading dialog {filename}: {e}")
        
        # Подсчет ошибок
        errors_file = os.path.join(self.logs_dir, "errors.json")
        if os.path.exists(errors_file):
            try:
                with open(errors_file, 'r', encoding='utf-8') as f:
                    errors = json.load(f)
                    stats["total_errors"] = len(errors)
            except Exception:
                pass
        
        # Подсчет запросов помощи
        help_file = os.path.join(self.logs_dir, "help_requests.json")
        if os.path.exists(help_file):
            try:
                with open(help_file, 'r', encoding='utf-8') as f:
                    help_requests = json.load(f)
                    stats["total_help_requests"] = len(help_requests)
            except Exception:
                pass
                
        return stats
    
    def get_error_summary_for_exercises(self) -> Dict[str, Any]:
        """Анализирует ошибки для создания персонализированных заданий"""
        errors_file = os.path.join(self.logs_dir, "errors.json")
        
        if not os.path.exists(errors_file):
            return {"error_themes": [], "recommendations": [], "total_errors": 0}
        
        try:
            with open(errors_file, 'r', encoding='utf-8') as f:
                errors = json.load(f)
            
            error_themes = []
            recommendations = []
            
            # Анализируем последние ошибки диалогов
            dialog_errors = [e for e in errors if e.get("type") == "dialog_error_summary"]
            
            for error in dialog_errors[-5:]:  # последние 5 диалогов с ошибками
                content = error.get("message", "")
                
                # Извлекаем темы для заданий
                if "ТЕМЫ_ДЛЯ_ЗАДАНИЙ:" in content:
                    themes_section = content.split("ТЕМЫ_ДЛЯ_ЗАДАНИЙ:")[1].strip()
                    error_themes.append(themes_section)
                
                # Извлекаем рекомендации
                if "РЕКОМЕНДАЦИИ:" in content:
                    recommendations_section = content.split("РЕКОМЕНДАЦИИ:")[1]
                    if "ТЕМЫ_ДЛЯ_ЗАДАНИЙ:" in recommendations_section:
                        recommendations_section = recommendations_section.split("ТЕМЫ_ДЛЯ_ЗАДАНИЙ:")[0]
                    recommendations.append(recommendations_section.strip())
            
            return {
                "error_themes": error_themes,
                "recommendations": recommendations,
                "total_errors": len(dialog_errors),
                "recent_errors": dialog_errors[-3:] if dialog_errors else []
            }
            
        except Exception as e:
            print(f"Error analyzing errors for exercises: {e}")
            return {"error_themes": [], "recommendations": [], "total_errors": 0} 

    async def analyze_and_save_detailed_user_errors(self, dialog_id: str, user_message_text: str, full_dialog_history: List[Dict]):
        """
        Анализирует сообщение пользователя с помощью OpenAI для выявления подробных ошибок
        и сохраняет их в user_error_profile.json.
        """
        if not self.client:
            print("OpenAI client not set in DialogManager. Cannot analyze detailed errors.")
            return

        # Формируем контекст диалога для OpenAI
        dialog_context_for_prompt = ""
        for msg in full_dialog_history[-5:]: # Берем последние 5 сообщений для контекста
            role = "User" if msg["role"] == "user" else "Assistant"
            dialog_context_for_prompt += f"{role}: {msg['content']}\\n"

        error_analysis_prompt = f"""
        Ты - продвинутый ассистент по проверке английского языка.
        Проанализируй ТОЛЬКО ПОСЛЕДНЕЕ СООБЩЕНИЕ ОТ ПОЛЬЗОВАТЕЛЯ на наличие ошибок.
        Учитывай предыдущий контекст диалога для лучшего понимания.

        Контекст диалога (последние сообщения):
        {dialog_context_for_prompt}
        Последнее сообщение от пользователя для анализа: "{user_message_text}"

        Твоя задача - выявить следующие типы ошибок в последнем сообщении пользователя:
        1.  Грамматические ошибки (неправильное время глагола, артикли, предлоги, порядок слов, согласование времен и т.д.).
        2.  Лексические ошибки (неправильный выбор слова, использование неформальной лексики в формальном контексте, смешение слов).
        3.  Стилистические ошибки (неестественные или неуклюжие фразы, тавтология).
        4.  Орфографические ошибки (опечатки).
        5.  Использование русских слов (если это не часть специального сценария, где это допустимо, считай это ошибкой).
        6.  Использование ненормативной лексики (маты, оскорбления).

        Для КАЖДОЙ найденной ошибки, предоставь следующую информацию в формате JSON объекта:
        {{
            "original_phrase": "фрагмент текста пользователя с ошибкой",
            "error_type": "строка, описывающая категорию ошибки (например, 'verb_tense', 'spelling', 'word_choice', 'russian_word_inappropriate', 'profanity', 'article_error', 'preposition_error')",
            "explanation": "краткое и понятное объяснение ошибки на русском языке",
            "correction": "предлагаемый правильный вариант на английском языке"
        }}

        Если ошибок не найдено, верни пустой список [].
        Предоставь ответ в виде списка JSON объектов. Каждый объект - это одна ошибка.
        Пример:
        [
            {{
                "original_phrase": "I has a cat",
                "error_type": "verb_tense",
                "explanation": "Неправильное спряжение глагола 'to have' в настоящем времени для местоимения 'I'. Правильно использовать 'have'.",
                "correction": "I have a cat"
            }},
            {{
                "original_phrase": "My freind",
                "error_type": "spelling",
                "explanation": "Орфографическая ошибка в слове 'friend'.",
                "correction": "My friend"
            }}
        ]
        """

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo", # Можно заменить на gpt-4 для более точного анализа
                messages=[
                    {"role": "system", "content": "You are an expert English language error detection assistant. Provide output ONLY in JSON format as a list of error objects, or an empty list if no errors are found."},
                    {"role": "user", "content": error_analysis_prompt}
                ],
                temperature=0.2, # Более низкая температура для точности
                response_format={"type": "json_object"} # Запрос JSON ответа, если модель поддерживает
            )
            
            ai_response_content = response.choices[0].message.content
            detected_errors = json.loads(ai_response_content) # Предполагаем, что модель вернула строку JSON

            if not isinstance(detected_errors, list): # Если модель вернула не список (например, сам объект {"errors": [...]})
                # Попробуем извлечь список из ключа, если он есть, или обернуть в список
                if isinstance(detected_errors, dict) and "errors" in detected_errors and isinstance(detected_errors["errors"], list):
                    detected_errors = detected_errors["errors"]
                else: # Если формат совсем неожиданный, считаем, что ошибок нет или не удалось распарсить
                    print(f"Warning: OpenAI returned unexpected format for error analysis: {ai_response_content}")
                    detected_errors = []


        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from OpenAI error analysis: {e}")
            print(f"OpenAI response content: {ai_response_content}")
            detected_errors = []
        except Exception as e:
            print(f"Error calling OpenAI for error analysis: {e}")
            detected_errors = []

        if not detected_errors:
            return # Нет ошибок для сохранения

        # Загрузка и обновление user_error_profile.json
        error_profile = {}
        if os.path.exists(self.user_error_profile_file):
            try:
                with open(self.user_error_profile_file, 'r', encoding='utf-8') as f:
                    error_profile = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: {self.user_error_profile_file} is corrupted. Initializing new profile.")
                error_profile = {}
        
        current_timestamp = datetime.datetime.now().isoformat()

        for error_data in detected_errors:
            if not all(k in error_data for k in ["original_phrase", "error_type", "explanation", "correction"]):
                print(f"Skipping malformed error data from OpenAI: {error_data}")
                continue

            # Ключ для профиля: нормализованная оригинальная фраза + тип ошибки
            # Это простой подход, можно усложнить для лучшей группировки
            error_key_base = error_data["original_phrase"].lower().strip().replace(" ", "_")
            error_key = f"{error_data['error_type']}_{error_key_base}"


            if error_key in error_profile:
                # Обновляем существующую ошибку
                error_profile[error_key]["count"] += 1
                error_profile[error_key]["last_seen_timestamp"] = current_timestamp
                error_profile[error_key]["last_seen_dialog_id"] = dialog_id
                # Добавляем объяснение и исправление, если они новые или отличаются (можно хранить списком)
                # Для простоты пока перезаписываем, но лучше сделать список уникальных
                error_profile[error_key]["explanation"] = error_data["explanation"]
                error_profile[error_key]["correction"] = error_data["correction"]
                error_profile[error_key].setdefault("history", []).append({
                    "dialog_id": dialog_id,
                    "user_message": user_message_text, # Сообщение, в котором ошибка
                    "timestamp": current_timestamp
                })
            else:
                # Добавляем новую ошибку
                error_profile[error_key] = {
                    "original_phrase": error_data["original_phrase"],
                    "error_type": error_data["error_type"],
                    "explanation": error_data["explanation"],
                    "correction": error_data["correction"],
                    "count": 1,
                    "exercise_repetition_count": 6, # Начальное значение X6
                    "first_seen_timestamp": current_timestamp,
                    "last_seen_timestamp": current_timestamp,
                    "first_seen_dialog_id": dialog_id,
                    "last_seen_dialog_id": dialog_id,
                    "history": [{
                        "dialog_id": dialog_id,
                        "user_message": user_message_text,
                        "timestamp": current_timestamp
                    }]
                }
        
        # Сохраняем обновленный профиль
        try:
            with open(self.user_error_profile_file, 'w', encoding='utf-8') as f:
                json.dump(error_profile, f, ensure_ascii=False, indent=4)
            print(f"User error profile updated with {len(detected_errors)} errors from dialog {dialog_id}")
        except Exception as e:
            print(f"Error writing to {self.user_error_profile_file}: {e}")

    def set_openai_client(self, client: OpenAI):
        """Устанавливает клиент OpenAI, если он не был передан в конструктор."""
        self.client = client

    def get_recent_dialogs(self, limit: int = 3) -> List[Dict]:
        """
        Получает последние диалоги для анализа ошибок
        """
        dialogs = []
        
        # Получаем все файлы диалогов
        dialog_files = []
        for filename in os.listdir(self.logs_dir):
            if filename.startswith("dialog_") and filename.endswith(".json"):
                file_path = os.path.join(self.logs_dir, filename)
                # Сортируем по времени изменения файла
                mod_time = os.path.getmtime(file_path)
                dialog_files.append((mod_time, file_path, filename))
        
        # Сортируем по времени (новые сначала)
        dialog_files.sort(reverse=True)
        
        # Загружаем последние limit диалогов
        for i, (mod_time, file_path, filename) in enumerate(dialog_files[:limit]):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    dialog_data = json.load(f)
                    dialogs.append(dialog_data)
                    print(f"📁 Загружен диалог: {filename} ({len(dialog_data.get('messages', []))} сообщений)")
            except Exception as e:
                print(f"❌ Ошибка загрузки диалога {filename}: {e}")
        
        print(f"📚 Загружено {len(dialogs)} диалогов для анализа")
        return dialogs 