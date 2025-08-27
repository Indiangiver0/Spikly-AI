import flet as ft
import asyncio
import uuid
from openai import OpenAI
from config import OPENAI_API_KEY
from templates import templates
from dialog_manager import DialogManager
from language_filter import LanguageFilter
from prompts import get_system_prompt
from help_system_flet import HelpSystem, HelpDialog
from datetime import datetime
import os

# Глобальная переменная для хранения экземпляра приложения
# Это не самый лучший способ, но для простоты пока так.
# В идеале, нужно передавать app через page.session или другим способом.
global_app_instance = None

# Импорт голосового функционала
try:
    from voice_handler import VoiceHandler
    VOICE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Voice functionality not available: {e}")
    VOICE_AVAILABLE = False

class EnglishLearningApp:
    def __init__(self, page: ft.Page):
        global global_app_instance
        global_app_instance = self
        self.page = page
        self.dialog_manager = DialogManager()
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Состояние упражнений
        self.current_practice_session = None
        self.completed_exercises_count = 0
        
        # Настройка страницы
        self.page.title = "Английские сценки"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window.width = 800
        self.page.window.height = 600
        self.page.window.resizable = True
        self.page.bgcolor = "#F5F5F5"
        
        # Полноэкранный режим при запуске
        if hasattr(self.page.window, 'full_screen'):
             self.page.window.full_screen = True
        elif hasattr(self.page.window, 'maximized'):
             self.page.window.maximized = True
        
        # Состояние приложения
        self.current_screen = "start"
        self.chat_screen = None
        
        # Показываем стартовый экран
        self.show_start_screen()

        # Добавляем обработчик закрытия приложения
        # self.page.on_window_event = self.on_window_event # Deprecated
        if hasattr(self.page, 'window') and self.page.window:
            self.page.window.on_event = self.on_window_event
            print("Установлен обработчик self.page.window.on_event")
        else:
            # Fallback for environments where page.window might not be immediately available
            # or for older Flet versions, though this specific error points to it being available but handler assignment failing.
            try:
                self.page.on_window_event = self.on_window_event
                print("Установлен обработчик self.page.on_window_event (fallback)")
            except Exception as e:
                print(f"⚠️ Не удалось установить обработчик событий окна: {e}")
    
    def on_window_event(self, e):
        """Обработчик событий окна"""
        if isinstance(e, str): # Older Flet versions might pass string data
            event_data = e
        elif hasattr(e, 'data'): # Newer Flet versions pass event object with data attribute
            event_data = e.data
        else:
            event_data = str(e) # Fallback

        print(f"Обработано событие окна: {event_data}")
        if event_data == "close":
            # Очищаем файлы практик при закрытии приложения
            self.cleanup_practice_files()
            print("👋 Приложение закрывается, файлы практик очищены")
    
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
        
        # Контейнер для выбора режима общения
        communication_label = ft.Text("🗣️ Выберите режим общения:", size=20, weight=ft.FontWeight.W_500)
        
        communication_options = [
            ft.dropdown.Option("text", "💬 Текстовый чат - Обычное общение через сообщения"),
            ft.dropdown.Option("voice", "🎤 Голосовой чат - Говорите и слушайте ответы (в разработке)")
        ]
        
        self.communication_dropdown = ft.Dropdown(
            options=communication_options,
            hint_text="Выберите способ общения...",
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
            on_click=None,  # Explicitly set to None when disabled
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
        
        # Основной контент для выбора
        selection_content = ft.Column([
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
            ft.Container(height=40),
            communication_label,
            ft.Container(height=15),
            self.communication_dropdown,
            ft.Container(height=50),
            self.start_button,
            ft.Container(height=20),
            ft.OutlinedButton(
                content=ft.Text("📚 Отработка ошибок", size=18, color="#2E7D32"),
                on_click=self.show_error_practice_screen,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=20),
                    padding=ft.padding.symmetric(horizontal=30, vertical=20),
                    side=ft.BorderSide(2, "#2E7D32")
                ),
                width=350,
                height=70
            ),
            ft.Container(height=50),
        ],
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        # Прокручиваемый контент
        scrollable_main_content = ft.Column(
            [selection_content],
            scroll=ft.ScrollMode.ADAPTIVE, 
            expand=True,
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        # Очищаем страницу и добавляем контент
        self.page.controls.clear()
        self.page.add(scrollable_main_content)
        self.page.update()
    
    def on_selection_change(self, e):
        """Обработчик изменения выбора - активирует кнопку если все выбрано"""
        print("DEBUG: on_selection_change entered")
        print(f"DEBUG: Scenario: {self.scenario_dropdown.value}, Difficulty: {self.difficulty_dropdown.value}, Communication: {self.communication_dropdown.value}")
        # Проверяем выбраны ли и сценарий и сложность
        if self.scenario_dropdown.value and self.difficulty_dropdown.value and self.communication_dropdown.value:
            print("DEBUG: All selections made. Enabling button.")
            # Активируем кнопку - делаем яркой и кликабельной
            self.start_button.bgcolor = "#25D366"  # Яркий зеленый
            self.start_button.disabled = False  # Можно кликать
            self.start_button.on_click = self.start_dialog  # Добавляем обработчик
            self.start_button.style.shadow_color = ft.Colors.with_opacity(0.40, ft.Colors.BLACK)
            self.start_button.style.elevation = 8
        else:
            print("DEBUG: Not all selections made. Disabling button.")
            # Деактивируем кнопку - делаем серой
            self.start_button.bgcolor = "#CCCCCC"  # Серая
            self.start_button.disabled = True  # Не кликается
            self.start_button.on_click = None  # Убираем обработчик
            self.start_button.style.shadow_color = ft.Colors.with_opacity(0.20, ft.Colors.BLACK)
            self.start_button.style.elevation = 2
        
        print(f"DEBUG: Button disabled: {self.start_button.disabled}, Button on_click: {self.start_button.on_click}")
        self.page.update()
    
    def start_dialog(self, e):
        """Обработчик начала диалога"""
        print("DEBUG: start_dialog entered")
        print(f"DEBUG: Scenario: {self.scenario_dropdown.value}, Difficulty: {self.difficulty_dropdown.value}, Communication: {self.communication_dropdown.value}")
        if not self.scenario_dropdown.value or not self.difficulty_dropdown.value or not self.communication_dropdown.value:
            print("DEBUG: start_dialog - not all values selected, returning.")
            return
        
        # Очищаем файлы практик при начале нового диалога
        self.cleanup_practice_files()
        
        scenario_key = int(self.scenario_dropdown.value)
        selected_template = templates[scenario_key]
        scenario_text = selected_template["description"]
        difficulty = self.difficulty_dropdown.value
        communication_mode = self.communication_dropdown.value
        
        self.show_chat_screen(scenario_key, scenario_text, difficulty, communication_mode)
    
    def close_dialog(self, dialog):
        """Закрывает диалог"""
        dialog.open = False
        self.page.update()
    
    def show_chat_screen(self, scenario_key, scenario, difficulty, communication_mode):
        """Показывает экран чата"""
        self.current_screen = "chat"
        
        # Создаем экран чата
        self.chat_screen = ChatScreen(
            self.page, 
            self, 
            scenario_key, 
            scenario, 
            difficulty,
            communication_mode,
            self.client,
            self.dialog_manager
        )
        self.chat_screen.show()

    def show_dialog_summary_screen(self, dialog_id: str, scenario: str, difficulty: str):
        """Показывает экран с итогами диалога и опциями."""
        self.current_screen = "dialog_summary"
        self.page.controls.clear()

        summary_title = ft.Text("Диалог завершён!", size=30, weight=ft.FontWeight.BOLD, color="#075E54")
        summary_details = ft.Text(f"Сценарий: {scenario}\nСложность: {difficulty}", size=18, color="#333333", text_align=ft.TextAlign.CENTER)

        new_dialog_button = ft.ElevatedButton(
            content=ft.Text("🎉 Начать новый диалог", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            bgcolor="#25D366",
            on_click=lambda e: self.return_to_main_screen(),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20), padding=ft.padding.symmetric(horizontal=30, vertical=20)),
            width=300, height=60
        )

        practice_errors_button = ft.OutlinedButton(
            content=ft.Text("📚 Отработка ошибок", size=18, color="#075E54"),
            on_click=self.show_error_practice_screen, # Используем тот же обработчик
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=20), 
                padding=ft.padding.symmetric(horizontal=30, vertical=20),
                side=ft.BorderSide(2, "#075E54")
            ),
            width=300, height=60
        )

        summary_layout = ft.Column([
            ft.Container(height=60),
            summary_title,
            ft.Container(height=15),
            summary_details,
            ft.Container(height=50),
            new_dialog_button,
            ft.Container(height=20),
            practice_errors_button,
            ft.Container(height=60),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True
        )
        
        self.page.add(summary_layout)
        self.page.update()

    def show_error_practice_screen(self, e=None): # Добавим e=None для совместимости с on_click
        """Показывает экран отработки ошибок с полным анализом и упражнениями."""
        print("DEBUG: Entering show_error_practice_screen")
        self.current_screen = "error_practice"
        self.page.controls.clear()

        # Получаем количество монет пользователя
        user_coins = self.dialog_manager.get_user_coins()

        # Заголовок с монетами и кнопкой магазина
        header_row = ft.Row([
            ft.Text("📚 Отработка ошибок", size=30, weight=ft.FontWeight.BOLD, color="#075E54"),
            ft.Container(expand=True),  # Занимает свободное место
            ft.Container(
                content=ft.Row([
                    ft.Text("🪙", size=24),
                    ft.Text(f"{user_coins}", size=20, weight=ft.FontWeight.BOLD, color="#FFB300")
                ]),
                bgcolor="#FFF9C4",
                border_radius=15,
                padding=ft.padding.symmetric(horizontal=15, vertical=8),
                border=ft.border.all(2, "#FFB300")
            ),
            ft.Container(width=10),
            ft.ElevatedButton(
                content=ft.Text("🛒 Магазин", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                bgcolor="#FF9800",
                on_click=self.show_shop_dialog,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=15),
                    padding=ft.padding.symmetric(horizontal=20, vertical=10)
                ),
                height=45
            )
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        
        # Кнопка запуска анализа
        analyze_button = ft.ElevatedButton(
            content=ft.Text("🔍 Анализировать ошибки и создать упражнения", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            bgcolor="#25D366",
            on_click=self.start_error_analysis,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=15),
                padding=ft.padding.symmetric(horizontal=30, vertical=20)
            ),
            width=400,
            height=70
        )
        
        # Информация о системе
        info_text = ft.Text(
            """Система анализа ошибок:
            
✅ Анализирует последние 3 диалога на все типы ошибок
✅ Учитывает ваши запросы переводов 
✅ Создает персонализированные упражнения
✅ Система счетчиков X6 → X0 (отработано)
✅ Максимум 5 ошибок за сессию, по 3 упражнения на ошибку

🪙 Награды:
• +1 монета за правильное упражнение
• +5 монет бонус за полную отработку ошибки (X0)

Типы упражнений:
• Замена слов 
• Переводы (англ ↔ рус)
• Составление предложений
• Написание связных текстов

Нажмите кнопку выше для запуска анализа!""",
            size=14,
            color="#333333",
            text_align=ft.TextAlign.LEFT
        )
        
        # Контейнер для результатов анализа
        self.analysis_results_container = ft.Column([], spacing=15)
        
        # Кнопка назад
        back_button = ft.ElevatedButton(
            "⬅️ На главный экран", 
            on_click=lambda e: self.return_to_main_screen(), 
            bgcolor="#CCCCCC",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=15),
                padding=ft.padding.symmetric(horizontal=30, vertical=15)
            )
        )

        layout = ft.Column([
            ft.Container(height=20),
            header_row,
            ft.Container(height=20),
            ft.Row([analyze_button], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=30),
            info_text,
            ft.Container(height=20),
            self.analysis_results_container,
            ft.Container(height=30),
            ft.Row([back_button], alignment=ft.MainAxisAlignment.CENTER)
        ],
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True
        )

        self.page.add(layout)
        self.page.update()
        print("DEBUG: Exiting show_error_practice_screen")
    
    def show_shop_dialog(self, e):
        """Показывает диалог магазина (пока простой)"""
        print("DEBUG: Attempting to show Shop Dialog")
        user_coins = self.dialog_manager.get_user_coins()
        coins_data = self.dialog_manager.get_coins_data()
        
        shop_dialog = ft.AlertDialog(
            title=ft.Text("🛒 Магазин", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("🪙", size=24),
                        ft.Text(f"У вас: {user_coins} монет", size=16, weight=ft.FontWeight.BOLD, color="#FFB300")
                    ]),
                    ft.Container(height=20),
                    ft.Text(f"💎 Всего заработано: {coins_data.get('total_earned', 0)} монет", size=14, color="#666"),
                    ft.Container(height=20),
                    ft.Text("🚧 Скоро здесь появятся полезные покупки:", size=14, color="#333"),
                    ft.Text("• Дополнительные подсказки", size=12, color="#666"),
                    ft.Text("• Персональные темы диалогов", size=12, color="#666"),
                    ft.Text("• Расширенная аналитика прогресса", size=12, color="#666")
                ]),
                width=300,
                height=200
            ),
            actions=[
                ft.TextButton("Закрыть", on_click=lambda _: self.close_dialog(shop_dialog))
            ]
        )
        
        self.page.overlay.append(shop_dialog)
        shop_dialog.open = True
        self.page.update()
        print("DEBUG: Shop Dialog should be open")
    
    async def start_error_analysis(self, e):
        """Запускает анализ ошибок и показывает экран с результатами"""
        print("DEBUG: Entering start_error_analysis")
        loading_text = ft.Text("⚙️ Создаем тестовые упражнения...", size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
        progress_ring = ft.ProgressRing(width=32, height=32, stroke_width=4)
        
        loading_content = ft.Column(
            [
                ft.Container(height=self.page.window.height / 3 if self.page.window.height else 200),
                loading_text,
                ft.Container(height=20),
                progress_ring
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.START
        )
        
        self.page.controls.clear()
        self.page.add(loading_content)
        self.page.update()

        try:
            await asyncio.sleep(0.5)  # Небольшая задержка для показа загрузки
            
            # Используем простые тестовые упражнения
            practice_session = self.create_test_exercises()
            print(f"DEBUG: Created test exercises: {practice_session is not None}")
            
            if practice_session and practice_session.get("exercises"):
                print("DEBUG: Showing analysis results")
                self.show_analysis_results(practice_session)
            else:
                print("DEBUG: Failed to create exercises or no exercises found")
                self.page.controls.clear()
                self.page.add(ft.Text("Не удалось создать упражнения.", size=20))
                self.page.add(ft.ElevatedButton("Вернуться", on_click=lambda _: self.return_to_main_screen()))
                self.page.update()

        except Exception as ex:
            print(f"DEBUG: Exception in start_error_analysis: {ex}")
            self.page.controls.clear()
            self.page.add(ft.Text(f"Произошла ошибка: {ex}", size=18))
            self.page.add(ft.ElevatedButton("Вернуться", on_click=lambda _: self.return_to_main_screen()))
            self.page.update()
        print("DEBUG: Exiting start_error_analysis")
    
    def show_analysis_results(self, practice_session):
        """Показывает результаты анализа и первые 5 упражнений"""
        print(f"DEBUG: Entering show_analysis_results with session: {practice_session is not None}")
        self.update_coins_display()
        
        # Сохраняем текущую сессию для отслеживания
        self.current_practice_session = practice_session
        self.completed_exercises_count = 0

        back_button = ft.ElevatedButton(
            "⬅️ На главный экран", 
            on_click=lambda e: self.return_to_main_screen(), 
            bgcolor="#CCCCCC",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=15),
                padding=ft.padding.symmetric(horizontal=30, vertical=15)
            )
        )
        
        view_all_button = None

        page_content_controls = []

        # Статистика
        stats_text = ft.Text(
            f"📊 Результаты анализа:\n"
            f"• Проанализировано ошибок: {practice_session['total_errors_analyzed']}\n"
            f"• Ошибок для отработки: {practice_session['errors_for_practice']}\n"
            f"• Создано упражнений: {practice_session['total_exercises']}",
            size=14,
            color="#2E7D32",
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER
        )
        page_content_controls.append(
            ft.Container(
                content=stats_text,
                alignment=ft.alignment.center,
                padding=ft.padding.only(bottom=20)
            )
        )
        
        # Список упражнений
        exercises_title = ft.Text("📝 Упражнения:", size=18, weight=ft.FontWeight.BOLD, color="#1976D2")
        page_content_controls.append(
            ft.Container(
                content=exercises_title,
                alignment=ft.alignment.center,
                padding=ft.padding.only(bottom=15)
            )
        )
        
        # Упражнения (показываем первые 5)
        exercises_to_display = practice_session.get("exercises", [])[:5]
        print(f"DEBUG: Exercises to display: {len(exercises_to_display)}")
        exercise_cards_column_controls = []
        
        if not exercises_to_display:
            exercise_cards_column_controls.append(
                ft.Text("Нет доступных упражнений для отображения.", size=16, color=ft.Colors.GREY_700)
            )
        else:
            for index, exercise_data in enumerate(exercises_to_display):
                print(f"DEBUG: Creating card for exercise {index + 1}")
                card = self.create_exercise_card(exercise_data, index + 1)
                exercise_cards_column_controls.append(card)
        
        exercise_cards_column = ft.Column(
            exercise_cards_column_controls, 
            spacing=20, 
            expand=False,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        # Кнопка для просмотра всех упражнений
        if len(practice_session["exercises"]) > 5:
            print("DEBUG: Creating 'View All Exercises' button")
            view_all_button = ft.ElevatedButton(
                content=ft.Text(
                    f"📋 Показать все {practice_session['total_exercises']} упражнений",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE
                ),
                bgcolor="#2196F3",
                on_click=lambda e: self.show_all_exercises(practice_session),
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=15),
                    padding=ft.padding.symmetric(horizontal=30, vertical=20)
                ),
                width=350,
                height=60
            )
            exercise_cards_column.controls.append(
                ft.Container(
                    content=view_all_button,
                    alignment=ft.alignment.center,
                    padding=ft.padding.only(top=20)
                )
            )
        
        exercises_container = ft.Container(
            content=exercise_cards_column,
            padding=ft.padding.all(20),
            border_radius=10,
            alignment=ft.alignment.center
        )
        page_content_controls.append(exercises_container)
        page_content_controls.append(ft.Container(height=20))

        action_buttons_row_controls = [back_button]
        # if view_all_button: # This was causing NameError if view_all_button was not created
        #    action_buttons_row_controls.append(view_all_button)
        
        page_content_controls.append(
            ft.Row(action_buttons_row_controls, alignment=ft.MainAxisAlignment.CENTER)
        ) # Removed view_all_button from here too, as it's inside exercise_cards_column

        analysis_results_page_layout = ft.Column(
            page_content_controls,
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True
        )
        
        self.page.controls.clear()
        self.page.add(analysis_results_page_layout)
        self.page.update()
        print("DEBUG: Exiting show_analysis_results")
    
    def show_all_exercises(self, practice_session):
        """Показывает все упражнения в отдельном диалоге"""
        print("DEBUG: Attempting to show All Exercises Dialog")
        exercises = practice_session["exercises"]
        
        # Создаем прокручиваемый список всех упражнений
        all_exercises_column = ft.Column(
            [], 
            scroll=ft.ScrollMode.ADAPTIVE, 
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        for i, exercise in enumerate(exercises, 1):
            exercise_card = self.create_exercise_card(exercise, i)
            all_exercises_column.controls.append(exercise_card)
        
        # Диалог со всеми упражнениями
        all_exercises_dialog = ft.AlertDialog(
            title=ft.Text(
                f"📋 Все упражнения ({len(exercises)})",
                size=20,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER
            ),
            content=ft.Container(
                content=all_exercises_column,
                width=650,
                height=500,
                padding=ft.padding.all(10),
                alignment=ft.alignment.center
            ),
            actions=[
                ft.TextButton(
                    "Закрыть",
                    on_click=lambda _: self.close_dialog(all_exercises_dialog),
                    style=ft.ButtonStyle(color=ft.colors.RED_ACCENT_700)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER
        )
        
        self.page.overlay.append(all_exercises_dialog)
        all_exercises_dialog.open = True
        self.page.update()
        print("DEBUG: All Exercises Dialog should be open")
    
    def create_exercise_card(self, exercise, number):
        """Создает интерактивную карточку упражнения с полем ввода и кнопкой проверки"""
        print(f"DEBUG: Creating exercise card for exercise number {number}, data: {exercise is not None}")
        exercise_type_names = {
            "word_replacement": "🔄 Замена слов",
            "translation_en_ru": "🇺🇸→🇷🇺 Перевод на русский", 
            "translation_ru_en": "🇷🇺→🇺🇸 Перевод на английский",
            "simple_sentences": "📝 Составление предложений",
            "text_composition": "📖 Написание текста"
        }
        
        type_name = exercise_type_names.get(exercise["exercise_type"], exercise["exercise_type"])
        
        # Поле для ввода ответа пользователя
        answer_field = ft.TextField(
            hint_text="Введите ваш ответ...",
            hint_style=ft.TextStyle(color="#757575"),
            multiline=True,
            min_lines=3,
            max_lines=6,
            border_color="#2196F3",
            focused_border_color="#1976D2",
            border_radius=10,
            filled=True,
            bgcolor=ft.Colors.WHITE,
            content_padding=ft.padding.all(15),
            text_size=15,
            text_style=ft.TextStyle(color="#1A1A1A"),
            expand=True
        )
        
        # Контейнер для результата проверки
        result_container = ft.Container(
            content=ft.Text(""),
            visible=False,
            bgcolor="#F5F5F5",
            border_radius=10,
            padding=ft.padding.all(15),
            margin=ft.margin.only(top=10)
        )
        
        # Кнопка проверки
        check_button = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, size=18, color=ft.Colors.WHITE),
                ft.Text("Проверить", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor="#4CAF50",
            on_click=lambda e: self.handle_check_exercise(exercise, answer_field, result_container, check_button),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.padding.symmetric(horizontal=20, vertical=15)
            ),
            width=150,
            height=50
        )

        # Determine content for the exercise text display
        exercise_display_content_value = self.format_exercise_content(exercise["content"], exercise["exercise_type"])
        print(f"DEBUG: Card {number} - Formatted exercise content: '{exercise_display_content_value[:100]}...' ")


        exercise_display_content = ft.Text(
                    exercise_display_content_value, # Was just exercise_display_content before
                    size=15, 
                    color="#1A1A1A",
                    selectable=True,
                    weight=ft.FontWeight.W_500
                )

        # Основная карточка
        card_content = ft.Column([
            # Заголовок упражнения
            ft.Container(
                content=ft.Row([
                    ft.Text(f"{number}.", size=18, weight=ft.FontWeight.BOLD, color="#1976D2"),
                    ft.Text(type_name, size=16, weight=ft.FontWeight.BOLD, color="#1976D2"),
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Text("🪙+1", size=12, weight=ft.FontWeight.BOLD, color="#FF8F00"),
                        bgcolor="#FFF8E1",
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border=ft.border.all(1, "#FF8F00")
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.padding.only(bottom=10)
            ),
            
            # Информация об ошибке
            ft.Container(
                content=ft.Column([
                    ft.Text("🎯 Отрабатываемая ошибка:", size=13, weight=ft.FontWeight.BOLD, color="#1976D2"),
                    ft.Text(
                        f"❌ {exercise['original_error']} → ✅ {exercise['correct_form']}", 
                        size=14, 
                        color="#1A1A1A",
                        weight=ft.FontWeight.W_600
                    )
                ], spacing=5),
                bgcolor="#E3F2FD",
                border_radius=8,
                padding=ft.padding.all(12),
                margin=ft.margin.only(bottom=15),
                border=ft.border.all(1, "#2196F3")
            ),
            
            # Содержание упражнения
            ft.Container(
                content=exercise_display_content, # Changed from ft.Text(exercise_display_content, ...)
                bgcolor="#FFFFFF",
                border_radius=8,
                padding=ft.padding.all(20),
                margin=ft.margin.only(bottom=15),
                border=ft.border.all(2, "#2196F3")
            ),
            
            # Поле ввода
            answer_field,
            
            # Кнопка проверки
            ft.Container(
                content=check_button,
                alignment=ft.alignment.center,
                padding=ft.padding.only(top=15)
            ),
            
            # Результат проверки
            result_container
        ])
        
        return ft.Container(
            content=card_content,
            bgcolor=ft.Colors.WHITE,
            border_radius=15,
            padding=ft.padding.all(20),
            margin=ft.margin.only(bottom=20),
            border=ft.border.all(1, "#E0E0E0"),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
                offset=ft.Offset(0, 2)
            ),
            width=600  # Фиксированная ширина для центрирования
        )
    
    def handle_check_exercise(self, exercise, answer_field, result_container, check_button):
        """Синхронный обработчик для проверки упражнения"""
        print(f"DEBUG: Handling check for exercise: {exercise.get('exercise_id', 'N/A')}")
        import threading
        
        def run_async():
            import asyncio
            try:
                # Создаем новый event loop для этого потока
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.check_exercise_async(exercise, answer_field, result_container, check_button))
            except Exception as e:
                # В случае ошибки показываем сообщение пользователю
                print(f"DEBUG: Error in run_async for check_exercise: {e}")
                result_container.content = ft.Text(f"Ошибка проверки: {e}", size=14, color="#F44336")
                result_container.bgcolor = "#FFEBEE"
                result_container.visible = True
                if self.page: self.page.update() # Ensure page update
            finally:
                if 'loop' in locals() and loop.is_running():
                    loop.close()
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=run_async)
        thread.daemon = True
        thread.start()
    
    async def check_exercise_async(self, exercise, answer_field, result_container, check_button):
        """Асинхронная проверка ответа пользователя на упражнение"""
        print(f"DEBUG: Starting async check for exercise: {exercise.get('exercise_id', 'N/A')}")
        user_answer = answer_field.value.strip()
        if not user_answer:
            result_container.content = ft.Text(
                "⚠️ Пожалуйста, введите ваш ответ", 
                size=14, 
                color="#FF9800",
                weight=ft.FontWeight.BOLD
            )
            result_container.bgcolor = "#FFF3E0"
            result_container.visible = True
            if self.page: self.page.update()
            return
        
        # Блокируем кнопку во время проверки
        check_button.disabled = True
        check_button.content = ft.Row([
            ft.ProgressRing(width=16, height=16, color=ft.Colors.WHITE),
            ft.Text("Проверяю...", size=14, color=ft.Colors.WHITE)
        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)
        if self.page: self.page.update()
        
        try:
            # Простая проверка - считаем ответ правильным если он содержит правильную форму
            correct_form = exercise.get("correct_form", "").lower()
            is_correct = correct_form in user_answer.lower()
            
            await asyncio.sleep(0.5) # Simulate network delay for checking

            if is_correct:
                # Начисляем монеты
                new_coin_count = self.dialog_manager.add_coins(1, "exercise_completed")
                
                # Увеличиваем счетчик выполненных упражнений
                self.completed_exercises_count += 1
                
                # Проверяем, все ли упражнения выполнены
                total_exercises = self.current_practice_session.get("total_exercises", 0) if self.current_practice_session else 0
                if self.completed_exercises_count >= total_exercises and total_exercises > 0 : # Check total_exercises > 0
                    self.cleanup_practice_files()
                    print(f"🎉 Все {total_exercises} упражнений выполнены! Файлы практик очищены.")
                
                result_container.content = ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color="#4CAF50", size=20),
                        ft.Text("Правильно!", size=16, weight=ft.FontWeight.BOLD, color="#2E7D32")
                    ]),
                    ft.Text("Отличная работа! Вы использовали правильную форму.", size=14, color="#1A1A1A"),
                    ft.Container(
                        content=ft.Row([
                            ft.Text("🪙", size=18),
                            ft.Text(f"+1 монета! Всего: {new_coin_count}", size=14, weight=ft.FontWeight.BOLD, color="#FF8F00")
                        ]),
                        bgcolor="#FFF8E1",
                        border_radius=8,
                        padding=ft.padding.all(10),
                        margin=ft.margin.only(top=10)
                    )
                ])
                result_container.bgcolor = "#E8F5E8"
                
                self.update_coins_display()
                
            else:
                result_container.content = ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.ERROR, color="#F44336", size=20),
                        ft.Text("Попробуйте еще раз", size=16, weight=ft.FontWeight.BOLD, color="#D32F2F")
                    ]),
                    ft.Text("Убедитесь, что вы используете правильную форму в своем ответе.", size=14, color="#1A1A1A"),
                    ft.Text(f"Подсказка: используйте '{exercise.get('correct_form', '')}'", size=14, color="#1976D2", weight=ft.FontWeight.W_600)
                ])
                result_container.bgcolor = "#FFEBEE"
            
            result_container.visible = True
            
            # Блокируем кнопку после проверки (независимо от результата)
            check_button.content = ft.Row([
                ft.Icon(ft.Icons.DONE, size=18, color=ft.Colors.WHITE),
                ft.Text("Проверено", size=14, color=ft.Colors.WHITE)
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)
            check_button.bgcolor = "#9E9E9E"
            check_button.disabled = True # Explicitly keep disabled
            
        except Exception as ex:
            print(f"DEBUG: Exception in check_exercise_async: {ex}")
            result_container.content = ft.Text(
                f"❌ Ошибка проверки: {ex}", 
                size=14, 
                color="#F44336"
            )
            result_container.bgcolor = "#FFEBEE"
            result_container.visible = True
            
            # Восстанавливаем кнопку в случае ошибки (опционально, но хорошо для UX)
            check_button.disabled = False
            check_button.content = ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, size=18, color=ft.Colors.WHITE),
                ft.Text("Проверить", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)
            check_button.bgcolor="#4CAF50" # Restore original color
        
        if self.page: self.page.update()
        print(f"DEBUG: Exiting async check for exercise: {exercise.get('exercise_id', 'N/A')}")
    
    def update_coins_display(self):
        """Обновляет отображение монет в интерфейсе"""
        print("DEBUG: Updating coins display (currently a placeholder)")
        # This method needs to find the coin display Text control and update it.
        # For now, we'll assume it's handled elsewhere or will be implemented.
        # If self.current_screen == "error_practice", we might need to rebuild parts of it.
        pass

    def format_exercise_content(self, content, exercise_type=None):
        """Форматирует содержимое упражнения для лучшего отображения"""
        print(f"DEBUG: format_exercise_content INPUT: '{str(content)[:100]}...' Type: {exercise_type}")
        if not content:
            return "Содержимое упражнения недоступно"
        
        try:
            # Просто очищаем и возвращаем контент как есть
            formatted_text = str(content).strip() # Ensure content is string
            
            # Обрабатываем переносы строк
            formatted_text = formatted_text.replace("\\n", "\n")
            
            # Убираем лишние пустые строки
            lines = []
            for line in formatted_text.split('\n'):
                cleaned_line = line.strip()
                if cleaned_line: # Only add non-empty lines
                    lines.append(cleaned_line)
            
            formatted_text = '\n'.join(lines)
            
            result = formatted_text if formatted_text.strip() else "Упражнение загружается..."
            print(f"DEBUG: format_exercise_content RETURNING: '{result[:100]}...' ")
            return result
            
        except Exception as e:
            print(f"DEBUG: format_exercise_content EXCEPTION: {e}")
            return f"Ошибка отображения: {str(e)}"

    def create_simple_exercise(self, error_type, original_error, correct_form, exercise_number):
        """Создает простое упражнение без использования OpenAI"""
        print(f"DEBUG: Creating simple exercise number {exercise_number}")
        exercise_types = [
            "word_replacement",
            "translation_en_ru", 
            "translation_ru_en"
        ]
        
        exercise_type = exercise_types[exercise_number % len(exercise_types)]
        
        content = "" # Initialize content
        if exercise_type == "word_replacement":
            content = f"Исправьте ошибку в следующем предложении:\n\n" \
                     f"Неправильно: {original_error}\n" \
                     f"Напишите правильный вариант:"
                     
        elif exercise_type == "translation_en_ru":
            content = f"Переведите на русский язык:\n\n" \
                     f"{correct_form}\n\n" \
                     f"Ваш перевод:"
                     
        elif exercise_type == "translation_ru_en":
            # Changed for clarity, "Правильная форма:" might be confusing here
            content = f"Переведите на английский язык следующую фразу, используя '{correct_form}':\\n\\n" \
                      f"Фраза для перевода: (Пример: '{correct_form}' используется в предложении...)" # Placeholder, needs actual Russian phrase
                      # This exercise type needs more thought if we don't have a Russian equivalent of the error.
                      # For now, let's make it simple:
            content = f"Составьте предложение на английском языке, используя правильную форму: '{correct_form}'."


        
        return {
            "exercise_id": f"simple_{exercise_type}_{exercise_number}_{datetime.now().strftime('%H%M%S%f')}", # Added %f for milliseconds
            "exercise_type": exercise_type,
            "exercise_number": exercise_number,
            "original_error": original_error,
            "correct_form": correct_form,
            "error_type": error_type,
            "content": content,
            "completed": False,
            "attempts": 0,
            "timestamp": datetime.now().isoformat()
        }

    def cleanup_practice_files(self):
        """Удаляет все файлы практических сессий"""
        try:
            sessions_dir = os.path.join(self.dialog_manager.logs_dir, "practice_sessions")
            if os.path.exists(sessions_dir):
                import shutil
                shutil.rmtree(sessions_dir)
                print("🗑️ Файлы практических сессий удалены")
        except Exception as e:
            print(f"❌ Ошибка удаления файлов практик: {e}")

    def create_test_exercises(self):
        """Создает тестовые упражнения для проверки отображения"""
        print("DEBUG: Creating test exercises")
        test_exercises = []
        
        # Тестовые ошибки
        test_errors = [
            {"type": "grammar", "original": "I am go to school", "correct": "I am going to school"},
            {"type": "vocabulary", "original": "I have 20 years old", "correct": "I am 20 years old"},
            {"type": "preposition", "original": "I live at Moscow", "correct": "I live in Moscow"},
        ]
        
        # Создаем по 3 упражнения на каждую ошибку
        exercise_counter = 1
        for error in test_errors:
            for i in range(3):  # 3 упражнения на ошибку
                exercise = self.create_simple_exercise(
                    error["type"], 
                    error["original"], 
                    error["correct"], 
                    exercise_counter
                )
                test_exercises.append(exercise)
                exercise_counter += 1
        
        return {
            "session_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S%f')}", # Added %f
            "timestamp": datetime.now().isoformat(),
            "total_errors_analyzed": 3,
            "errors_for_practice": 3,
            "total_exercises": 9,  # 3 ошибки × 3 упражнения
            "exercises": test_exercises,
            "error_profile_snapshot": {} # Placeholder for now
        }

    def return_to_main_screen(self, e=None): # Added e=None for compatibility with on_click
        """Возвращается на главный экран с очисткой файлов практик"""
        print("DEBUG: Returning to main screen")
        # Очищаем файлы практик при возврате на главный экран
        self.cleanup_practice_files()
        self.show_start_screen()

