import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import ffmpeg
from tqdm import tqdm


class VideoCompressorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VideoRazor V1.0 by CTumak")
        self.root.geometry("600x600")

        # Переменные
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.current_video = tk.StringVar()
        self.video_count = tk.StringVar()
        self.progress = tk.DoubleVar()
        self.mode = tk.StringVar(value="default")  # Режим: default или advanced

        # Переменные для продвинутых настроек
        self.codec = tk.StringVar(value="libx264")  # Кодек (по умолчанию)
        self.crf = tk.StringVar(value="23")  # CRF (по умолчанию)
        self.bitrate = tk.StringVar(value="0")  # Битрейт (по умолчанию)
        self.preset = tk.StringVar(value="fast")  # Скорость кодирования (по умолчанию)

        # Флаг для блокировки кнопки
        self.is_compressing = False

        # Интерфейс
        self.create_ui()

    def create_ui(self):
        # Выбор режима
        tk.Label(self.root, text="Режим сжатия:").pack(pady=5)
        tk.Radiobutton(self.root, text="Оптимальные параметры", variable=self.mode, value="default",
                       command=self.update_ui).pack(anchor=tk.W)
        tk.Radiobutton(self.root, text="Для продвинутых", variable=self.mode, value="advanced",
                       command=self.update_ui).pack(anchor=tk.W)

        # Выбор входного файла/папки
        tk.Label(self.root, text="Выберите файл или папку с видео:").pack(pady=5)
        tk.Entry(self.root, textvariable=self.input_path, width=50).pack(pady=5)
        tk.Button(self.root, text="Выбор файлов", command=self.select_input).pack(pady=5)

        # Выбор папки для сохранения
        tk.Label(self.root, text="Выберите папку для сохранения:").pack(pady=5)
        tk.Entry(self.root, textvariable=self.output_path, width=50).pack(pady=5)
        tk.Button(self.root, text="Обзор", command=self.select_output).pack(pady=5)

        # Продвинутые настройки (скрыты по умолчанию)
        self.advanced_frame = tk.Frame(self.root)
        self.advanced_frame.pack(pady=10, fill=tk.X, expand=True)

        tk.Label(self.advanced_frame, text="Кодек:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Combobox(self.advanced_frame, textvariable=self.codec, values=["libx264", "libx265", "libvpx-vp9"]).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self.advanced_frame, text="CRF (18-28):").grid(row=1, column=0, padx=5, pady=5)
        tk.Entry(self.advanced_frame, textvariable=self.crf, width=10).grid(row=1, column=1, padx=5, pady=5)

        tk.Label(self.advanced_frame, text="Битрейт (например, 1M):").grid(row=2, column=0, padx=5, pady=5)
        tk.Entry(self.advanced_frame, textvariable=self.bitrate, width=10).grid(row=2, column=1, padx=5, pady=5)

        tk.Label(self.advanced_frame, text="Скорость кодирования:").grid(row=3, column=0, padx=5, pady=5)
        ttk.Combobox(self.advanced_frame, textvariable=self.preset, values=["ultrafast", "superfast", "veryfast",
                                                                           "faster", "fast", "medium", "slow",
                                                                           "slower", "veryslow"]).grid(row=3, column=1,
                                                                                                       padx=5, pady=5)

        # Прогресс-бар
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=10)

        # Информация о текущем видео
        tk.Label(self.root, textvariable=self.current_video).pack(pady=5)
        tk.Label(self.root, textvariable=self.video_count).pack(pady=5)

        # Кнопка запуска
        self.compress_button = tk.Button(self.root, text="Сжать видео", command=self.start_compression)
        self.compress_button.pack(pady=20)

        # Метка для сообщения
        self.status_label = tk.Label(self.root, text="", fg="red")
        self.status_label.pack(pady=5)

        # Инициализация интерфейса
        self.update_ui()

    def update_ui(self):
        """Обновление интерфейса в зависимости от выбранного режима."""
        if self.mode.get() == "default":
            self.advanced_frame.pack_forget()  # Скрыть продвинутые настройки
        elif self.mode.get() == "advanced":
            self.advanced_frame.pack()  # Показать продвинутые настройки

    def select_input(self):
        """Выбор входного файла или папки."""
        # Спрашиваем пользователя, хочет ли он выбрать папку
        if messagebox.askyesno("Выбор типа ввода", "Вы хотите выбрать папку? (Нет — файл)"):
            path = filedialog.askdirectory()  # Выбор папки
        else:
            path = filedialog.askopenfilename(filetypes=[("Видео файлы", "*.mp4;*.avi;*.mkv;*.mov")])  # Выбор файла
        if path:
            self.input_path.set(path)

    def select_output(self):
        """Выбор папки для сохранения."""
        path = filedialog.askdirectory()
        if path:
            self.output_path.set(path)

    def start_compression(self):
        """Запуск сжатия видео."""
        input_path = self.input_path.get()
        output_path = self.output_path.get()

        if not input_path or not output_path:
            messagebox.showerror("Ошибка", "Пожалуйста, выберите входные и выходные пути.")
            return

        # Блокируем кнопку и показываем сообщение
        self.compress_button.config(state=tk.DISABLED)
        self.status_label.config(text="Начался процесс сжатия, пожалуйста, не закрывайте программу")

        if os.path.isfile(input_path):
            # Запуск сжатия в отдельном потоке
            threading.Thread(target=self.compress_video, args=(input_path, output_path), daemon=True).start()
        elif os.path.isdir(input_path):
            # Запуск сжатия папки в отдельном потоке
            threading.Thread(target=self.compress_folder, args=(input_path, output_path), daemon=True).start()
        else:
            messagebox.showerror("Ошибка", "Неверный путь.")

    def compress_folder(self, input_folder, output_folder):
        """Сжатие всех видео в папке."""
        videos = [f for f in os.listdir(input_folder) if f.endswith((".mp4", ".avi", ".mkv", ".mov"))]
        total_videos = len(videos)
        self.video_count.set(f"Всего видео: {total_videos}")

        for i, video in enumerate(videos, 1):
            input_file = os.path.join(input_folder, video)
            output_file = os.path.join(output_folder, video)
            self.current_video.set(f"Сжимается: {video} ({i}/{total_videos})")
            self.compress_video(input_file, output_file)
            self.progress.set((i / total_videos) * 100)

        # Восстанавливаем кнопку и скрываем сообщение
        self.compress_button.config(state=tk.NORMAL)
        self.status_label.config(text="")
        messagebox.showinfo("Готово", "Все видео сжаты!")

    def compress_video(self, input_file, output_file):
        """Сжатие одного видео."""
        try:
            # Используем FFmpeg для сжатия
            ffmpeg_args = {
                "vcodec": self.codec.get() if self.mode.get() == "advanced" else "libx264",
                "pix_fmt": "yuv420p",
                "crf": self.crf.get() if self.mode.get() == "advanced" else "23",
                "b:v": self.bitrate.get() if self.mode.get() == "advanced" and self.bitrate.get() else None,
                "preset": self.preset.get() if self.mode.get() == "advanced" else "fast"
            }

            stream = ffmpeg.input(input_file)
            stream = ffmpeg.output(stream, output_file, **{k: v for k, v in ffmpeg_args.items() if v})
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
        except Exception as e:
            # Восстанавливаем кнопку и скрываем сообщение
            self.compress_button.config(state=tk.NORMAL)
            self.status_label.config(text="")
            messagebox.showerror("Ошибка", f"Ошибка при сжатии видео: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoCompressorApp(root)
    root.mainloop()