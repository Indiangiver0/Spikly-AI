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
        """Генерирует содержимое для подсказок на основе текущего контекста диалога"""
        
        # Ищем последнее сообщение от AI для перевода
        last_ai_message_content = "Сообщений от AI для перевода пока нет."
        for i in range(len(messages) - 1, -1, -1):
            if messages[i]["role"] == "assistant":
                last_ai_message_content = messages[i]["content"]
                break

        # Получаем последние несколько сообщений для общего контекста (исключая system prompt)
        recent_dialog_messages = []
        if len(messages) > 1: # Если есть что-то кроме системного сообщения
            for msg in messages[1:]: # Пропускаем системное сообщение messages[0]
                role = "Вы" if msg["role"] == "user" else "AI"
                recent_dialog_messages.append(f"{role}: {msg['content']}")
        
        context_for_prompt = "\n".join(recent_dialog_messages[-4:]) # Последние 4 реплики диалога
        
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
        
        КУЛЬТУРНЫЙ_КОНТЕКСТ: [Если в ПОСЛЕДНЕМ СООБЩЕНИИ AI или в текущем контексте диалога есть культурные отсылки, идиомы или неочевидные моменты - объясни их. Если нет особых культурных моментов - напиши "НЕТ"]
        
        ГРАММАТИКА: [Если в ПОСЛЕДНЕМ СООБЩЕНИИ AI есть важные грамматические конструкции для изучения - объясни их. Если грамматика простая и очевидная - напиши "НЕТ"]
        
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
            return f"Ошибка при генерации подсказки: {e}"
    
    def parse_help_content(self, content):
        """Парсит ответ от OpenAI и возвращает структурированные данные"""
        sections = {
            'translation': '',
            'answer_options': [],
            'cultural_context': '',
            'grammar': '',
            'show_cultural': True,
            'show_grammar': True
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
            elif line.startswith('КУЛЬТУРНЫЙ_КОНТЕКСТ:'):
                current_section = 'cultural_context'
                context_text = line.replace('КУЛЬТУРНЫЙ_КОНТЕКСТ:', '').strip()
                sections['cultural_context'] = context_text
                sections['show_cultural'] = context_text.upper() != 'НЕТ'
            elif line.startswith('ГРАММАТИКА:'):
                current_section = 'grammar'
                grammar_text = line.replace('ГРАММАТИКА:', '').strip()
                sections['grammar'] = grammar_text
                sections['show_grammar'] = grammar_text.upper() != 'НЕТ'
            elif current_section == 'answer_options' and (line.startswith('1.') or line.startswith('2.') or line.startswith('3.')):
                sections['answer_options'].append(line[2:].strip())
        
        return sections


class HelpDialog:
    def __init__(self, parent_app, chat_screen):
        self.parent_app = parent_app
        self.chat_screen = chat_screen
        self.help_system = HelpSystem(chat_screen.client)
        self.original_content = None
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

        # Кнопки для показа/скрытия культурного контекста и грамматики
        action_buttons_box_children = []

        if help_data.get('show_cultural', True):
            cultural_context_text = toga.Label(
                f"🌍 Культурный контекст: {help_data.get('cultural_context', 'Нет данных')}",
                style=Pack(padding=(15, 0, 10, 0))
            )
            content_children.append(cultural_context_text)
        else:
            show_cultural_button = toga.Button(
                "📖 Показать культурный контекст",
                on_press=self.show_cultural_context,
                style=Pack(padding=(5,5), background_color="#17a2b8", color="#ffffff", flex=1)
            )
            action_buttons_box_children.append(show_cultural_button)

        if help_data.get('show_grammar', True):
            grammar_text = toga.Label(
                f"📚 Грамматика: {help_data.get('grammar', 'Нет данных')}",
                style=Pack(padding=(10, 0, 20, 0))
            )
            content_children.append(grammar_text)
        else:
            show_grammar_button = toga.Button(
                "✍️ Показать грамматические советы",
                on_press=self.show_grammar_tips,
                style=Pack(padding=(5,5), background_color="#17a2b8", color="#ffffff", flex=1)
            )
            action_buttons_box_children.append(show_grammar_button)
        
        if action_buttons_box_children:
            action_buttons_box = toga.Box(
                children=action_buttons_box_children,
                style=Pack(direction="row" if len(action_buttons_box_children) > 1 else "column", padding=(10,0))
            )
            content_children.append(action_buttons_box)

        # Кнопка "Спросить Помощника"
        ask_assistant_button = toga.Button(
            "💬 Спросить Помощника",
            on_press=self.show_assistant_dialog, # Изменено на прямой вызов
            style=Pack(padding=(20, 0, 5, 0), background_color="#ffc107", color="#212529", font_weight="bold", flex=1)
        )
        
        # Кнопка закрытия помощи
        close_help_button = toga.Button(
            "Закрыть помощь",
            on_press=self.back_to_chat, # Используем back_to_chat для простоты
            style=Pack(padding=(5,0,10,0), background_color="#6c757d", color="#ffffff", flex=1)
        )

        buttons_box = toga.Box(
            children=[ask_assistant_button, close_help_button],
            style=Pack(direction="row", padding=(0,0))
        )
        content_children.append(buttons_box)
        
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
        
        self.parent_app.main_window.content = help_box
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

    def show_cultural_context(self, widget):
        """Показывает дополнительную информацию о культурном контексте"""
        # Простая заглушка
        self.parent_app.main_window.info_dialog("Культурный контекст", "Функция в разработке")
    
    def show_grammar_tips(self, widget):
        """Показывает дополнительные грамматические советы"""
        # Простая заглушка
        self.parent_app.main_window.info_dialog("Грамматические советы", "Функция в разработке")
    
    def show_assistant_dialog(self, widget=None): # widget=None, чтобы можно было вызывать без sender
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
        # Простая заглушка - просто показываем кэшированные данные
        if self.current_help_data:
            self.create_help_ui(self.current_help_data)
    
    def back_to_chat(self, widget):
        """Возвращает к чату"""
        if self.original_content:
            self.parent_app.main_window.content = self.original_content
    
    def close_dialog(self, widget):
        """Закрывает диалог подсказок и возвращает к чату"""
        self.back_to_chat(widget) 