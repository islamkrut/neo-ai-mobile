import flet as ft
import g4f
import threading
import requests
import urllib.parse
import random

def main(page: ft.Page):
    # Настройки окна / экрана планшета
    page.title = "Neo-AI (Stable Text Edition)"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#080808"
    page.padding = 0

    # Константы стиля
    ACCENT_COLOR = "#00FF00"
    BG_SIDEBAR = "#0a0a0a"

    # Данные приложения (Память чатов)
    chats = {"Чат 1": []}
    current_chat = ["Чат 1"] # Используем список, чтобы менять внутри функций
    is_typing = [False]

    # --- КОМПОНЕНТЫ ИНТЕРФЕЙСА ---
    
    # Хедер (Верхняя панель)
    header_text = ft.Text(">> SYSTEM ACTIVE", font_family="Consolas", size=20, color=ACCENT_COLOR, weight=ft.FontWeight.BOLD)
    
    # Поле вывода текста чата
    chat_box = ft.ListView(expand=True, spacing=10, auto_scroll=True)
    
    # Контейнер для отображения сгенерированных картинок
    image_display = ft.Image(width=450, height=450, fit=ft.ImageFit.CONTAIN, visible=False)
    
    # Индикатор загрузки (Progress Bar)
    progress_bar = ft.ProgressBar(width=400, color=ACCENT_COLOR, bgcolor="#111", visible=False)

    # Элементы управления режимами
    mode_switch = ft.SegmentedButton(
        selected={"Чат"},
        segments=[
            ft.Segment(value="Чат", label=ft.Text("Чат", color=ACCENT_COLOR)),
            ft.Segment(value="Картинка", label=ft.Text("Картинка", color=ACCENT_COLOR)),
        ],
    )
    
    style_dropdown = ft.Dropdown(
        width=150,
        value="Realism",
        options=[
            ft.dropdown.Option("Realism"),
            ft.dropdown.Option("Cyberpunk"),
            ft.dropdown.Option("Anime"),
            ft.dropdown.Option("Cinematic"),
            ft.dropdown.Option("No Style"),
        ],
        border_color=ACCENT_COLOR,
        focused_border_color=ACCENT_COLOR,
    )
    
    code_mode_switch = ft.Switch(label="РЕЖИМ КОДА", label_style=ft.TextStyle(font_family="Consolas", size=12, color=ACCENT_COLOR))

    # Поле ввода и кнопка отправки
    entry = ft.TextField(
        hint_text="Напишите ваш вопрос для Neo-AI здесь...",
        expand=True,
        border_color=ACCENT_COLOR,
        focused_border_color=ACCENT_COLOR,
        cursor_color=ACCENT_COLOR,
        text_style=ft.TextStyle(font_family="Consolas", color=ACCENT_COLOR),
    )
    
    execute_btn = ft.ElevatedButton(
        text="EXECUTE",
        color="black",
        bgcolor=ACCENT_COLOR,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)),
        width=120,
        height=50,
    )

    # --- ЛОГИКА ФУНКЦИЙ ---

    def show_status(msg):
        old_text = header_text.value
        header_text.value = f">> {msg} <<"
        header_text.color = ft.colors.WHITE
        page.update()
        
        def reset_status():
            header_text.value = old_text
            header_text.color = ACCENT_COLOR
            page.update()
        threading.Timer(1.5, reset_status).start()

    def update_ui_state(loading: bool):
        is_typing[0] = loading
        progress_bar.visible = loading
        execute_btn.disabled = loading
        entry.disabled = loading
        page.update()

    def render_chat_history():
        chat_box.controls.clear()
        active = current_chat[0]
        for msg in chats[active]:
            prefix = ">>> " if msg["role"] == "user" else "RESP: "
            content = msg["content"]
            if "Ты работаешь в строгом РЕЖИМЕ КОДА" in content:
                content = content.split("Вот задача: ")[-1]
            
            chat_box.controls.append(
                ft.Text(f"{prefix}{content}", font_family="Consolas", size=14, color=ACCENT_COLOR)
            )
        page.update()

    # Потоковая функция работы с ИИ текстом
    def ai_chat_thread(prompt):
        active = current_chat[0]
        final_prompt = prompt
        if code_mode_switch.value:
            final_prompt = f"Ты работаешь в строгом РЕЖИМЕ КОДА. Выдавай только чистый код, скрипты или технические инструкции. Не пиши приветствий и лишних объяснений. Вот задача: {prompt}"
        
        chats[active].append({"role": "user", "content": final_prompt})
        
        models_pool = [g4f.models.gpt_4o, g4f.models.llama_3_1_70b, g4f.models.default]
        response = None
        
        for model in models_pool:
            try:
                response = g4f.ChatCompletion.create(
                    model=model,
                    messages=chats[active],
                    timeout=10
                )
                if response and len(str(response).strip()) > 0:
                    break
            except Exception:
                continue
        
        if not response:
            response = "ERR: Шлюзы ИИ перегружены. Попробуйте отправить еще раз."
            
        chats[active].append({"role": "assistant", "content": response})
        
        # Эффект печатающегося текста
        def type_effect():
            chat_box.controls.append(ft.Text("RESP: ", font_family="Consolas", size=14, color=ACCENT_COLOR))
            text_control = chat_box.controls[-1]
            full_resp = response
            for i in range(1, len(full_resp) + 1):
                text_control.value = f"RESP: {full_resp[:i]}"
                page.update()
            update_ui_state(False)

        ft.app(target=type_effect)

    # Потоковая функция генерации картинок
    def ai_paint_thread(prompt):
        try:
            style = style_dropdown.value
            style_prompt = f", {style} style" if style != "No Style" else ""
            full_prompt = f"{prompt}{style_prompt}, masterpiece, 8k resolution, highly detailed"
            encoded = urllib.parse.quote(full_prompt)
            
            url = f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512&model=flux&nologo=true&seed={random.randint(1,999999)}"
            
            res = requests.get(url, timeout=30)
            if res.status_code == 200:
                image_display.src_bytes = res.content
                image_display.visible = True
                chat_box.visible = False
            else:
                show_status("ОШИБКА СЕРВЕРА КАРТИНОК")
        except Exception as e:
            show_status("СБОЙ СЕТИ")
        finally:
            update_ui_state(False)

    def start_action(e):
        if is_typing[0]: return
        prompt = entry.value.strip()
        if not prompt: return
        
        current_mode = list(mode_switch.selected)[0]
        update_ui_state(True)
        entry.value = ""
        
        if current_mode == "Чат":
            image_display.visible = False
            chat_box.visible = True
            chat_box.controls.append(ft.Text(f">>> {prompt}", font_family="Consolas", size=14, color=ACCENT_COLOR))
            page.update()
            threading.Thread(target=ai_chat_thread, args=(prompt,), daemon=True).start()
        else:
            threading.Thread(target=ai_paint_thread, args=(prompt,), daemon=True).start()

    execute_btn.on_click = start_action

    # Управление режимами вывода экрана
    def handle_mode_change(e):
        current_mode = list(mode_switch.selected)[0]
        if current_mode == "Чат":
            image_display.visible = False
            chat_box.visible = True
        else:
            chat_box.visible = False
            image_display.visible = True
        page.update()

    mode_switch.on_change = handle_mode_change

    # Управление сессиями (Боковое меню)
    sidebar_chats_container = ft.Column(spacing=5)

    def select_chat(chat_name):
        if is_typing[0]: return
        current_chat[0] = chat_name
        header_text.value = f">> SESSION: {chat_name.upper()}"
        render_chat_history()
        render_sidebar()

    def render_sidebar():
        sidebar_chats_container.controls.clear()
        for name in chats.keys():
            is_active = (name == current_chat[0])
            sidebar_chats_container.controls.append(
                ft.TextButton(
                    text=name.upper(),
                    style=ft.ButtonStyle(
                        color=ACCENT_COLOR if is_active else ft.colors.WHITE70,
                        bgcolor="#222" if is_active else "transparent"
                    ),
                    width=180,
                    on_click=lambda e, n=name: select_chat(n)
                )
            )
        page.update()

    def create_new_session(e):
        if is_typing[0]: return
        new_name = f"Чат {len(chats) + 1}"
        chats[new_name] = []
        select_chat(new_name)

    # Быстрые утилиты буфера
    def clear_entry(e):
        entry.value = ""
        page.update()

    def copy_all_text(e):
        active = current_chat[0]
        text_to_copy = ""
        for msg in chats[active]:
            text_to_copy += f"{msg['role']}: {msg['content']}\n"
        if text_to_copy:
            page.set_clipboard(text_to_copy)
            show_status("ТЕКСТ СКОПИРОВАН")

    # --- СБОРКА МАКЕТА СЕТКИ (LAYOUT) ---
    
    # Левая панель (Sidebar)
    sidebar = ft.Container(
        content=ft.Column([
            ft.ElevatedButton("+ NEW SESSION", color="black", bgcolor="transparent", 
                              style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5), side=ft.BorderSide(1, ACCENT_COLOR)),
                              width=180, on_click=create_new_session),
            ft.Text("SESSIONS:", color=ACCENT_COLOR, size=12, font_family="Consolas"),
            sidebar_chats_container
        ], spacing=15),
        width=210,
        bgcolor=BG_SIDEBAR,
        padding=15
    )

    # Правая рабочая зона (Main Area)
    main_area = ft.Container(
        content=ft.Column([
            # Хедер строка
            ft.Row([header_text, ft.IconButton(icon=ft.icons.COPY, icon_color=ACCENT_COLOR, on_click=copy_all_text, tooltip="Скопировать всё")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            # Настройки
            ft.Row([mode_switch, style_dropdown, code_mode_switch], spacing=15),
            # Контент зоны вывода
            ft.Container(content=ft.VerticalDivider(width=0), expand=True), # Распорка
            chat_box,
            image_display,
            progress_bar,
            # Быстрые кнопки над строкой
            ft.Row([
                ft.TextButton("🗑️ Очистить строку", style=ft.ButtonStyle(color=ACCENT_COLOR), on_click=clear_entry)
            ]),
            # Строка ввода в самом низу
            ft.Row([entry, execute_btn], spacing=10)
        ], expand=True),
        expand=True,
        padding=20
    )

    # Запуск экрана
    page.add(ft.Row([sidebar, main_area], expand=True))
    render_sidebar()

ft.app(target=main)
