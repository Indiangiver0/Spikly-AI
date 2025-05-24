import toga
from toga.style import Pack
from openai import OpenAI
import asyncio
from config import OPENAI_API_KEY
from templates import templates
from help_system import HelpDialog
from dialog_manager import DialogManager
from language_filter import LanguageFilter
from prompts import get_system_prompt

class StartScreen:
    def __init__(self, app):
        self.app = app
        self.selected_scenario = None
        self.selected_difficulty = None
        
    def build(self):
        # Заголовок
        title = toga.Label(
            "Английские сценки",
            style=Pack(
                text_align="center",
                font_size=24,
                font_weight="bold",
                padding=(20, 0, 30, 0)
            )
        )
        
        # Выбор сценария
        scenario_label = toga.Label(
            "Выберите сценарий:",
            style=Pack(font_size=16, padding=(0, 0, 10, 0))
        )
        
        self.scenario_selection = toga.Selection(
            items=[f"{key}. {value['description']}" for key, value in templates.items()],
            style=Pack(padding=(0, 0, 20, 0), width=400)
        )
        
        # Выбор сложности
        difficulty_label = toga.Label(
            "Выберите сложность:",
            style=Pack(font_size=16, padding=(0, 0, 10, 0))
        )
        
        difficulty_options = [
            "Easy (B1-B2) - Простая лексика, неограниченные подсказки",
            "Medium (B2-C1) - Средняя сложность, 10-15 подсказок", 
            "Hard (C1-C2) - Продвинутый уровень, 5 подсказок"
        ]
        
        self.difficulty_selection = toga.Selection(
            items=difficulty_options,
            style=Pack(padding=(0, 0, 30, 0), width=400)
        )
        
        # Кнопка начала диалога
        start_button = toga.Button(
            "Начать диалог",
            on_press=self.start_dialog,
            style=Pack(
                padding=10,
                background_color="#007bff",
                color="#ffffff",
                font_size=16
            )
        )
        
        # Основной контейнер
        main_box = toga.Box(
            children=[
                title,
                scenario_label,
                self.scenario_selection,
                difficulty_label,
                self.difficulty_selection,
                start_button
            ],
            style=Pack(
                direction="column",
                alignment="center",
                padding=30
            )
        )
        
        return main_box
    
    def start_dialog(self, widget):
        if self.scenario_selection.value and self.difficulty_selection.value:
            # Извлекаем номер сценария
            scenario_key = int(self.scenario_selection.value.split('.')[0])
            selected_template = templates[scenario_key]
            scenario_text = selected_template["description"]
            
            # Определяем сложность
            difficulty = self.difficulty_selection.value.split(' ')[0].lower()
            
            # Переходим к чату
            self.app.show_chat_screen(scenario_key, scenario_text, difficulty)
        else:
            self.app.main_window.info_dialog("Ошибка", "Пожалуйста, выберите сценарий и сложность")


