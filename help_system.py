import toga
from toga.style import Pack
from openai import OpenAI
import asyncio
from config import OPENAI_API_KEY
from dialog_manager import DialogManager

class HelpSystem:
    def __init__(self, client):
        self.client = client
        self.dialog_manager = DialogManager()
        
    async def generate_help_content(self, messages, scenario, difficulty):
        """Генерирует содержимое для подсказок (перевод и варианты ответов) 
           на основе текущего контекста диалога.
        """
        
        last_ai_message_content = "Сообщений от AI для перевода пока нет."
        for i in range(len(messages) - 1, -1, -1):
            if messages[i]["role"] == "assistant":
                last_ai_message_content = messages[i]["content"]
                break

        recent_dialog_messages = []
        if len(messages) > 1:
            for msg in messages[1:]:
                role = "Вы" if msg["role"] == "user" else "AI"
                recent_dialog_messages.append(f"{role}: {msg['content']}")
        context_for_prompt = "\n".join(recent_dialog_messages[-4:])
        
        help_prompt = f"""
        Сценарий: {scenario}
        Уровень сложности: {difficulty}
        Последние сообщения диалога (для общего понимания контекста):
        {context_for_prompt}

        Сообщение от AI, которое нужно перевести на русский язык: "{last_ai_message_content}"
        
        Предоставь помощь пользователю в изучении английского языка в следующем формате:
        
        ПЕРЕВОД: [Переведи на русский язык ТОЛЬКО указанное выше "Сообщение от AI, которое нужно перевести". Если там написано, что сообщений нет, так и укажи.]
        
        ВАРИАНТЫ_ОТВЕТОВ:
        1. [Простой вариант ответа от лица пользователя на английском языке, подходящий к последнему сообщению AI в диалоге]
        2. [Средний по сложности вариант ответа от лица пользователя на английском языке, подходящий к последнему сообщению AI в диалоге]
        3. [Более продвинутый вариант ответа от лица пользователя на английском языке, подходящий к последнему сообщению AI в диалоге]
                
        ВАЖНО: Варианты ответов должны быть ТОЛЬКО на английском языке. Остальное на русском.
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": help_prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Ошибка при генерации основной подсказки: {e}"
    
    def parse_help_content(self, content):
        """Парсит ответ от OpenAI для перевода и вариантов ответов."""
        sections = {
            'translation': '',
            'answer_options': [],
        }
        
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('ПЕРЕВОД:'):
                current_section = 'translation'
                sections['translation'] = line.replace('ПЕРЕВОД:', '').strip()
            elif line.startswith('ВАРИАНТЫ_ОТВЕТОВ:'):
                current_section = 'answer_options'
            elif current_section == 'answer_options' and (line.startswith('1.') or line.startswith('2.') or line.startswith('3.')):
                sections['answer_options'].append(line[2:].strip())
        
        return sections

    async def generate_specific_cultural_context(self, ai_message_content: str, scenario: str, difficulty: str):
        """Генерирует объяснение культурного контекста для конкретного сообщения AI."""
        if not ai_message_content or ai_message_content == "Сообщений от AI для перевода пока нет.":
            return "Нет сообщения от AI для анализа культурного контекста."

        prompt = f"""
        Проанализируй следующее сообщение от AI из диалога на английском языке и подробно объясни ЛЮБЫЕ культурные отсылки, идиомы, упоминания специфических реалий (например, праздников, традиций, еды, социальных норм, этикета, географических названий с культурным значением, известных личностей или событий) или другие неочевидные моменты, которые могут быть сложны для понимания изучающим язык. 
        Будь внимателен даже к мелочам, которые могут иметь культурное значение.
        Если однозначных культурных отсылок нет, кратко укажи, что фраза является стандартной/нейтральной в данном контексте, или объясни, почему определенные элементы (если есть сомнения) могут не являться специфической культурной отсылкой в данном случае. Не пиши просто "НЕТ".
        Ответ дай на русском языке. Если твой ответ получается длинным, старайся разбивать его на абзацы или использовать переносы строк для лучшей читаемости в простом диалоговом окне.

        Сценарий диалога (для общего понимания): {scenario}
        Уровень сложности: {difficulty}

        Сообщение AI для анализа:
        "{ai_message_content}"
        """
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.dialog_manager.save_error(
                "cultural_context_generation_error", 
                str(e),
                {"scenario": scenario, "difficulty": difficulty, "ai_message": ai_message_content}
            )
            return f"Ошибка при генерации культурного контекста: {e}"

    async def generate_specific_grammar_analysis(self, ai_message_content: str, scenario: str, difficulty: str):
        """Генерирует грамматический разбор конкретного сообщения AI."""
        if not ai_message_content or ai_message_content == "Сообщений от AI для перевода пока нет.":
            return "Нет сообщения от AI для грамматического анализа."

        prompt = f"""
        Проанализируй грамматическую структуру следующего сообщения от AI из диалога на английском языке. 
        Объясни основные грамматические конструкции, использованные в сообщении (например, время, залог, порядок слов, использование артиклей, модальных глаголов и т.д.). 
        Постарайся объяснить так, чтобы было понятно изучающему английский язык. Можно представить в виде: "Структура: [краткое описание структуры, например, Subject + Verb (Past Simple) + Object]. Ключевые моменты: [пояснения]".
        Если сообщение очень короткое или грамматически тривиальное, укажи это.
        Ответ дай на русском языке. Если твой ответ получается длинным, старайся разбивать его на абзацы или использовать переносы строк для лучшей читаемости в простом диалоговом окне.

        Сценарий диалога (для общего понимания): {scenario}
        Уровень сложности: {difficulty}

        Сообщение AI для анализа:
        "{ai_message_content}"
        """
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.dialog_manager.save_error(
                "grammar_analysis_generation_error", 
                str(e),
                {"scenario": scenario, "difficulty": difficulty, "ai_message": ai_message_content}
            )
            return f"Ошибка при генерации грамматического анализа: {e}"


class HelpDialog:
    def __init__(self, parent_app, chat_screen):
        self.parent_app = parent_app
        self.chat_screen = chat_screen
        self.help_system = HelpSystem(chat_screen.client)
        self.original_content = None # UI чата
        self.help_screen_content = None # UI основного экрана помощи
        self.current_help_data = None
        self._cached_help_content = None
        self._cached_for_messages_hash = None
        self.was_new_content_generated = False
        
    async def show_help_dialog(self):
        """Создает и показывает диалог с подсказками."""
        print("Attempting to show help dialog...")
        self.was_new_content_generated = False

        # Генерируем хэш текущего состояния сообщений
        current_messages_str = "".join([msg['content'] for msg in self.chat_screen.messages])
        current_messages_hash = hash(current_messages_str)

        # Проверяем, есть ли актуальный кэш
        if self._cached_help_content and self._cached_for_messages_hash == current_messages_hash:
            print("Using cached help content.")
            parsed_help = self.help_system.parse_help_content(self._cached_help_content)
            self.current_help_data = parsed_help
        else:
            print("Generating new help content...")
            # Генерируем содержимое подсказок
            help_content = await self.help_system.generate_help_content(
                self.chat_screen.messages,
                self.chat_screen.scenario,
                self.chat_screen.difficulty
            )
            if "Ошибка при генерации подсказки:" in help_content:
                self.parent_app.main_window.error_dialog("Ошибка Помощи", help_content)
                return False
            
            print(f"Generated help content: {help_content[:100]}...")
            
            # Кэшируем новый контент
            self._cached_help_content = help_content
            self._cached_for_messages_hash = current_messages_hash
            self.was_new_content_generated = True
            
            # Парсим содержимое
            parsed_help = self.help_system.parse_help_content(help_content)
            self.current_help_data = parsed_help
        
        print(f"Parsed help: {parsed_help}")
        
        # Логируем запрос помощи
        self.help_system.dialog_manager.save_help_request(
            "answer_options", 
            "Requested help with answer options", 
            str(parsed_help['answer_options']),
            {"scenario": self.chat_screen.scenario, "difficulty": self.chat_screen.difficulty}
        )
        
        # Создаем UI диалога
        self.create_help_ui(parsed_help)
        return True
    
    def create_help_ui(self, help_data):
        """Создает UI для окна подсказок"""
        print("Creating help UI...")
        
        # Сохраняем текущий контент
        self.original_content = self.parent_app.main_window.content
        
        # Кнопка возврата к чату
        back_to_chat_button = toga.Button(
            "← Вернуться к чату",
            on_press=self.back_to_chat,
            style=Pack(padding=10, background_color="#dc3545", color="#ffffff")
        )
        
        # Заголовок
        title = toga.Label(
            "💡 Помощь по диалогу",
            style=Pack(font_size=18, font_weight="bold", padding=(10, 0, 20, 0))
        )
        
        # Перевод
        translation_text = toga.Label(
            f"🔤 Перевод: {help_data.get('translation', 'Нет перевода')}",
            style=Pack(padding=(0, 0, 15, 0))
        )
        
        # Создаем список элементов для контента
        content_children = [title, translation_text]
        
        # Варианты ответов - кликабельные кнопки
        if help_data.get('answer_options'):
            options_label = toga.Label(
                "💡 Варианты ответов (нажмите, чтобы отправить):",
                style=Pack(font_weight="bold", padding=(0, 0, 10, 0))
            )
            content_children.append(options_label)
            
            for i, option in enumerate(help_data['answer_options'], 1):
                option_button = toga.Button(
                    f"{i}. {option}",
                    on_press=lambda widget, text=option: self.send_answer_option(text),
                    style=Pack(
                        padding=(5, 0),
                        background_color="#28a745",
                        color="#ffffff",
                        flex=1
                    )
                )
                content_children.append(option_button)
            
        # Постоянные кнопки для Культурного контекста и Грамматического разбора
        cultural_context_button = toga.Button(
            "🌍 Культурный контекст",
            on_press=self.request_cultural_context, # Новый обработчик
            style=Pack(padding=(15, 5, 5, 5), background_color="#17a2b8", color="#ffffff", flex=1)
        )
        
        grammar_analysis_button = toga.Button(
            "📚 Грамматический разбор",
            on_press=self.request_grammar_analysis, # Новый обработчик
            style=Pack(padding=(5, 5, 15, 5), background_color="#17a2b8", color="#ffffff", flex=1)
        )

        dynamic_info_buttons_box = toga.Box(
            children=[cultural_context_button, grammar_analysis_button],
            style=Pack(direction="row", padding=(10,0))
        )
        content_children.append(dynamic_info_buttons_box)

        # Кнопка "Спросить Помощника"
        ask_assistant_button = toga.Button(
            "💬 Спросить Помощника",
            on_press=self.show_assistant_dialog, 
            style=Pack(padding=(20, 0, 10, 0), background_color="#ffc107", color="#212529", font_weight="bold", flex=1)
        )
        
        content_children.append(ask_assistant_button)
        
        # ScrollContainer для всего содержимого
        scroll_container = toga.ScrollContainer(
            content=toga.Box(
                children=content_children,
                style=Pack(direction="column", padding=20, flex=1)
            ),
            style=Pack(flex=1)
        )
        
        # Основной контейнер помощи
        help_box = toga.Box(
            children=[
                back_to_chat_button,
                scroll_container
            ],
            style=Pack(direction="column", flex=1)
        )
        
        self.help_screen_content = help_box # Сохраняем UI основного экрана помощи
        self.parent_app.main_window.content = self.help_screen_content
        print("Help UI created and set as main window content.")

    async def _ask_assistant_openai(self, question):
        """Отправляет вопрос помощнику OpenAI и возвращает ответ."""
        dialog_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.chat_screen.messages])
        
        prompt = f"""
        Ты — продвинутый ИИ-помощник. Твоя задача — помочь пользователю разобраться с его вопросом или проблемой, связанной с текущим англоязычным диалогом. Предоставляй углубленные и подробные объяснения на русском языке.

        Контекст основного диалога, в котором находится пользователь:
        Событие и роль основного AI-собеседника: "{self.chat_screen.scenario}"
        Уровень сложности диалога: {self.chat_screen.difficulty}

        История основного диалога к текущему моменту:
        {dialog_history}

        Вопрос пользователя к тебе (ИИ-помощнику): "{question}"

        Предоставь развернутый и понятный ответ на вопрос пользователя на русском языке.
        При необходимости, можешь ссылаться на историю диалога для полноты ответа.
        Ответ должен быть готов к отображению в интерфейсе.
        """
        
        try:
            response = await asyncio.to_thread(
                self.help_system.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            answer = response.choices[0].message.content
            self.help_system.dialog_manager.save_help_request(
                "assistant_question", 
                question, 
                answer, 
                {"scenario": self.chat_screen.scenario, "difficulty": self.chat_screen.difficulty, "dialog_history_length": len(self.chat_screen.messages)}
            )
            return answer
        except Exception as e:
            error_message = f"Ошибка при запросе к Помощнику: {e}"
            self.help_system.dialog_manager.save_error(
                "assistant_api_error", 
                str(e),
                {"scenario": self.chat_screen.scenario, "difficulty": self.chat_screen.difficulty, "question": question}
            )
            return error_message

    async def handle_ask_assistant(self, widget):
        """Обрабатывает запрос к помощнику."""
        question = self.assistant_input.value.strip()
        if not question:
            self.parent_app.main_window.info_dialog("Помощник", "Пожалуйста, введите ваш вопрос.")
            return

        self.assistant_input.value = "" # Очищаем поле ввода
        # Показываем индикатор загрузки
        self.assistant_response_area.value = "Пожалуйста, подождите, Помощник обрабатывает ваш запрос..."
        
        # Запускаем асинхронный запрос
        answer = await self._ask_assistant_openai(question)
        self.assistant_response_area.value = answer

    async def request_cultural_context(self, widget):
        """Запрашивает и отображает культурный контекст для последнего сообщения AI."""
        last_ai_message = None
        for i in range(len(self.chat_screen.messages) - 1, -1, -1):
            if self.chat_screen.messages[i]["role"] == "assistant":
                last_ai_message = self.chat_screen.messages[i]["content"]
                break
        
        if not last_ai_message:
            self.parent_app.main_window.info_dialog("Информация", "Нет сообщений от AI для анализа.")
            return

        # Показываем индикатор загрузки (опционально, если будет долго)
        # self.parent_app.main_window.info_dialog("Загрузка", "Анализирую культурный контекст...")
        
        explanation = await self.help_system.generate_specific_cultural_context(
            last_ai_message, self.chat_screen.scenario, self.chat_screen.difficulty
        )
        
        self.help_system.dialog_manager.save_help_request(
            "dynamic_cultural_context", 
            f"Requested cultural context for AI message: {last_ai_message[:50]}...", 
            explanation,
            {"scenario": self.chat_screen.scenario, "difficulty": self.chat_screen.difficulty}
        )
        self.parent_app.main_window.info_dialog("🌍 Культурный контекст", explanation)

    async def request_grammar_analysis(self, widget):
        """Запрашивает и отображает грамматический анализ последнего сообщения AI."""
        last_ai_message = None
        for i in range(len(self.chat_screen.messages) - 1, -1, -1):
            if self.chat_screen.messages[i]["role"] == "assistant":
                last_ai_message = self.chat_screen.messages[i]["content"]
                break
        
        if not last_ai_message:
            self.parent_app.main_window.info_dialog("Информация", "Нет сообщений от AI для анализа.")
            return

        analysis = await self.help_system.generate_specific_grammar_analysis(
            last_ai_message, self.chat_screen.scenario, self.chat_screen.difficulty
        )
        
        self.help_system.dialog_manager.save_help_request(
            "dynamic_grammar_analysis", 
            f"Requested grammar analysis for AI message: {last_ai_message[:50]}...", 
            analysis,
            {"scenario": self.chat_screen.scenario, "difficulty": self.chat_screen.difficulty}
        )
        # Специальное логирование для системы упражнений
        self.help_system.dialog_manager.save_error(
            error_type="grammar_topic_requested", # Используем тип ошибки для простоты или можно создать новый тип лога
            error_message=f"User requested grammar analysis for: '{last_ai_message}'",
            context={"scenario": self.chat_screen.scenario, 
                     "difficulty": self.chat_screen.difficulty, 
                     "ai_message": last_ai_message,
                     "grammar_analysis_provided": analysis}
        )
        self.parent_app.main_window.info_dialog("📚 Грамматический разбор", analysis)
    
    def show_assistant_dialog(self, widget=None):
        """Показывает UI для взаимодействия с Помощником."""
        print("Showing assistant dialog...")
        # self.original_content уже должен быть сохранен из show_help_dialog
        
        back_to_help_button = toga.Button(
            "← Назад к подсказкам",
            on_press=self.back_to_help,
            style=Pack(padding=10, background_color="#007bff", color="#ffffff")
        )

        title = toga.Label(
            "💬 Задать вопрос Помощнику",
            style=Pack(font_size=18, font_weight="bold", padding=(10,0,15,0))
        )

        instruction = toga.Label(
            "Задайте ваш вопрос о текущем диалоге, попросите объяснить что-то подробнее или помочь с ответом.",
            style=Pack(padding=(0,0,15,0))
        )

        self.assistant_input = toga.TextInput(
            placeholder="Введите ваш вопрос здесь...",
            style=Pack(padding=(0,0,10,0), height=80) # Увеличим немного высоту
        )

        ask_button = toga.Button(
            "Отправить вопрос Помощнику",
            on_press=self.handle_ask_assistant, # Используем новую async-совместимую обертку
            style=Pack(padding=10, background_color="#28a745", color="#ffffff")
        )

        self.assistant_response_area = toga.MultilineTextInput(
            readonly=True,
            placeholder="Ответ Помощника появится здесь...",
            style=Pack(flex=1, padding=(10,0,0,0))
        )
        
        assistant_box_content = toga.Box(
            children=[
                title, 
                instruction, 
                self.assistant_input, 
                ask_button, 
                self.assistant_response_area
            ],
            style=Pack(direction="column", padding=20, flex=1)
        )

        assistant_scroll = toga.ScrollContainer(
            content=assistant_box_content,
            style=Pack(flex=1)
        )
        
        assistant_main_box = toga.Box(
            children=[back_to_help_button, assistant_scroll],
            style=Pack(direction="column", flex=1)
        )

        self.parent_app.main_window.content = assistant_main_box
        print("Assistant UI created and set.")

    def send_answer_option(self, answer_text):
        """Отправляет выбранный вариант ответа в чат"""
        print(f"Sending answer option: {answer_text}")
        
        # Логируем использование варианта ответа
        self.help_system.dialog_manager.save_help_request(
            "answer_used", 
            answer_text, 
            "User selected this answer option",
            {"scenario": self.chat_screen.scenario, "difficulty": self.chat_screen.difficulty}
        )
        
        # Возвращаемся к чату
        self.back_to_chat(None)
        
        # Устанавливаем текст в поле ввода
        self.chat_screen.user_input.value = answer_text
        # Имитируем нажатие кнопки отправки - создаем задачу корутины
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self.chat_screen.send_message(None))
        except RuntimeError:
            # Если нет активного цикла, создаем новый
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.chat_screen.send_message(None))
            finally:
                loop.close()
    
    def back_to_help(self, widget):
        """Возвращает к основному окну подсказок"""
        if self.help_screen_content:
            self.parent_app.main_window.content = self.help_screen_content
            print("Returned to main help screen.")
        elif self.current_help_data: # Fallback, если help_screen_content почему-то None
            print("Fallback: Recreating help UI for back_to_help")
            self.create_help_ui(self.current_help_data)
        else:
            # Если совсем нечего показывать, возвращаемся в чат
            print("Error/Warning: No help content to return to, going back to chat.")
            self.back_to_chat(None)
    
    def back_to_chat(self, widget):
        """Возвращает к чату"""
        if self.original_content:
            self.parent_app.main_window.content = self.original_content
    
    def close_dialog(self, widget):
        """Закрывает диалог подсказок и возвращает к чату"""
        self.back_to_chat(widget) 