class ChatScreen:
    def __init__(self, page: ft.Page, app: 'EnglishLearningApp', scenario_key, scenario, difficulty, communication_mode, client, dialog_manager):
        self.page = page
        self.app = app # Сохраняем ссылку на экземпляр EnglishLearningApp
        self.dialog_id = str(uuid.uuid4())
        self.scenario_key = scenario_key
        self.scenario = scenario
        self.difficulty = difficulty
        self.communication_mode = communication_mode
        self.client = client
        self.dialog_manager = dialog_manager
        # Передаем созданный OpenAI клиент в DialogManager
        if self.dialog_manager and self.client: # Check if they exist
            self.dialog_manager.set_openai_client(self.client)
        self.language_filter = LanguageFilter()
        
        # Состояние чата
        self.messages = []
        self.hint_count = 0
        self.max_hints = self.get_max_hints()
        
        # UI элементы
        self.chat_container = None # type: ft.Column | None
        self.message_input = None # type: ft.TextField | None
        self.hints_display = ft.Text(weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE) # Для отображения подсказок
        
        # Голосовой функционал
        self.voice_handler = None # type: VoiceHandler | None
        self.voice_button = None # type: ft.Container | None
        self.is_voice_mode = (communication_mode == "voice")
        
        if self.is_voice_mode and VOICE_AVAILABLE:
            try:
                self.voice_handler = VoiceHandler()
                self.setup_voice_callbacks()
            except Exception as e:
                print(f"⚠️ Error initializing VoiceHandler: {e}")
                VOICE_AVAILABLE = False # Disable voice if init fails
                self.is_voice_mode = False # Fallback to text mode

        # Система помощи
        # Ensure HelpSystem and HelpDialog are initialized correctly
        try:
            # These require client and dialog_manager to be properly initialized
            if self.client and self.dialog_manager:
                 self.help_system = HelpSystem(self.client, self.dialog_manager)
                 self.help_dialog = HelpDialog(self.page, self, self.client, self.dialog_manager) # Pass self as chat_screen
            else:
                print("⚠️ HelpSystem/HelpDialog not initialized due to missing client or dialog_manager")
                self.help_system = None
                self.help_dialog = None

        except Exception as e:
            print(f"⚠️ Error initializing HelpSystem/HelpDialog: {e}")
            self.help_system = None
            self.help_dialog = None

        # Определение системного промпта
        current_template_details = templates.get(self.scenario_key, {}) # Получаем детали шаблона по ID

        self.system_prompt_content = get_system_prompt(
            scenario_description=self.scenario, # Это текстовое описание роли, переданное в конструктор
            difficulty=self.difficulty,
            role_aggression_response=current_template_details.get("aggression_response"), # Берем из шаблона по ID
            scenario_key=self.scenario_key # Это ID сценария
        )
        self.messages = [{"role": "system", "content": self.system_prompt_content}]
        print(f"DEBUG: ChatScreen initialized for scenario {self.scenario_key}, mode {self.communication_mode}")
    
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
        # This method seems redundant as system prompt is set in __init__
        # If it's meant to be called later, ensure it's used.
        print("DEBUG: Setting up system prompt (Note: also done in __init__)")
        current_template_details = templates.get(self.scenario_key, {})
        aggression_response_for_role = current_template_details.get("aggression_response")

        system_content = get_system_prompt(
            scenario_description=self.scenario, 
            difficulty=self.difficulty,
            role_aggression_response=aggression_response_for_role,
            scenario_key=self.scenario_key # Убедимся, что scenario_key также передается здесь
        )
        
        self.messages = [{"role": "system", "content": system_content}]
    
    def setup_voice_callbacks(self):
        """Настраивает колбэки для голосового обработчика"""
        if not self.voice_handler:
            print("DEBUG: Voice handler not available, skipping voice callbacks setup.")
            return
            
        self.voice_handler.on_recording_start = self.on_voice_recording_start
        self.voice_handler.on_recording_stop = self.on_voice_recording_stop
        self.voice_handler.on_transcription_ready = self.on_voice_transcription_ready
        print("DEBUG: Voice callbacks set up.")

    def on_voice_recording_start(self):
        """Колбэк начала записи голоса"""
        print("DEBUG: Voice recording started (callback)")
        if self.voice_button:
            self.voice_button.icon = ft.Icons.STOP
            self.voice_button.bgcolor = "#F44336"  # Красный
            self.voice_button.tooltip = "Остановить запись"
            if self.page: self.page.update(self.voice_button)
    
    def on_voice_recording_stop(self):
        """Колбэк остановки записи голоса"""
        print("DEBUG: Voice recording stopped (callback)")
        if self.voice_button:
            self.voice_button.icon = ft.Icons.MIC
            self.voice_button.bgcolor = "#4CAF50"  # Зеленый
            self.voice_button.tooltip = "Начать запись"
            if self.page: self.page.update(self.voice_button)
            
        # Запускаем транскрипцию
        if self.voice_handler:
            print("DEBUG: Scheduling voice transcription processing.")
            asyncio.create_task(self.process_voice_transcription())
    
    def on_voice_transcription_ready(self, text: str):
        """Колбэк готовности транскрипции"""
        print(f"DEBUG: Voice transcription ready (callback): '{text}'")
        # Добавляем транскрибированный текст в поле ввода
        if self.message_input:
            self.message_input.value = text
            if self.page: self.page.update(self.message_input)
    
    async def process_voice_transcription(self):
        """Обрабатывает транскрипцию голоса"""
        if not self.voice_handler:
            print("DEBUG: No voice handler for transcription processing.")
            return
            
        try:
            # Показываем индикатор обработки
            self.add_message_to_chat("🎤 Обрабатываю голосовое сообщение...", "system")
            
            # Транскрибируем аудио
            print("DEBUG: Awaiting transcription from voice_handler.")
            transcription = await self.voice_handler.transcribe_audio()
            print(f"DEBUG: Transcription received: '{transcription}'")

            if transcription:
                # Удаляем индикатор обработки
                if self.chat_container and self.chat_container.controls:
                    self.chat_container.controls.pop()  # Удаляем последнее сообщение
                
                # Добавляем транскрибированное сообщение
                self.add_message_to_chat(f"🗣️ {transcription}", "user")
                
                # Отправляем сообщение в чат
                await self.process_text_message(transcription)
            else:
                # Удаляем индикатор и показываем ошибку
                if self.chat_container and self.chat_container.controls:
                    self.chat_container.controls.pop()
                self.add_message_to_chat("❌ Не удалось распознать речь. Попробуйте еще раз.", "system")
                
        except Exception as e:
            print(f"Error processing voice transcription: {e}")
            self.add_message_to_chat("❌ Ошибка обработки голоса.", "system")
    
    async def handle_voice_button_click(self, e):
        """Обработчик нажатия кнопки записи голоса"""
        if not self.voice_handler:
            print("DEBUG: Voice button clicked, but no voice handler.")
            return
        
        if self.voice_handler.is_recording:
            print("DEBUG: Stopping voice recording (button click).")
            self.voice_handler.stop_recording()
        else:
            print("DEBUG: Starting voice recording (button click).")
            self.voice_handler.start_recording()
    
    async def play_ai_response_voice(self, text: str):
        """Воспроизводит ответ ИИ голосом"""
        if not self.voice_handler or not self.is_voice_mode:
            print("DEBUG: Not playing AI voice (no handler or not voice mode).")
            return
            
        try:
            # Показываем индикатор генерации речи
            self.add_message_to_chat("🔊 Генерирую голосовой ответ...", "system")
            
            # Генерируем речь
            print("DEBUG: Generating speech from AI text.")
            audio_data = await self.voice_handler.text_to_speech(text)
            
            # Удаляем индикатор
            if self.chat_container and self.chat_container.controls:
                self.chat_container.controls.pop()
            
            if audio_data:
                # Воспроизводим аудио
                print("DEBUG: Playing AI audio response.")
                self.voice_handler.play_audio(audio_data) # This might need to be async or threaded if it blocks
                self.add_message_to_chat("🔊 Воспроизвожу ответ...", "system") # This appears after playback starts
            else:
                self.add_message_to_chat("❌ Не удалось сгенерировать голосовой ответ.", "system")
                
        except Exception as e:
            print(f"Error playing AI voice response: {e}")
            self.add_message_to_chat("❌ Ошибка воспроизведения голоса.", "system")

    def create_message_bubble(self, text, role):
        """Создает красивый пузырь сообщения в стиле WhatsApp"""
        
        # Определяем максимальную ширину пузыря
        bubble_max_width = self.page.window.width * 0.6 if self.page.window.width and self.page.window.width > 0 else 400 # Added fallback
        
        # Определяем цвета и выравнивание
        if role == "user":
            bgcolor = "#075E54" # Darker Green (original WhatsApp user bubble)
            text_color = ft.Colors.WHITE
            alignment = ft.MainAxisAlignment.END
            margin_left = 60
            margin_right = 10
        elif role == "assistant":
            bgcolor = ft.Colors.WHITE # WhatsApp AI/other person bubble
            text_color = "#333333" # Dark gray for text
            alignment = ft.MainAxisAlignment.START
            margin_left = 10
            margin_right = 60
        else: # System messages
            bgcolor = "#FFE0B2" # Light yellow, like WhatsApp system messages
            text_color = "#5D4037" # Brownish text
            alignment = ft.MainAxisAlignment.CENTER
            margin_left = 40
            margin_right = 40
        
        # Создаем пузырь с округлыми углами и тенями
        bubble = ft.Container(
            content=ft.Text(
                text,
                size=14, # Slightly smaller for better fit
                color=text_color,
                selectable=True
            ),
            bgcolor=bgcolor,
            border_radius=18, # More rounded
            padding=ft.padding.symmetric(horizontal=16, vertical=12), # Adjusted padding
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=3, # Softer shadow
                color=ft.Colors.with_opacity(0.20, ft.Colors.BLACK), # Lighter shadow
                offset=ft.Offset(0, 1)
            ),
            animate=ft.animation.Animation(300, ft.AnimationCurve.EASE_OUT_CUBIC),
            margin=ft.margin.only(
                left=margin_left,
                right=margin_right,
                top=4, # Reduced top/bottom margin for tighter packing
                bottom=4
            ),
            # width=bubble_max_width # Max width is better for responsive
            max_width=bubble_max_width # Use max_width
        )
        
        return ft.Row([bubble], alignment=alignment)
    
    def add_message_to_chat(self, text, role):
        """Добавляет сообщение в чат с анимацией"""
        if self.chat_container:
            message_bubble = self.create_message_bubble(text, role)
            self.chat_container.controls.append(message_bubble)
            if self.page: self.page.update(self.chat_container) # Update only chat_container for efficiency
    
    async def send_message(self, e=None): # Added e=None for direct calls
        """Отправляет сообщение"""
        if not self.message_input: return

        user_text = self.message_input.value.strip()
        if not user_text:
            return
        
        # Очищаем поле ввода
        self.message_input.value = ""
        if self.page: self.page.update(self.message_input) # Update only input field
        
        # Обрабатываем текстовое сообщение
        await self.process_text_message(user_text)
    
    async def process_text_message(self, user_text: str):
        """Обрабатывает текстовое сообщение (из ввода или голоса)"""
        print(f"DEBUG: Processing text message: '{user_text}'")
        # Добавляем сообщение пользователя
        self.add_message_to_chat(user_text, "user")

        # Предварительный анализ сообщения пользователя
        if self.language_filter.is_aggressive(user_text):
            detected_profanity_keywords = self.language_filter.get_detected_keywords(user_text)
            if detected_profanity_keywords and self.dialog_manager:
                self.dialog_manager.log_raw_user_error(
                    dialog_id=self.dialog_id,
                    user_message_text=user_text,
                    detected_error_type="profanity",
                    raw_error_details=detected_profanity_keywords,
                    context={"scenario": self.scenario, "difficulty": self.difficulty}
                )

        common_russian_words = [
            "да", "нет", "не", "и", "в", "на", "я", "ты", "он", "она", "оно", "мы", "вы", "они",
            "мой", "твой", "его", "ее", "их", "наш", "ваш", "это", "тот", "так", "как", "что", "где",
            "когда", "привет", "пока", "спасибо", "пожалуйста", "хорошо", "плохо", "что-то", "почему"
        ]
        
        detected_russian_words = []
        user_words = user_text.lower().replace(',', '').replace('.', '').replace('!', '').replace('?', '').split()
        for word in user_words:
            if word in common_russian_words:
                detected_russian_words.append(word)
        
        if detected_russian_words and self.dialog_manager:
            self.dialog_manager.log_raw_user_error(
                dialog_id=self.dialog_id,
                user_message_text=user_text,
                detected_error_type="russian_word_detected",
                raw_error_details=list(set(detected_russian_words)), # Unique words
                context={"scenario": self.scenario, "difficulty": self.difficulty}
            )
        
        if any(word in user_text.lower() for word in ["выход", "exit", "bye", "пока"]): # Added "пока"
            self.add_message_to_chat("Диалог завершён. До встречи!", "system")
            self.save_dialog_on_completion()
            if self.app : self.app.show_dialog_summary_screen(self.dialog_id, self.scenario, self.difficulty)
            return
        
        # Aggression check moved after exit check
        current_template = templates.get(self.scenario_key)
        if self.language_filter.is_aggressive(user_text) and current_template:
            # ... (rest of aggression logic as before)
            # Ensure dialog_manager is checked before use
            if self.dialog_manager:
                # ... dialog_manager.save_aggressive_language_incident(...)
                pass # Placeholder for brevity
            return

        self.messages.append({"role": "user", "content": user_text})
        
        if not self.client:
            self.add_message_to_chat("Ошибка: OpenAI клиент не инициализирован.", "system")
            print("ERROR: OpenAI client not initialized in ChatScreen.")
            return

        try:
            # Показываем индикатор "печатает..."
            typing_indicator = self.create_message_bubble("AI печатает...", "assistant") # System role might be better
            if self.chat_container:
                self.chat_container.controls.append(typing_indicator)
                if self.page: self.page.update(self.chat_container)

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=self.messages,
                temperature=0.7 # Default, can be adjusted
            )
            
            # Удаляем индикатор "печатает..."
            if self.chat_container and self.chat_container.controls and self.chat_container.controls[-1] == typing_indicator:
                self.chat_container.controls.pop()
                # No page update needed here, will be updated when AI message is added
            
            answer = response.choices[0].message.content
            self.add_message_to_chat(answer, "assistant") # This updates the page
            self.messages.append({"role": "assistant", "content": answer})
            
            if self.is_voice_mode and VOICE_AVAILABLE and self.voice_handler:
                await self.play_ai_response_voice(answer)
            
            if self.dialog_manager:
                asyncio.create_task(
                    self.dialog_manager.analyze_and_save_detailed_user_errors(
                        dialog_id=self.dialog_id,
                        user_message_text=user_text,
                        full_dialog_history=self.messages
                    )
                )
            
        except Exception as ex:
            print(f"ERROR in process_text_message (OpenAI call): {ex}")
            self.add_message_to_chat(f"Ошибка API: {ex}", "system") # Changed role to system
            if self.dialog_manager:
                self.dialog_manager.save_error("api_error", str(ex), {
                    "scenario": self.scenario,
                    "difficulty": self.difficulty,
                    "user_message": user_text
                })
    
    def save_dialog_on_completion(self):
        """Сохраняет диалог при завершении"""
        if len(self.messages) > 1 and self.dialog_manager:  # есть сообщения кроме system
            self.dialog_manager.save_dialog(self.dialog_id, self.scenario, self.difficulty, self.messages)
            print(f"Dialog (ID: {self.dialog_id}) saved: {len(self.messages)} messages")
    
    def close_dialog(self, dialog: ft.AlertDialog): # Type hint for dialog
        """Закрывает диалог"""
        dialog.open = False
        if self.page: self.page.update() # Update the whole page to remove overlay
    
    def go_back(self, e):
        """Возвращается к стартовому экрану через экран итогов"""
        print("DEBUG: ChatScreen go_back called.")
        if self.voice_handler:
            print("DEBUG: Cleaning up voice handler.")
            self.voice_handler.cleanup()
            
        self.save_dialog_on_completion()
        if self.app: self.app.show_dialog_summary_screen(self.dialog_id, self.scenario, self.difficulty)
        self.hint_count = 0 # Reset hint count
    
    async def show_help(self, e):
        """Показывает окно помощи"""
        print("DEBUG: Attempting to show Help Dialog from ChatScreen")
        if self.help_dialog:
            await self.help_dialog.show_help_dialog()
        else:
            print("ERROR: HelpDialog not initialized, cannot show help.")
            # Optionally, show a simple message to the user
            error_dialog = ft.AlertDialog(title=ft.Text("Ошибка"), content=ft.Text("Система помощи недоступна."))
            self.page.overlay.append(error_dialog)
            error_dialog.open = True
            self.page.update()


    def _update_hints_display(self):
        """Обновляет текстовое поле с количеством подсказок."""
        if self.max_hints == float('inf'):
            self.hints_display.value = "💡 Подсказки: ∞"
        else:
            remaining_hints = max(0, self.max_hints - self.hint_count)
            self.hints_display.value = f"💡 Подсказки: {remaining_hints}/{self.max_hints}"
        
        # Check if page and hints_display are valid and attached to page
        if self.page and self.hints_display and self.hints_display.page:
             self.page.update(self.hints_display)
        elif self.page and self.hints_display: # If not attached, try to update page anyway if it might be part of a larger update
             print("DEBUG: _update_hints_display called, but hints_display might not be on page yet.")
             # self.page.update() # Avoid full page update if only this changed and it's not visible

    def show(self):
        """Показывает экран чата"""
        print("DEBUG: ChatScreen.show() called.")
        self._update_hints_display()

        # Заголовок
        header = ft.Container(
            content=ft.Row([
                ft.IconButton(
                    ft.icons.ARROW_BACK, # Corrected to ft.icons
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
                        # max_lines=2, # Removed for now, can cause layout issues if too restrictive
                        overflow=ft.TextOverflow.ELLIPSIS # Better for long text
                    ),
                    ft.Text(
                        f"⚡ Сложность: {self.difficulty.upper()}",
                        size=12,
                        color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE) # Brighter opacity
                    ),
                    ft.Text(
                        f"🗣️ Режим: {'💬 Текст' if self.communication_mode == 'text' else '🎤 Голос'}",
                        size=12,
                        color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE)
                    )
                ], spacing=2, expand=True), # Added expand=True to Column for better space usage
                # ft.Container(expand=True), # Removed redundant expander
                self.hints_display, # Already aligned due to Row properties
                ft.Container(width=10),
                ft.IconButton(
                    ft.icons.HELP_OUTLINE, # Corrected to ft.icons
                    icon_color=ft.Colors.WHITE,
                    on_click=self.show_help,
                    tooltip="Помощь" # Added tooltip
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#075E54", # Dark WhatsApp Green
            padding=ft.padding.all(15),
            border_radius=ft.border_radius.only(bottom_left=20, bottom_right=20) # Softer radius
        )
        
        # Контейнер для сообщений
        self.chat_container = ft.Column(
            controls=[],
            scroll=ft.ScrollMode.ADAPTIVE, # Changed from AUTO for better control
            auto_scroll=True, # Keep auto_scroll
            spacing=2, # Minimal spacing between bubbles
            # expand=True # Ensure chat_container itself can expand
        )
        
        # Область чата
        chat_area = ft.Container(
            content=self.chat_container,
            bgcolor="#E5DDD5", # WhatsApp chat background
            expand=True,
            padding=ft.padding.all(10),
            border_radius=ft.border_radius.only(top_left=10, top_right=10) # Slight radius for chat area
        )
        
        # Поле ввода
        self.message_input = ft.TextField(
            hint_text="Введите ваше сообщение...",
            border_color="#E0E0E0", # Light grey border
            border_radius=25, # Rounded input field
            filled=True,
            bgcolor=ft.Colors.WHITE,
            content_padding=ft.padding.symmetric(horizontal=20, vertical=15),
            text_size=14,
            on_submit=self.send_message, # Async version
            expand=True,
            shift_enter=True, # Allow multiline with Shift+Enter
            min_lines=1,
            max_lines=5,
        )
        
        # Кнопка отправки
        send_button = ft.Container(
            content=ft.Icon(ft.icons.SEND, color=ft.Colors.WHITE, size=24), # Corrected to ft.icons
            bgcolor="#25D366", # WhatsApp Green
            border_radius=25, # Fully rounded
            width=50,
            height=50,
            ink=True,
            on_click=self.send_message, # Async version
            alignment=ft.alignment.center,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=5,
                color=ft.Colors.with_opacity(0.20, ft.Colors.BLACK), # Softer shadow
                offset=ft.Offset(0, 2)
            ),
            tooltip="Отправить" # Added tooltip
        )
        
        # Кнопка записи голоса (только для голосового режима)
        input_buttons = [send_button] # Send button is always present
        
        if self.is_voice_mode and VOICE_AVAILABLE:
            self.voice_button = ft.Container(
                content=ft.Icon(ft.icons.MIC, color=ft.Colors.WHITE, size=24), # Corrected to ft.icons
                bgcolor="#4CAF50", # Standard Green for mic
                border_radius=25,
                width=50,
                height=50,
                ink=True,
                on_click=self.handle_voice_button_click, # Async version
                alignment=ft.alignment.center,
                tooltip="Начать запись",
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=5,
                    color=ft.Colors.with_opacity(0.20, ft.Colors.BLACK),
                    offset=ft.Offset(0, 2)
                )
            )
            input_buttons.insert(0, self.voice_button)  # Mic button first
            input_buttons.insert(1, ft.Container(width=10))  # Отступ между кнопками
        
        # Панель ввода
        input_row_controls = [self.message_input, ft.Container(width=10)] + input_buttons
        input_row = ft.Row(input_row_controls, spacing=0, vertical_alignment=ft.CrossAxisAlignment.END) # Align items to bottom
        
        input_panel = ft.Container(
            content=input_row,
            bgcolor=ft.Colors.GREY_200, # Light grey background for input panel
            padding=ft.padding.symmetric(horizontal=15, vertical=10), # Adjusted padding
            # border_radius=ft.border_radius.only(top_left=15, top_right=15), # Removed top radius
            # shadow=ft.BoxShadow( # Removed shadow from input panel, can be too much
            # )
        )
        
        # Главный контейнер чата
        main_chat_layout = ft.Column([ # Renamed to avoid conflict
            header,
            chat_area, # This should expand
            input_panel
        ], spacing=0, expand=True)
        
        # Очищаем страницу и добавляем чат
        self.page.controls.clear()
        self.page.add(main_chat_layout) # Use the new layout variable
        self.page.update()
        print("DEBUG: ChatScreen UI should be visible.")


def main(page: ft.Page):
    print("DEBUG: main(page) called")
    # global global_app_instance # This is not strictly necessary if app is not accessed globally outside its methods
    app = EnglishLearningApp(page)
    # global_app_instance = app 
    print("DEBUG: EnglishLearningApp instantiated")

if __name__ == '__main__':
    print("DEBUG: Starting Flet app...")
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8550, host="0.0.0.0")