class ChatScreen:
    def __init__(self, app, scenario_key, scenario, difficulty):
        self.app = app
        self.scenario_key = scenario_key
        self.scenario = scenario
        self.difficulty = difficulty
        self.messages = []
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.hint_count = 0
        self.max_hints = self.get_max_hints()
        self.help_dialog = None
        self.dialog_manager = DialogManager()
        self.language_filter = LanguageFilter()
        
        # Настройка системного промпта
        self.setup_system_prompt()
    
    def get_max_hints(self):
        hints_map = {
            "easy": float('inf'),  # неограниченно
            "medium": 15,
            "hard": 5
        }
        return hints_map.get(self.difficulty, 15)
    
    def setup_system_prompt(self):
        # difficulty_instructions = {
        #     "easy": "Use simple vocabulary and grammar (B1-B2 level). Avoid complex cultural references. Keep dialogue topics straightforward.",
        #     "medium": "Use intermediate complexity vocabulary and grammar (B2-C1 level). Include some cultural context.",
        #     "hard": "Use advanced vocabulary, idioms, and native-like speech (C1-C2 level). Include cultural references and context freely."
        # }
        # 
        # system_content = f"""You are strictly playing the role described in this scenario: {self.scenario}. 
        # Never break character. 
        # Difficulty level: {self.difficulty}
        # Instructions: {difficulty_instructions.get(self.difficulty, '')}
        # Keep responses conversational and engaging. Wait for the user to initiate the conversation."""
        
        # Получаем реакцию на агрессию для текущей роли
        current_template_details = templates.get(self.scenario_key, {})
        aggression_response_for_role = current_template_details.get("aggression_response")

        system_content = get_system_prompt(
            scenario_description=self.scenario, 
            difficulty=self.difficulty,
            role_aggression_response=aggression_response_for_role
        )
        
        self.messages = [{"role": "system", "content": system_content}]
    
    def build(self):
        # Заголовок с информацией о сценарии
        header = toga.Box(
            children=[
                toga.Label(
                    f"Сценарий: {self.scenario}",
                    style=Pack(font_size=14, padding=(5, 10))
                ),
                toga.Label(
                    f"Сложность: {self.difficulty.upper()}",
                    style=Pack(font_size=12, padding=(5, 10))
                )
            ],
            style=Pack(direction="column", background_color="#f8f9fa", padding=10)
        )
        
        # Область чата
        self.chat_log = toga.MultilineTextInput(
            readonly=True,
            style=Pack(flex=1, padding=10)
        )
        
        # Поле ввода и кнопки
        self.user_input = toga.TextInput(
            placeholder="Введите ваше сообщение...",
            style=Pack(flex=1, padding=(0, 10))
        )
        
        send_button = toga.Button(
            "Отправить",
            on_press=self.send_message,
            style=Pack(padding=(0, 10))
        )
        
        # Сохраняем ссылку на кнопку помощи
        self.help_button = toga.Button(
            f"Помощь ({self.max_hints - self.hint_count if self.max_hints != float('inf') else '∞'})",
            on_press=self.show_help,
            style=Pack(padding=(0, 10), background_color="#28a745", color="#ffffff")
        )
        
        back_button = toga.Button(
            "Назад",
            on_press=self.go_back,
            style=Pack(padding=(0, 10), background_color="#6c757d", color="#ffffff")
        )
        
        # Контейнер для ввода
        input_box = toga.Box(
            children=[self.user_input, send_button, self.help_button, back_button],
            style=Pack(direction="row", padding=10)
        )
        
        # Основной контейнер
        main_box = toga.Box(
            children=[header, self.chat_log, input_box],
            style=Pack(direction="column")
        )
        
        return main_box
    
    async def send_message(self, widget):
        user_text = self.user_input.value.strip()
        if not user_text:
            return

        # Сбрасываем кэш подсказок, так как диалог изменится
        if self.help_dialog:
            self.help_dialog._cached_help_content = None
            self.help_dialog._cached_for_messages_hash = None

        # Проверка на выход
        if any(word in user_text.lower() for word in ["выход", "exit", "bye"]):
            self.chat_log.value += "\nДиалог завершён. До встречи!"
            self.save_dialog_on_completion()
            return

        # Проверка на агрессивный язык
        if self.language_filter.is_aggressive(user_text):
            detected_keywords = self.language_filter.get_detected_keywords(user_text)
            
            # Проверяем, относится ли агрессия к текущей роли
            role_keywords_present = False
            current_template = templates.get(self.scenario_key)
            if current_template and "keywords_for_reaction_check" in current_template:
                for r_keyword in current_template["keywords_for_reaction_check"]:
                    if r_keyword in user_text.lower(): # Проверяем наличие ключевых слов роли в сообщении
                        role_keywords_present = True
                        break
            
            # Реакция, если агрессия направлена на роль или если нет ключевых слов для проверки (общая агрессия)
            should_react_aggressively = role_keywords_present or (current_template and "keywords_for_reaction_check" not in current_template)

            if should_react_aggressively:
                aggression_response_text = templates.get(self.scenario_key, {}).get("aggression_response", "Please be respectful. I'm here to help you practice English.")
                
                self.chat_log.value += f"\nYou: {user_text}\n"
                self.chat_log.value += f"\nAI (System Reaction): {aggression_response_text}\n"
                self.user_input.value = ""

                # Логирование инцидента
                self.dialog_manager.save_aggressive_language_incident(
                    user_message=user_text,
                    detected_keywords=detected_keywords,
                    role_reaction=aggression_response_text,
                    scenario=self.scenario,
                    difficulty=self.difficulty
                )
                # Логируем также как ошибку пользователя для последующего анализа
                error_context = {
                    "scenario": self.scenario,
                    "difficulty": self.difficulty,
                    "user_message": user_text,
                    "detected_keywords": detected_keywords,
                    "ai_reaction": aggression_response_text
                }
                self.dialog_manager.save_error(
                    error_type="aggressive_language",
                    error_message=f"User used aggressive language: {', '.join(detected_keywords)}",
                    context=error_context
                )
                return # Прерываем дальнейшую обработку сообщения

        self.user_input.value = ""
        self.chat_log.value += f"\nYou: {user_text}\n"

        try:
            # Сбрасываем кэш подсказок также перед получением ответа от AI
            if self.help_dialog:
                self.help_dialog._cached_help_content = None
                self.help_dialog._cached_for_messages_hash = None

            # Формируем промпт с проверкой на завершение диалога
            enhanced_messages = self.messages + [{"role": "user", "content": user_text}]
            
            # Проверяем, нужно ли завершать диалог
            should_end = await self.check_conversation_completion(enhanced_messages)
            
            if should_end:
                # ИИ завершает диалог
                completion_response = await self.generate_completion_message(enhanced_messages)
                self.chat_log.value += f"\nAI: {completion_response}"
                self.chat_log.value += "\n\n--- Диалог завершён автоматически ---"
                self.messages.append({"role": "user", "content": user_text})
                self.messages.append({"role": "assistant", "content": completion_response})
                
                # Показываем диалог 3 секунды перед закрытием
                await asyncio.sleep(3)
                
                self.save_dialog_on_completion()
                self.app.show_start_screen()
                return
            
            # Обычный запрос к OpenAI
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=enhanced_messages
            )
            answer = response.choices[0].message.content
            self.chat_log.value += f"\nAI: {answer}"
            self.messages.append({"role": "user", "content": user_text})
            self.messages.append({"role": "assistant", "content": answer})

        except Exception as e:
            self.chat_log.value += f"\nОшибка: {e}"
            self.dialog_manager.save_error("api_error", str(e), {
                "scenario": self.scenario,
                "difficulty": self.difficulty,
                "user_message": user_text
            })
    
    async def analyze_dialog_errors(self):
        """Анализирует ошибки пользователя во всем диалоге после завершения"""
        # Собираем все сообщения пользователя
        user_messages = []
        for msg in self.messages:
            if msg["role"] == "user":
                user_messages.append(msg["content"])
        
        if not user_messages:
            return
        
        # Формируем текст всех сообщений пользователя
        all_user_text = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(user_messages)])
        
        error_analysis_prompt = f"""
        Проанализируй все сообщения пользователя из диалога на английском языке на предмет ошибок:
        
        Сценарий: {self.scenario}
        Уровень сложности: {self.difficulty}
        
        Сообщения пользователя:
        {all_user_text}
        
        Создай детальную сводку ошибок в формате:
        
        ОБЩИЕ_ОШИБКИ: [перечисли основные типы ошибок, которые повторяются]
        
        КОНКРЕТНЫЕ_ОШИБКИ:
        [Для каждого сообщения с ошибками:]
        Сообщение N: "оригинальный текст"
        Ошибки: [список ошибок]
        Исправления: [правильный вариант]
        
        РЕКОМЕНДАЦИИ: [что нужно изучить/повторить пользователю]
        
        ТЕМЫ_ДЛЯ_ЗАДАНИЙ: [конкретные темы для создания упражнений]
        
        Если ошибок нет - напиши "ОШИБОК_НЕТ"
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": error_analysis_prompt}],
                temperature=0.3
            )
            
            error_analysis = response.choices[0].message.content
            
            # Проверяем, есть ли ошибки
            if "ОШИБОК_НЕТ" not in error_analysis.upper():
                # Сохраняем сводку ошибок
                self.dialog_manager.save_error(
                    "dialog_error_summary",
                    error_analysis,
                    {
                        "scenario": self.scenario,
                        "difficulty": self.difficulty,
                        "total_user_messages": len(user_messages),
                        "dialog_length": len(self.messages),
                        "all_user_messages": user_messages
                    }
                )
                print(f"Dialog error analysis completed and saved")
            else:
                print("No errors found in dialog")
                
        except Exception as e:
            print(f"Error analyzing dialog: {e}")
    
    def _analyze_dialog_sync(self):
        """Синхронная версия анализа ошибок для threading fallback"""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.analyze_dialog_errors())
            loop.close()
        except Exception as e:
            print(f"Error in sync dialog analysis: {e}")
    
    async def check_conversation_completion(self, messages):
        """Проверяет, нужно ли завершать диалог"""
        if len(messages) < 12:  # Увеличиваем минимальную длину диалога
            return False
            
        # Получаем последние 4 сообщения для анализа
        recent_messages = messages[-4:]
        context = ""
        for msg in recent_messages:
            role = "Пользователь" if msg["role"] == "user" else "AI"
            context += f"{role}: {msg['content']}\n"
        
        # Проверяем прощальные слова
        last_user_message = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                last_user_message = msg["content"].lower()
                break
        
        farewell_words = ["bye", "goodbye", "see you", "thank you", "thanks", "that's all", "конец", "пока", "до свидания"]
        has_farewell = any(word in last_user_message for word in farewell_words)
        
        if not has_farewell:
            return False  # Если нет прощальных слов, не завершаем
        
        completion_check_prompt = f"""
        Проанализируй диалог и определи, нужно ли его завершить:
        
        Сценарий: {self.scenario}
        Последние сообщения:
        {context}
        Последнее сообщение пользователя: {last_user_message}
        
        КРИТЕРИИ для завершения (ХОТЯ БЫ 2 из 3 должны выполняться):
        1. Пользователь явно показывает что хочет закончить (прощается: "bye", "see you", "thanks")
        2. Цель сценария достигнута (заказ оформлен, регистрация завершена, проблема решена)
        3. В диалоге нет открытых вопросов или ожидающих действий
        
        Ответь ТОЛЬКО: ДА (если нужно завершить) или НЕТ (если продолжать)
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": completion_check_prompt}],
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip().upper()
            return "ДА" in result
            
        except Exception as e:
            print(f"Error checking conversation completion: {e}")
            return False
    
    async def generate_completion_message(self, messages):
        """Генерирует сообщение для завершения диалога"""
        completion_prompt = f"""
        Сгенерируй естественное завершающее сообщение для диалога:
        
        Сценарий: {self.scenario}
        Последние сообщения: {messages[-4:]}
        
        Сообщение должно:
        1. Естественно завершать диалог
        2. Быть в характере роли из сценария
        3. Подводить итог или прощаться
        4. Быть на английском языке
        
        Ответь только текстом сообщения, без дополнительных объяснений.
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": completion_prompt}],
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return "Thank you for the conversation. Have a great day!"
    
    def save_dialog_on_completion(self):
        """Сохраняет диалог при завершении"""
        if len(self.messages) > 1:  # есть сообщения кроме system
            self.dialog_manager.save_dialog(self.scenario, self.difficulty, self.messages)
            print(f"Dialog saved: {len(self.messages)} messages")
            
            # Анализируем ошибки после завершения диалога
            try:
                import threading
                thread = threading.Thread(target=self._analyze_dialog_sync)
                thread.start()
            except Exception as e:
                print(f"Could not analyze dialog errors: {e}")
    
    async def show_help(self, widget):
        if not self.messages or len(self.messages) <= 1: # Проверяем, есть ли сообщения кроме системного
            self.app.main_window.info_dialog(
                "Информация",
                "Подсказка доступна после начала диалога (хотя бы одна реплика AI)."
            )
            return

        if self.max_hints != float('inf') and self.hint_count >= self.max_hints:
            self.app.main_window.info_dialog(
                "Информация",
                "Вы использовали все доступные подсказки для этого уровня сложности."
            )
            return
        
        # Создаем HelpDialog если его еще нет
        if self.help_dialog is None:
            self.help_dialog = HelpDialog(self.app, self) # Передаем self.app и self (ChatScreen)

        # Уменьшаем счетчик подсказок только если это новый запрос (не из кэша)
        # Это более сложная логика, так как show_help_dialog теперь сама решает, кэш или нет.
        # Мы можем проверить, был ли контент сгенерирован заново.
        # Простой способ: всегда уменьшать, если только кэш не был использован ПРЯМО СЕЙЧАС.
        # Но это сложно отследить извне. 
        # Более надежно: уменьшать счетчик только при *первом* успешном показе окна подсказки
        # для текущего состояния диалога. 
        # Или, как сейчас, уменьшать всегда, а кэширование просто предотвращает повторный API call.
        # Решим пока уменьшать всегда при вызове, если лимит не исчерпан.
        # Логика кэширования в HelpDialog предотвратит повторную *трату* ресурса OpenAI,
        # но пользователь все равно "активировал" подсказку.

        # Проверка, был ли использован кэш для текущего вызова
        # Это потребует от HelpDialog возвращать информацию, был ли использован кэш
        # или изменения состояния, которое можно проверить здесь.
        # Пока что, для простоты, уменьшим счетчик, если он не бесконечен,
        # подразумевая, что нажатие кнопки "Помощь" является намерением использовать подсказку.
        # Кэш внутри HelpDialog оптимизирует только API вызовы.

        # Чтобы подсказка "не тратилась" при показе из кэша, нужно изменить логику подсчета.
        # Сделаем так: HelpDialog будет отвечать, был ли контент новым.

        # Передаем Verantwortung за подсчет подсказок в HelpDialog
        # help_shown_successfully = await self.help_dialog.show_help_dialog(self.hint_count, self.max_hints)
        # 
        # if help_shown_successfully:
        #    if self.max_hints != float('inf') and self.help_dialog.was_new_content_generated:
        #        self.hint_count += 1
        #        self.update_help_button_label()

        # Пока что упрощенная логика: если окно показывается, и подсказки не бесконечны, считаем использованной.
        # Если окно уже открыто (второй клик), то show_help_dialog внутри себя использует кэш.

        # await self.help_dialog.show_help_dialog()

        # Если подсказка была успешно показана (т.е. не было ошибки или отказа из-за лимита)
        # и если это была генерация нового контента (не из кэша)
        # И если подсказки не бесконечны
        # То увеличиваем счетчик.
        # Это требует от show_help_dialog понимания, был ли контент новым.
        # Внесем это изменение в help_system.py
        help_dialog_shown = await self.help_dialog.show_help_dialog()

        if help_dialog_shown:
            if self.help_dialog.was_new_content_generated and self.max_hints != float('inf'):
                self.hint_count += 1
                self.update_help_button_label()
        else:
            # Если диалог помощи не был показан (например, из-за ошибки генерации),
            # можно добавить обработку этого случая, если необходимо.
            print("Help dialog was not shown (e.g. generation error).")

    def update_help_button_label(self):
        """Обновляет текст на кнопке помощи с текущим количеством подсказок."""
        # Найдем кнопку помощи. Это может потребовать хранения ссылки на нее.
        # Предположим, что input_box и его дети доступны или могут быть найдены.
        # Для простоты, пока не будем реализовывать динамическое обновление текста кнопки,
        # так как это потребует рефакторинга build метода для сохранения ссылок на виджеты.
        # Оставим это для будущего улучшения, если потребуется.
        # Пока что текст кнопки будет обновляться только при пересоздании экрана чата.
        # Чтобы это работало корректно, нужно будет хранить ссылку на help_button.
        # В методе build, где создается help_button:
        # self.help_button = toga.Button(...)
        # И затем здесь:
        # if hasattr(self, 'help_button'):
        #    label = f"Помощь ({self.max_hints - self.hint_count if self.max_hints != float('inf') else '∞'})"
        #    self.help_button.label = label
        if hasattr(self, 'help_button'):
            label = f"Помощь ({self.max_hints - self.hint_count if self.max_hints != float('inf') else '∞'})"
            self.help_button.text = label # Используем .text для Toga Button

    def go_back(self, widget):
        # Сохраняем диалог перед выходом
        self.save_dialog_on_completion()
        self.app.show_start_screen()


class EnglishLearningApp(toga.App):
    def startup(self):
        self.main_window = toga.MainWindow(title=self.formal_name)
        self.dialog_manager = DialogManager()
        self.show_start_screen()
        self.main_window.show()
    
    def show_start_screen(self):
        self.start_screen = StartScreen(self)
        self.main_window.content = self.start_screen.build()
    
    def show_chat_screen(self, scenario_key, scenario, difficulty):
        self.chat_screen = ChatScreen(self, scenario_key, scenario, difficulty)
        self.main_window.content = self.chat_screen.build()


def main():
    return EnglishLearningApp(
        "Английские сценки", 
        "org.example.english_chat"
    )


if __name__ == '__main__':
    app = main()
    app.main_loop()