import flet as ft
import asyncio
from openai import OpenAI
from config import OPENAI_API_KEY
from templates import templates
from dialog_manager import DialogManager
from language_filter import LanguageFilter
from prompts import get_system_prompt
from help_system_flet import HelpDialog

class EnglishLearningApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.dialog_manager = DialogManager()
        
        # Настройка страницы
        self.page.title = "Английские сценки"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window.width = 800
        self.page.window.height = 600
        self.page.window.resizable = True
        self.page.bgcolor = "#F5F5F5"
        
        # Состояние приложения
        self.current_screen = "start"
        self.chat_screen = None
        
        # Показываем стартовый экран
        self.show_start_screen()
    
    def show_start_screen(self):
        """Показывает стартовый экран с выбором сценария и сложности"""
        self.current_screen = "start"
        
        # Заголовок
        title = ft.Text(
            "🎭 Английские сценки",
            size=36,
            weight=ft.FontWeight.BOLD,
            color="#2E7D32",
            text_align=ft.TextAlign.CENTER
        )
        
        subtitle = ft.Text(
            "Изучайте английский через реальные диалоги",
            size=18,
            color="#666",
            text_align=ft.TextAlign.CENTER
        )
        
        # Контейнер для выбора сценария
        scenario_label = ft.Text("📋 Выберите сценарий:", size=20, weight=ft.FontWeight.W_500)
        
        scenario_options = []
        for key, value in templates.items():
            scenario_options.append(ft.dropdown.Option(
                key=str(key),
                text=f"{key}. {value['description']}"
            ))
        
        self.scenario_dropdown = ft.Dropdown(
            options=scenario_options,
            hint_text="Выберите сценарий для диалога...",
            bgcolor=ft.Colors.WHITE,
            border_color="#E0E0E0",
            border_radius=15,
            content_padding=ft.padding.all(18),
            text_size=16,
            on_change=self.on_selection_change
        )
        
        # Контейнер для выбора сложности
        difficulty_label = ft.Text("⚡ Выберите сложность:", size=20, weight=ft.FontWeight.W_500)
        
        difficulty_options = [
            ft.dropdown.Option("easy", "🟢 Easy (B1-B2) - Простая лексика, неограниченные подсказки"),
            ft.dropdown.Option("medium", "🟡 Medium (B2-C1) - Средняя сложность, 10-15 подсказок"), 
            ft.dropdown.Option("hard", "🔴 Hard (C1-C2) - Продвинутый уровень, 5 подсказок")
        ]
        
        self.difficulty_dropdown = ft.Dropdown(
            options=difficulty_options,
            hint_text="Выберите уровень сложности...",
            bgcolor=ft.Colors.WHITE,
            border_color="#E0E0E0",
            border_radius=15,
            content_padding=ft.padding.all(18),
            text_size=16,
            on_change=self.on_selection_change
        )
        
        # 🚀 УМНАЯ КНОПКА СТАРТ (неактивная по умолчанию)
        self.start_button = ft.ElevatedButton(
            content=ft.Text(
                "🚀 НАЧАТЬ ДИАЛОГ",
                size=20,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE,
                text_align=ft.TextAlign.CENTER
            ),
            bgcolor="#CCCCCC",  # Серая неактивная
            disabled=True,
            on_click=None,  # Нет обработчика
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=25),
                padding=ft.padding.symmetric(horizontal=40, vertical=25),
                animation_duration=300,
                shadow_color=ft.Colors.with_opacity(0.20, ft.Colors.BLACK),
                elevation=2
            ),
            width=350,
            height=80
        )
        
        # Основной контент без серого поля
        main_content = ft.Column([
            ft.Container(height=50),
            title,
            ft.Container(height=10),
            subtitle,
            ft.Container(height=60),
            scenario_label,
            ft.Container(height=15),
            self.scenario_dropdown,
            ft.Container(height=40),
            difficulty_label,
            ft.Container(height=15),
            self.difficulty_dropdown,
            ft.Container(height=50),
            self.start_button,
            ft.Container(height=50),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        # Очищаем страницу и добавляем контент БЕЗ серого поля
        self.page.controls.clear()
        self.page.add(main_content)
        self.page.update()
    
    def on_selection_change(self, e):
        """Обработчик изменения выбора - активирует кнопку если все выбрано"""
        # Проверяем выбраны ли и сценарий и сложность
        if self.scenario_dropdown.value and self.difficulty_dropdown.value:
            # Активируем кнопку - делаем яркой и кликабельной
            self.start_button.bgcolor = "#25D366"  # Яркий зеленый
            self.start_button.disabled = False  # Можно кликать
            self.start_button.on_click = self.start_dialog  # Добавляем обработчик
            self.start_button.style.shadow_color = ft.Colors.with_opacity(0.40, ft.Colors.BLACK)
            self.start_button.style.elevation = 8
        else:
            # Деактивируем кнопку - делаем серой
            self.start_button.bgcolor = "#CCCCCC"  # Серая
            self.start_button.disabled = True  # Не кликается
            self.start_button.on_click = None  # Убираем обработчик
            self.start_button.style.shadow_color = ft.Colors.with_opacity(0.20, ft.Colors.BLACK)
            self.start_button.style.elevation = 2
        
        self.page.update()
    
    def start_dialog(self, e):
        """Обработчик начала диалога"""
        if not self.scenario_dropdown.value or not self.difficulty_dropdown.value:
            return  # Не должно произойти, но на всякий случай
        
        # Получаем выбранные значения
        scenario_key = int(self.scenario_dropdown.value)
        selected_template = templates[scenario_key]
        scenario_text = selected_template["description"]
        difficulty = self.difficulty_dropdown.value
        
        # Переходим к чату
        self.show_chat_screen(scenario_key, scenario_text, difficulty)
    
    def close_dialog(self, dialog):
        """Закрывает диалог"""
        dialog.open = False
        self.page.update()
    
    def show_chat_screen(self, scenario_key, scenario, difficulty):
        """Показывает экран чата"""
        self.current_screen = "chat"
        
        # Создаем экран чата
        self.chat_screen = ChatScreen(
            self.page, 
            self, 
            scenario_key, 
            scenario, 
            difficulty,
            self.client,
            self.dialog_manager
        )
        self.chat_screen.show()

class ChatScreen:
    def __init__(self, page: ft.Page, app, scenario_key, scenario, difficulty, client, dialog_manager):
        self.page = page
        self.app = app
        self.scenario_key = scenario_key
        self.scenario = scenario
        self.difficulty = difficulty
        self.client = client
        self.dialog_manager = dialog_manager
        self.language_filter = LanguageFilter()
        
        # Состояние чата
        self.messages = []
        self.hint_count = 0
        self.max_hints = self.get_max_hints()
        
        # UI элементы
        self.chat_container = None
        self.message_input = None
        self.hints_display = ft.Text(weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE) # Для отображения подсказок
        
        # Система помощи
        self.help_dialog = HelpDialog(self.page, self)
        
        # Настройка системного промпта
        self.setup_system_prompt()
    
    def get_max_hints(self):
        """Получает максимальное количество подсказок"""
        hints_map = {
            "easy": float('inf'),
            "medium": 15,
            "hard": 5
        }
        return hints_map.get(self.difficulty, 15)
    
    def setup_system_prompt(self):
        """Настраивает системный промпт"""
        current_template_details = templates.get(self.scenario_key, {})
        aggression_response_for_role = current_template_details.get("aggression_response")

        system_content = get_system_prompt(
            scenario_description=self.scenario, 
            difficulty=self.difficulty,
            role_aggression_response=aggression_response_for_role
        )
        
        self.messages = [{"role": "system", "content": system_content}]
    
    def create_message_bubble(self, text, role):
        """Создает красивый пузырь сообщения - НАСТОЯЩИЙ WhatsApp стиль!"""
        
        # Определяем максимальную ширину пузыря (например, 70% ширины страницы)
        # Учитываем отступы слева/справа для пузыря (margin_left, margin_right)
        # и внутренние отступы (padding)
        bubble_max_width = self.page.window.width * 0.7 if self.page.window.width else 500 # Запасное значение, если ширина окна еще не определена
        
        # Определяем цвета и выравнивание
        if role == "user":
            bgcolor = "#075E54"
            text_color = ft.Colors.WHITE
            alignment = ft.MainAxisAlignment.END
            margin_left = 60
            margin_right = 10
        elif role == "assistant":
            bgcolor = ft.Colors.WHITE
            text_color = "#333333"
            alignment = ft.MainAxisAlignment.START
            margin_left = 10
            margin_right = 60
        else:
            # Системные сообщения
            bgcolor = "#FFE0B2"
            text_color = "#5D4037"
            alignment = ft.MainAxisAlignment.CENTER
            margin_left = 40
            margin_right = 40
        
        # Создаем пузырь с НАСТОЯЩИМИ округлыми углами и тенями!
        bubble = ft.Container(
            content=ft.Text(
                text,
                size=14,
                color=text_color,
                selectable=True
                # width тут не ставим, пусть Text сам переносится внутри Container-а
            ),
            bgcolor=bgcolor,
            border_radius=18,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=3,
                color=ft.Colors.with_opacity(0.26, ft.Colors.BLACK),
                offset=ft.Offset(0, 1)
            ),
            animate=ft.animation.Animation(300, ft.AnimationCurve.EASE_OUT_CUBIC),
            margin=ft.margin.only(
                left=margin_left,
                right=margin_right,
                top=4,
                bottom=4
            ),
            width=bubble_max_width # Ограничиваем ширину самого контейнера-пузыря
        )
        
        return ft.Row([bubble], alignment=alignment)
    
    def add_message_to_chat(self, text, role):
        """Добавляет сообщение в чат с анимацией"""
        if self.chat_container:
            message_bubble = self.create_message_bubble(text, role)
            self.chat_container.controls.append(message_bubble)
            
            # Прокручиваем вниз
            self.page.update()
            # Автоскролл будет работать автоматически в Column с scroll
    
    async def send_message(self, e):
        """Отправляет сообщение"""
        user_text = self.message_input.value.strip()
        if not user_text:
            return
        
        # Добавляем сообщение пользователя
        self.add_message_to_chat(user_text, "user")
        self.message_input.value = ""
        self.page.update()
        
        # Проверка на выход
        if any(word in user_text.lower() for word in ["выход", "exit", "bye"]):
            self.add_message_to_chat("Диалог завершён. До встречи!", "system")
            # Сохраняем диалог при завершении
            self.save_dialog_on_completion()
            return
        
        # Проверка на агрессивный язык
        if self.language_filter.is_aggressive(user_text):
            detected_keywords = self.language_filter.get_detected_keywords(user_text)
            role_keywords_present = False
            current_template = templates.get(self.scenario_key)
            if current_template and "keywords_for_reaction_check" in current_template:
                for r_keyword in current_template["keywords_for_reaction_check"]:
                    if r_keyword in user_text.lower():
                        role_keywords_present = True
                        break
            should_react_aggressively = role_keywords_present or (current_template and "keywords_for_reaction_check" not in current_template)

            if should_react_aggressively:
                aggression_response_text = templates.get(self.scenario_key, {}).get("aggression_response", "Please be respectful. I'm here to help you practice English.")
                self.add_message_to_chat(f"AI (System Reaction): {aggression_response_text}", "system")
                self.dialog_manager.save_aggressive_language_incident(
                    user_message=user_text,
                    detected_keywords=detected_keywords,
                    role_reaction=aggression_response_text,
                    scenario=self.scenario,
                    difficulty=self.difficulty
                )
                return
        
        # Добавляем в историю сообщений
        self.messages.append({"role": "user", "content": user_text})
        
        try:
            # Отправляем запрос к OpenAI
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=self.messages
            )
            
            answer = response.choices[0].message.content
            self.add_message_to_chat(answer, "assistant")
            self.messages.append({"role": "assistant", "content": answer})
            
        except Exception as ex:
            self.add_message_to_chat(f"Ошибка: {ex}", "error")
            self.dialog_manager.save_error("api_error", str(ex), {
                "scenario": self.scenario,
                "difficulty": self.difficulty,
                "user_message": user_text
            })
    
    def save_dialog_on_completion(self):
        """Сохраняет диалог при завершении"""
        if len(self.messages) > 1:  # есть сообщения кроме system
            self.dialog_manager.save_dialog(self.scenario, self.difficulty, self.messages)
            print(f"Dialog saved: {len(self.messages)} messages")
    
    def go_back(self, e):
        """Возвращается к стартовому экрану"""
        # Сохраняем диалог перед выходом
        self.save_dialog_on_completion()
        self.app.show_start_screen()
        self.hint_count = 0 # Сбрасываем счетчик подсказок при выходе
        # Обновление отображения подсказок произойдет при следующем показе ChatScreen
    
    async def show_help(self, e):
        """Показывает окно помощи"""
        # Уменьшаем на 1 только если помощь действительно была показана (не ошибка/лимит)
        # Это теперь делается внутри HelpDialog, после успешного отображения
        await self.help_dialog.show_help_dialog()
        # Обновляем отображение счетчика после закрытия диалога помощи (через on_dismiss)

    def _update_hints_display(self):
        """Обновляет текстовое поле с количеством подсказок."""
        if self.max_hints == float('inf'):
            self.hints_display.value = "💡 Подсказки: ∞"
        else:
            # Убедимся, что self.hint_count не превышает self.max_hints для корректного отображения
            remaining_hints = max(0, self.max_hints - self.hint_count)
            self.hints_display.value = f"💡 Подсказки: {remaining_hints}/{self.max_hints}"
        
        if self.page and self.hints_display.page: # Проверяем, что элемент добавлен на страницу
             self.page.update(self.hints_display) # Обновляем только сам текстовый элемент

    def show(self):
        """Показывает экран чата"""
        # Обновляем отображение счетчика подсказок при каждом показе экрана
        self._update_hints_display()

        # Заголовок
        header = ft.Container(
            content=ft.Row([
                ft.IconButton(
                    ft.icons.ARROW_BACK,
                    icon_color=ft.Colors.WHITE,
                    on_click=self.go_back,
                    tooltip="Назад"
                ),
                ft.Column([
                    ft.Text(
                        f"📋 {self.scenario}",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE,
                        max_lines=2
                    ),
                    ft.Text(
                        f"⚡ Сложность: {self.difficulty.upper()}",
                        size=12,
                        color=ft.Colors.with_opacity(0.70, ft.Colors.WHITE)
                    )
                ], spacing=2),
                ft.Container(expand=True), # Занимает все доступное пространство, отодвигая иконки вправо
                self.hints_display, # Добавляем отображение подсказок
                ft.Container(width=10), # Небольшой отступ перед кнопкой помощи
                ft.IconButton(
                    ft.icons.HELP_OUTLINE,
                    icon_color=ft.Colors.WHITE,
                    on_click=self.show_help,
                    # tooltip убран отсюда, т.к. количество подсказок теперь отображается рядом
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER), # Добавлено vertical_alignment
            bgcolor="#075E54",
            padding=ft.padding.all(15),
            border_radius=ft.border_radius.only(bottom_left=15, bottom_right=15)
        )
        
        # Контейнер для сообщений
        self.chat_container = ft.Column(
            controls=[],
            scroll=ft.ScrollMode.AUTO,
            auto_scroll=True,
            spacing=2
        )
        
        # Область чата
        chat_area = ft.Container(
            content=self.chat_container,
            bgcolor="#E5DDD5",  # Фон как в WhatsApp
            expand=True,
            padding=ft.padding.all(10),
            border_radius=10
        )
        
        # Поле ввода
        self.message_input = ft.TextField(
            hint_text="Введите ваше сообщение...",
            border_color="#E0E0E0",
            border_radius=25,
            filled=True,
            bgcolor=ft.Colors.WHITE,
            content_padding=ft.padding.symmetric(horizontal=20, vertical=15),
            text_size=14,
            on_submit=self.send_message,
            expand=True
        )
        
        # Кнопка отправки
        send_button = ft.Container(
            content=ft.Icon(ft.icons.SEND, color=ft.Colors.WHITE, size=24),
            bgcolor="#25D366",
            border_radius=25,
            width=50,
            height=50,
            ink=True,
            on_click=self.send_message,
            alignment=ft.alignment.center,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=5,
                color=ft.Colors.with_opacity(0.26, ft.Colors.BLACK),
                offset=ft.Offset(0, 2)
            )
        )
        
        # Панель ввода
        input_row = ft.Row([
            self.message_input,
            ft.Container(width=10),
            send_button
        ], spacing=0)
        
        input_panel = ft.Container(
            content=input_row,
            bgcolor=ft.Colors.WHITE,
            padding=ft.padding.all(15),
            border_radius=ft.border_radius.only(top_left=15, top_right=15),
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=10,
                color=ft.Colors.with_opacity(0.12, ft.Colors.BLACK),
                offset=ft.Offset(0, -2)
            )
        )
        
        # Главный контейнер чата
        main_chat = ft.Column([
            header,
            chat_area,
            input_panel
        ], spacing=0, expand=True)
        
        # Очищаем страницу и добавляем чат
        self.page.controls.clear()
        self.page.add(main_chat)
        self.page.update()


def main(page: ft.Page):
    app = EnglishLearningApp(page)

if __name__ == '__main__':
    ft.app(target=main) 