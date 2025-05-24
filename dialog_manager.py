import os
import json
import datetime
from typing import Dict, List, Any

class DialogManager:
    def __init__(self):
        self.logs_dir = "dialog_logs"
        self.ensure_logs_directory()
        
    def ensure_logs_directory(self):
        """Создает папку для логов если её нет"""
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
            
    def save_dialog(self, scenario: str, difficulty: str, messages: List[Dict]):
        """Сохраняет диалог и поддерживает только последние 3 диалога"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dialog_{timestamp}.json"
        filepath = os.path.join(self.logs_dir, filename)
        
        dialog_data = {
            "timestamp": timestamp,
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
        """Сохраняет ошибку в общий файл ошибок"""
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
            
    def save_help_request(self, request_type: str, user_input: str, ai_response: str, context: Dict = None):
        """Сохраняет запросы помощи: переводы, культурные вопросы, варианты ответов"""
        help_file = os.path.join(self.logs_dir, "help_requests.json")
        
        help_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": request_type,  # "translation", "cultural", "answer_options", "assistant_question"
            "user_input": user_input,
            "ai_response": ai_response,
            "context": context or {}
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
            
    def save_aggressive_language_incident(self, user_message: str, detected_keywords: List[str], role_reaction: str, scenario: str, difficulty: str):
        """Сохраняет инцидент с использованием агрессивного языка пользователем."""
        incidents_file = os.path.join(self.logs_dir, "aggressive_incidents.json")
        
        incident_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
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