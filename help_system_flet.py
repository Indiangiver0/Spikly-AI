import flet as ft
import asyncio
from openai import OpenAI
from config import OPENAI_API_KEY

class HelpSystem:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
    async def generate_help_content(self, last_messages, scenario, difficulty):
        """Генерирует контент для помощи"""
        # Формируем контекст из последних сообщений
        context = ""
        last_ai_message_content = ""
        
        for msg in last_messages[-6:]:
            role = "Пользователь" if msg["role"] == "user" else "AI"
            context += f"{role}: {msg['content']}\n"
            if msg["role"] == "assistant":
                last_ai_message_content = msg['content']
        
        if not last_ai_message_content:
            return None
            
        help_prompt = f"""
        Контекст диалога:
        Сценарий: {scenario}
        Сложность: {difficulty}
        Последние сообщения:
        {context}
        
        Сообщение от AI для перевода: "{last_ai_message_content}"
        
        Предоставь помощь в формате:
        
        ПЕРЕВОД:
        [Перевод последнего сообщения AI на русский язык]
        
        ВАРИАНТЫ_ОТВЕТОВ:
        1. [Простой ответ на английском]
        2. [Средний ответ на английском] 
        3. [Продвинутый ответ на английском]
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": help_prompt}],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            return self.parse_help_content(content)
            
        except Exception as e:
            return {"error": f"Ошибка генерации помощи: {e}"}
    
    def parse_help_content(self, content):
        """Парсит контент помощи"""
        result = {
            "translation": "",
            "answer_options": []
        }
        
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("ПЕРЕВОД:"):
                current_section = "translation"
                result["translation"] = line.replace("ПЕРЕВОД:", "").strip()
            elif line.startswith("ВАРИАНТЫ_ОТВЕТОВ:"):
                current_section = "answers"
            elif current_section == "translation" and line:
                result["translation"] += " " + line
            elif current_section == "answers" and line and (line.startswith("1.") or line.startswith("2.") or line.startswith("3.")):
                answer = line[2:].strip()
                if answer:
                    result["answer_options"].append(answer)
        
        return result
    
    async def generate_cultural_context(self, ai_message, scenario, difficulty):
        """Генерирует культурный контекст"""
        prompt = f"""
        Проанализируй это сообщение от AI: "{ai_message}"
        Сценарий: {scenario}
        
        Найди и объясни культурные особенности, идиомы, традиции или национальные особенности.
        Если культурного контекста нет, объясни почему.
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Ошибка: {e}"
    
    async def generate_grammar_analysis(self, ai_message, scenario, difficulty):
        """Генерирует грамматический анализ"""
        prompt = f"""
        Проанализируй грамматику в этом сообщении: "{ai_message}"
        Объясни структуру предложений, времена, артикли и другие грамматические особенности.
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Ошибка: {e}"

class HelpDialog:
    def __init__(self, page: ft.Page, chat_screen):
        self.page = page
        self.chat_screen = chat_screen
        self.help_system = HelpSystem()
        self.current_help_data = None
        
    async def show_help_dialog(self):
        """Показывает диалог помощи"""
        if not self.chat_screen.messages or len(self.chat_screen.messages) <= 1:
            await self.show_info_dialog("ℹ️ Информация", 
                "Подсказка доступна после начала диалога")
            return False
            
        if (self.chat_screen.max_hints != float('inf') and 
            self.chat_screen.hint_count >= self.chat_screen.max_hints):
            await self.show_info_dialog("⚠️ Лимит", 
                "Вы использовали все доступные подсказки для этого уровня сложности")
            return False
        
        # Генерируем помощь
        loading_dialog = self.create_loading_dialog()
        self.page.dialog = loading_dialog
        loading_dialog.open = True
        self.page.update()
        
        try:
            self.current_help_data = await self.help_system.generate_help_content(
                self.chat_screen.messages,
                self.chat_screen.scenario,
                self.chat_screen.difficulty
            )
            
            loading_dialog.open = False
            
            if self.current_help_data and "error" not in self.current_help_data:
                help_dialog = self.create_help_dialog()
                self.page.dialog = help_dialog
                help_dialog.open = True
                help_dialog.on_dismiss = lambda e: self.chat_screen._update_hints_display()
                self.page.update()
                
                # Увеличиваем счетчик подсказок, если помощь была успешно СГЕНЕРИРОВАНА и ПОКАЗАНА
                if self.chat_screen.max_hints != float('inf'):
                    self.chat_screen.hint_count += 1
                    
                return True
            else:
                await self.show_info_dialog("❌ Ошибка", 
                    self.current_help_data.get("error", "Неизвестная ошибка"))
                return False
                
        except Exception as e:
            loading_dialog.open = False
            await self.show_info_dialog("❌ Ошибка", f"Ошибка генерации: {e}")
            return False
    
    def create_loading_dialog(self):
        """Создает диалог загрузки"""
        return ft.AlertDialog(
            title=ft.Text("🔄 Генерация помощи..."),
            content=ft.Container(
                content=ft.Column([
                    ft.ProgressRing(),
                    ft.Text("Анализируем диалог и готовим подсказки...")
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                height=100
            ),
            modal=True
        )
    
    def create_help_dialog(self):
        """Создает основной диалог помощи"""
        # Рассчитываем ширину диалога (например, 80% ширины страницы, но не более 700px и не менее 500px)
        dialog_width = min(max(self.page.width * 0.8 if self.page.width else 600, 500), 700)

        # Перевод
        translation_text = ft.Text(
            self.current_help_data.get("translation", "Перевод недоступен"),
            size=16,
            color="#2E7D32",
            weight=ft.FontWeight.W_500
        )
        
        translation_container = ft.Container(
            content=ft.Column([
                ft.Text("🔤 Перевод:", size=18, weight=ft.FontWeight.BOLD),
                translation_text
            ]),
            bgcolor="#E8F5E8",
            border_radius=10,
            padding=ft.padding.all(15),
            margin=ft.margin.only(bottom=15)
        )
        
        # Варианты ответов
        answer_buttons = []
        for i, answer in enumerate(self.current_help_data.get("answer_options", [])[:3], 1):
            button = ft.Container(
                content=ft.Text(
                    f"{i}. {answer}",
                    size=14,
                    color=ft.Colors.WHITE,
                    text_align=ft.TextAlign.LEFT
                ),
                bgcolor="#25D366",
                border_radius=8,
                padding=ft.padding.all(12),
                margin=ft.margin.only(bottom=8),
                ink=True,
                on_click=lambda e, ans=answer: self.send_answer_to_chat(ans)
            )
            answer_buttons.append(button)
        
        answers_container = ft.Container(
            content=ft.Column([
                ft.Text("💬 Варианты ответов:", size=18, weight=ft.FontWeight.BOLD),
                ft.Column(answer_buttons)
            ]),
            bgcolor="#E3F2FD",
            border_radius=10,
            padding=ft.padding.all(15),
            margin=ft.margin.only(bottom=15)
        )
        
        # Кнопки дополнительных функций
        cultural_btn = ft.ElevatedButton(
            "🌍 Культурный контекст",
            bgcolor="#FF9800",
            color=ft.Colors.WHITE,
            on_click=self.show_cultural_context
        )
        
        grammar_btn = ft.ElevatedButton(
            "📚 Грамматический анализ",
            bgcolor="#9C27B0",
            color=ft.Colors.WHITE,
            on_click=self.show_grammar_analysis
        )
        
        assistant_btn = ft.ElevatedButton(
            "🤖 Спросить Помощника",
            bgcolor="#2196F3",
            color=ft.Colors.WHITE,
            on_click=self.show_assistant_dialog
        )
        
        action_buttons = ft.Row([
            cultural_btn,
            grammar_btn,
            assistant_btn
        ], alignment=ft.MainAxisAlignment.SPACE_AROUND)
        
        # Основной контент
        main_column_content = ft.Column(
            [
                translation_container,
                answers_container,
                ft.Container(height=10), # Небольшой отступ
                ft.Row(
                    [cultural_btn, grammar_btn], 
                    alignment=ft.MainAxisAlignment.SPACE_AROUND, # Равномерное распределение
                    # Добавим возможность переноса кнопок, если они не помещаются
                    wrap=True, 
                    spacing=10 # Отступ между кнопками, если они перенесутся
                ),
                ft.Container(height=20), # Отступ побольше
                assistant_btn # Кнопка "Спросить Помощника" будет последней, на всю ширину
            ],
            # Контейнер для основного содержимого будет иметь прокрутку, если не помещается
            scroll=ft.ScrollMode.ADAPTIVE,
            # Ограничим максимальную высоту, чтобы диалог не был слишком длинным
            # Например, 70% высоты страницы
            height=self.page.height * 0.7 if self.page.height else 450 
        )

        return ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.icons.LIGHTBULB_OUTLINE, color="#FFC107"),
                ft.Text("💡 Помощь", weight=ft.FontWeight.BOLD)
            ]),
            # Оборачиваем main_column_content в контейнер с заданной шириной
            content=ft.Container(content=main_column_content, width=dialog_width),
            actions=[
                ft.TextButton("Закрыть", on_click=self.close_help_dialog, style=ft.ButtonStyle(color=ft.colors.RED_ACCENT_700))
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=15),
            content_padding=ft.padding.all(20),
            title_padding=ft.padding.only(left=20, top=20, right=20, bottom=10),
            actions_padding=ft.padding.only(right=20, bottom=10)
        )
    
    def send_answer_to_chat(self, answer):
        """Отправляет выбранный ответ в чат"""
        self.close_help_dialog(None)
        # Заполняем поле ввода и отправляем
        self.chat_screen.message_input.value = answer
        asyncio.create_task(self.chat_screen.send_message(None))
    
    async def show_cultural_context(self, e):
        """Показывает культурный контекст"""
        last_ai_message = ""
        for msg in reversed(self.chat_screen.messages):
            if msg["role"] == "assistant":
                last_ai_message = msg["content"]
                break
        
        if not last_ai_message:
            await self.show_info_dialog("ℹ️ Информация", "Нет сообщения AI для анализа")
            return
        
        loading = self.create_loading_dialog()
        self.page.dialog = loading
        loading.open = True
        self.page.update()
        
        try:
            context = await self.help_system.generate_cultural_context(
                last_ai_message, 
                self.chat_screen.scenario, 
                self.chat_screen.difficulty
            )
            loading.open = False
            await self.show_info_dialog("🌍 Культурный контекст", context)
        except Exception as ex:
            loading.open = False
            await self.show_info_dialog("❌ Ошибка", f"Ошибка анализа: {ex}")
    
    async def show_grammar_analysis(self, e):
        """Показывает грамматический анализ"""
        last_ai_message = ""
        for msg in reversed(self.chat_screen.messages):
            if msg["role"] == "assistant":
                last_ai_message = msg["content"]
                break
        
        if not last_ai_message:
            await self.show_info_dialog("ℹ️ Информация", "Нет сообщения AI для анализа")
            return
        
        loading = self.create_loading_dialog()
        self.page.dialog = loading
        loading.open = True
        self.page.update()
        
        try:
            analysis = await self.help_system.generate_grammar_analysis(
                last_ai_message, 
                self.chat_screen.scenario, 
                self.chat_screen.difficulty
            )
            loading.open = False
            await self.show_info_dialog("📚 Грамматический анализ", analysis)
        except Exception as ex:
            loading.open = False
            await self.show_info_dialog("❌ Ошибка", f"Ошибка анализа: {ex}")
    
    def show_assistant_dialog(self, e):
        """Показывает диалог помощника"""
        question_field = ft.TextField(
            hint_text="Задайте ваш вопрос помощнику...",
            multiline=True,
            min_lines=3,
            max_lines=5,
            border_radius=10
        )
        
        async def ask_assistant(e):
            question = question_field.value.strip()
            if not question:
                return
            
            loading = self.create_loading_dialog()
            self.page.dialog = loading
            loading.open = True
            self.page.update()
            
            try:
                prompt = f"""
                Ты помощник по изучению английского языка. 
                Контекст: {self.chat_screen.scenario}
                Сложность: {self.chat_screen.difficulty}
                
                Вопрос пользователя: {question}
                
                Дай подробный и понятный ответ на русском языке.
                """
                
                response = await asyncio.to_thread(
                    self.help_system.client.chat.completions.create,
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                
                answer = response.choices[0].message.content
                loading.open = False
                await self.show_info_dialog("🤖 Ответ помощника", answer)
                
            except Exception as ex:
                loading.open = False
                await self.show_info_dialog("❌ Ошибка", f"Ошибка: {ex}")
        
        assistant_dialog = ft.AlertDialog(
            title=ft.Text("🤖 Помощник", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Задайте любой вопрос по текущему диалогу:"),
                    question_field
                ]),
                width=400,
                height=200
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.close_dialog(assistant_dialog)),
                ft.ElevatedButton("Спросить", on_click=ask_assistant)
            ]
        )
        
        self.page.dialog = assistant_dialog
        assistant_dialog.open = True
        self.page.update()
    
    async def show_info_dialog(self, title, content):
        """Показывает информационный диалог"""
        info_dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(content, selectable=True),
            actions=[ft.TextButton("OK", on_click=lambda _: self.close_dialog(info_dialog))]
        )
        self.page.dialog = info_dialog
        info_dialog.open = True
        self.page.update()
    
    def close_help_dialog(self, e):
        """Закрывает диалог помощи"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
    
    def close_dialog(self, dialog):
        """Закрывает указанный диалог"""
        dialog.open = False
        self.page.update() 