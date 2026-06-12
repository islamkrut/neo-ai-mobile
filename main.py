Import customtkinter as ctk
import g4f
import threading
import requests
import urllib.parse
from PIL import Image
from io import BytesIO
from tkinter import messagebox
import speech_recognition as sr
import random
import os

ctk.set_appearance_mode("dark")

class NeoAI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Переименовали ИИ в Neo-AI
        self.title("Neo-AI (Stable Text Edition)")
        self.geometry("1250x900")
        
        self.accent_color = "#00FF00"
        self.bg_color = "#080808"
        self.configure(fg_color=self.bg_color) 
        
        # Хранилище данных чатов и памяти
        self.chats = {"Чат 1": []}  
        self.current_chat = "Чат 1"
        self.is_typing = False
        self.is_recording = False 

        # Загрузка кастомного логотипа (убедись, что картинка лежит рядом под именем logo.png)
        self.logo_path = "logo.png"
        self.ctk_logo_img = None
        if os.path.exists(self.logo_path):
            try:
                raw_logo = Image.open(self.logo_path)
                # Масштабируем логотип для красивого отображения по центру
                self.ctk_logo_img = ctk.CTkImage(raw_logo, size=(550, 366)) 
            except Exception as e:
                print(f"Не удалось загрузить логотип: {e}")

        # Главная сетка окна
        self.grid_columnconfigure(0, weight=0) 
        self.grid_columnconfigure(1, weight=1) 
        self.grid_rowconfigure(0, weight=1)

        self.recognizer = sr.Recognizer()

        # --- SIDEBAR (Боковая панель) ---
        self.sidebar = ctk.CTkFrame(self, width=200, fg_color="#0a0a0a", corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.new_chat_btn = ctk.CTkButton(self.sidebar, text="+ NEW SESSION", fg_color="transparent", border_width=1, border_color=self.accent_color, command=self.create_new_chat)
        self.new_chat_btn.pack(pady=20, padx=10, fill="x")

        self.chat_list_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent", label_text="SESSIONS")
        self.chat_list_frame.pack(expand=True, fill="both", padx=5, pady=5)
        self.chat_buttons = {}
        self.render_chat_list()

        # --- MAIN AREA (Главная зона) ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(2, weight=1) 

        # Хедер и верхняя панель управления
        self.top_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", pady=10)
        
        self.header = ctk.CTkLabel(self.top_bar, text=">> SYSTEM ACTIVE", font=("Consolas", 24, "bold"), text_color=self.accent_color)
        self.header.pack(side="left")

        # КНОПКА КОПИРОВАНИЯ ВЫДЕЛЕННОГО ФРАГМЕНТА
        self.copy_sel_btn = ctk.CTkButton(
            self.top_bar, 
            text="✂️ Скопировать выделенное", 
            width=180, 
            fg_color="#111", 
            border_width=1, 
            border_color=self.accent_color, 
            command=self.copy_selected_or_all
        )
        self.copy_sel_btn.pack(side="right", padx=10)

        # Контроллеры режимов
        self.top_controls = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.top_controls.grid(row=1, column=0, pady=5, sticky="w")

        self.mode_switch = ctk.CTkSegmentedButton(self.top_controls, values=["Чат", "Картинка"], selected_color=self.accent_color, command=self.switch_mode)
        self.mode_switch.set("Чат")
        self.mode_switch.pack(side="left", padx=10)

        self.style_dropdown = ctk.CTkOptionMenu(self.top_controls, values=["Realism", "Cyberpunk", "Anime", "Cinematic", "No Style"], fg_color="#111", button_color=self.accent_color)
        self.style_dropdown.set("Realism")
        self.style_dropdown.pack(side="left", padx=10)

        # РЕЖИМ КОДА (Code Mode)
        self.code_mode_switch = ctk.CTkSwitch(self.top_controls, text="РЕЖИМ КОДА", progress_color=self.accent_color, font=("Consolas", 12, "bold"))
        self.code_mode_switch.pack(side="left", padx=20)

        # Текстовое поле вывода данных
        self.textbox = ctk.CTkTextbox(self.main_container, fg_color="#0f0f0f", border_color=self.accent_color, border_width=1, text_color=self.accent_color, font=("Consolas", 14))
        self.textbox.grid(row=2, column=0, sticky="nsew", pady=10)
        self.textbox.configure(state="disabled") 
        
        # Биндинги для выделения текста
        self.textbox.bind("<Control-c>", lambda e: self.copy_selected_or_all())
        self.textbox.bind("<Control-a>", lambda e: self.select_all_text())

        # Поле для вывода сгенерированных картинок / Логотипа
        self.image_label = ctk.CTkLabel(self.main_container, text="", fg_color="#0f0f0f")
        if self.ctk_logo_img:
            self.image_label.configure(image=self.ctk_logo_img)
        
        self.progress_bar = ctk.CTkProgressBar(self.main_container, progress_color=self.accent_color)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=3, column=0, sticky="ew", pady=5)
        self.progress_bar.grid_remove()

        # --- INPUT AREA (Поле ввода) ---
        self.input_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.input_container.grid(row=4, column=0, pady=20, sticky="ew")
        self.input_container.grid_columnconfigure(0, weight=1)

        # Панель быстрых утилит над строкой ввода
        self.utils_frame = ctk.CTkFrame(self.input_container, fg_color="transparent")
        self.utils_frame.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 5))
        
        self.paste_btn = ctk.CTkButton(self.utils_frame, text="📋 Вставить из буфера", height=25, font=("Consolas", 11), fg_color="#161616", command=self.paste_to_entry)
        self.paste_btn.pack(side="left", padx=(0, 10))
        
        self.clear_btn = ctk.CTkButton(self.utils_frame, text="🗑️ Очистить строку", height=25, font=("Consolas", 11), fg_color="#161616", command=lambda: self.entry.delete(0, "end"))
        self.clear_btn.pack(side="left")

        # Основная строка управления и кнопки
        self.input_frame = ctk.CTkFrame(self.input_container, fg_color="transparent")
        self.input_frame.grid(row=1, column=0, sticky="ew")
        self.input_frame.grid_columnconfigure(1, weight=1)

        self.voice_btn = ctk.CTkButton(self.input_frame, text="🎤", width=40, height=50, fg_color="#111", border_width=1, border_color=self.accent_color, font=("Consolas", 20), command=self.toggle_voice_input)
        self.voice_btn.grid(row=0, column=0, padx=(0, 10))

        self.entry = ctk.CTkEntry(self.input_frame, placeholder_text="Напишите ваш вопрос для Neo-AI здесь...", height=50, border_color=self.accent_color, fg_color="#111")
        self.entry.grid(row=0, column=1, padx=(0, 10), sticky="ew")
        self.entry.bind("<Return>", lambda e: self.start_action())
        self.entry.bind("<Control-a>", lambda e: self.entry.select_range(0, 'end'))

        self.btn = ctk.CTkButton(self.input_frame, text="EXECUTE", width=120, height=50, fg_color=self.accent_color, text_color="black", font=("Impact", 16), command=self.start_action)
        self.btn.grid(row=0, column=2)

    # --- УМНОЕ КОПИРОВАНИЕ ФРАГМЕНТОВ ИЛИ ВСЕГО ТЕКСТА ---
    def copy_selected_or_all(self):
        try:
            selected_text = self.textbox.get("sel.first", "sel.last").strip()
            if selected_text:
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                self.show_status_msg("ФРАГМЕНТ СКОПИРОВАН")
                return "break" 
        except Exception:
            pass

        all_text = self.textbox.get("1.0", "end-1c").strip()
        if all_text:
            self.clipboard_clear()
            self.clipboard_append(all_text)
            self.show_status_msg("ВЕСЬ ТЕКСТ СКОПИРОВАН")
        else:
            messagebox.showwarning("Neo-AI", "Окно вывода пустое, нечего копировать.")
        return "break"

    def select_all_text(self):
        self.textbox.tag_add("sel", "1.0", "end")
        return "break"

    def show_status_msg(self, msg):
        current_header = self.header.cget("text")
        self.header.configure(text=f">> {msg} <<", text_color="#FFFFFF")
        self.after(1500, lambda: self.header.configure(text=current_header, text_color=self.accent_color))

    def paste_to_entry(self):
        try:
            clipboard_text = self.clipboard_get()
            self.entry.insert("end", clipboard_text)
        except Exception:
            messagebox.showwarning("Neo-AI", "Буфер обмена пуст.")

    def start_action(self):
        if self.is_typing or self.is_recording: return
        prompt = self.entry.get().strip()
        if not prompt: return
        
        mode = self.mode_switch.get()
        self.btn.configure(state="disabled")
        self.new_chat_btn.configure(state="disabled") 
        self.voice_btn.configure(state="disabled") 
        self.progress_bar.grid()
        self.progress_bar.start()
        self.is_typing = True

        if mode == "Чат":
            threading.Thread(target=self.process_chat_with_memory, args=(prompt,), daemon=True).start()
        else:
            threading.Thread(target=self.run_ai_painter, args=(prompt,), daemon=True).start()
        
        self.entry.delete(0, "end")

    # --- ЦИКЛ ОБРАБОТКИ ТЕКСТА ---
    def process_chat_with_memory(self, user_text):
        try:
            self.after(0, lambda: self.write_to_textbox(f">>> {user_text}\n"))
            
            final_prompt = user_text
            if self.code_mode_switch.get():
                final_prompt = f"Ты работаешь в строгом РЕЖИМЕ КОДА. Выдавай только чистый код, скрипты или технические инструкции. Не пиши приветствий, вежливых фраз и лишних объяснений. Вот задача: {user_text}"

            self.chats[self.current_chat].append({"role": "user", "content": final_prompt})
            
            models_pool = [
                g4f.models.gpt_4o,
                g4f.models.llama_3_1_70b,
                g4f.models.default
            ]
            
            response = None
            for model in models_pool:
                try:
                    response = g4f.ChatCompletion.create(
                        model=model, 
                        messages=self.chats[self.current_chat],
                        timeout=8
                    )
                    if response and len(str(response).strip()) > 0:
                        break
                except Exception:
                    continue
            
            if not response:
                raise Exception("Шлюзы перегружены. Попробуйте нажать EXECUTE еще раз.")

            self.chats[self.current_chat].append({"role": "assistant", "content": response})
            self.after(0, lambda: self.typewriter_effect(f"RESP: {response}", target_chat=self.current_chat))
        except Exception as e:
            self.after(0, lambda: self.write_to_textbox(f"ERR: {e}\n\n"))
            self.after(0, self.unlock_ui)

    def write_to_textbox(self, text):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", text)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    # --- ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ ---
    def run_ai_painter(self, prompt):
        try:
            style = self.style_dropdown.get()
            style_prompt = f", {style} style" if style != "No Style" else ""
            full_prompt = f"{prompt}{style_prompt}, masterpiece, 8k resolution, highly detailed"
            encoded = urllib.parse.quote(full_prompt)
            
            url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&model=flux&nologo=true&seed={random.randint(1,999999)}"
            
            res = requests.get(url, timeout=60)
            if res.status_code == 200:
                img = Image.open(BytesIO(res.content))
                ctk_img = ctk.CTkImage(img, size=(550, 550))
                self.after(0, lambda: self.image_label.configure(image=ctk_img, text=""))
            else:
                raise Exception(f"Ошибка сервера: Статус {res.status_code}")
        except Exception as e:
            self.after(0, lambda: self.image_label.configure(text=f"ERROR: {e}"))
        finally:
            self.after(0, self.unlock_ui)

    # --- ГОЛОСОВОЙ ВВОД ---
    def toggle_voice_input(self):
        if self.is_typing: return
        if not self.is_recording:
            self.is_recording = True
            self.voice_btn.configure(fg_color="#FF0000", text_color="white", text="🛑")
            self.entry.configure(placeholder_text="Слушаю вас... Говорите...")
            threading.Thread(target=self.record_voice, daemon=True).start()
        else:
            self.is_recording = False

    def record_voice(self):
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                if not self.is_recording: return
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=15)
            if self.is_recording:
                text = self.recognizer.recognize_google(audio, language="ru-RU")
                self.after(0, lambda: self.entry.insert("end", f" {text}"))
        except Exception:
            pass
        finally:
            self.after(0, self.reset_voice_button)

    def reset_voice_button(self):
        self.is_recording = False
        self.voice_btn.configure(fg_color="#111", text_color=self.accent_color, text="🎤")
        self.entry.configure(placeholder_text="Напишите ваш вопрос для Neo-AI здесь...")

    def unlock_ui(self):
        self.is_typing = False
        self.btn.configure(state="normal")
        self.new_chat_btn.configure(state="normal")
        self.voice_btn.configure(state="normal") 
        self.progress_bar.stop()
        self.progress_bar.grid_remove()

    def switch_mode(self, mode):
        self.image_label.grid_forget()
        self.textbox.grid_forget()
        if mode == "Чат":
            self.textbox.grid(row=2, column=0, sticky="nsew", pady=10)
        else:
            # При переключении в режим рисования, если еще ничего не создано, возвращаем наш логотип
            if self.ctk_logo_img and self.image_label.cget("image") is None:
                self.image_label.configure(image=self.ctk_logo_img)
            self.image_label.grid(row=2, column=0, pady=10)

    def typewriter_effect(self, text, index=0, target_chat=None):
        if target_chat and target_chat != self.current_chat:
            self.unlock_ui()
            return
        if index < len(text):
            self.textbox.configure(state="normal")
            self.textbox.insert("end", text[index])
            self.textbox.see("end")
            self.textbox.configure(state="disabled")
            self.after(4, lambda: self.typewriter_effect(text, index + 1, target_chat))
        else:
            self.textbox.configure(state="normal")
            self.textbox.insert("end", "\n\n")
            self.textbox.configure(state="disabled")
            self.unlock_ui()

    def create_new_chat(self):
        if self.is_typing or self.is_recording: return
        name = f"Чат {len(self.chats) + 1}"
        self.chats[name] = []
        self.render_chat_list()
        self.select_chat(name)

    def render_chat_list(self):
        for btn in self.chat_buttons.values(): 
            btn.destroy()
        self.chat_buttons.clear()
        
        for name in self.chats.keys():
            is_selected = (name == self.current_chat)
            btn = ctk.CTkButton(
                self.chat_list_frame, 
                text=name, 
                fg_color="#222" if is_selected else "#1a1a1a",
                border_width=1 if is_selected else 0,
                border_color=self.accent_color if is_selected else "transparent",
                command=lambda n=name: self.select_chat(n)
            )
            btn.pack(fill="x", pady=4, padx=5)
            self.chat_buttons[name] = btn

    def select_chat(self, name):
        if self.is_typing or self.is_recording: return 
        self.current_chat = name
        
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        
        for msg in self.chats[name]:
            prefix = ">>> " if msg["role"] == "user" else "RESP: "
            content = msg["content"]
            if "Ты работаешь в строгом РЕЖИМЕ КОДА" in content:
                content = content.split("Вот задача: ")[-1]
            self.textbox.insert("end", f"{prefix}{content}\n\n")
            
        self.textbox.configure(state="disabled")
        self.header.configure(text=f">> SESSION: {name.upper()}")
        self.render_chat_list()

if __name__ == "__main__":
    app = NeoAI()
    app.mainloop()
