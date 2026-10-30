import argparse
import datetime as dt
import io
import os
import shlex
import socket
import sys
import tkinter as tk
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from tkinter.scrolledtext import ScrolledText


APP_NAME = "Эмулятор"
DEFAULT_VFS_NAME = "default-vfs.zip"


def parse_args():
    """Разбирает параметры запуска приложения."""
    parser = argparse.ArgumentParser(
        description="Эмулятор оболочки ОС — вариант 18."
    )
    parser.add_argument(
        "--vfs",
        default=None,
        help="путь к ZIP-архиву виртуальной файловой системы",
    )
    parser.add_argument(
        "--log",
        default="emulator-log.xml",
        help="путь к XML-файлу журнала событий",
    )
    parser.add_argument(
        "--script",
        default=None,
        help="путь к стартовому скрипту эмулятора",
    )
    return parser.parse_args()


class VirtualFileSystem:
    """Хранит ZIP-архив VFS в памяти и сохраняет его без распаковки."""

    def __init__(self, archive_path=None):
        self.archive_path = archive_path
        self.archive_name = (
            Path(archive_path).name if archive_path else DEFAULT_VFS_NAME
        )
        self.archive_bytes = self._load_archive(archive_path)

    @staticmethod
    def _empty_archive():
        """Создаёт пустой ZIP-архив в памяти."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED):
            pass
        return buffer.getvalue()

    def _load_archive(self, archive_path):
        """Загружает и проверяет ZIP-архив, не извлекая его на диск."""
        if not archive_path:
            return self._empty_archive()

        path = Path(archive_path)
        if not path.is_file():
            raise FileNotFoundError(
                f"Файл VFS не найден: {archive_path}"
            )

        data = path.read_bytes()
        try:
            with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
                bad_file = archive.testzip()
                if bad_file:
                    raise ValueError(
                        f"Повреждён файл внутри ZIP: {bad_file}"
                    )
        except zipfile.BadZipFile as error:
            raise ValueError(
                f"Некорректный ZIP-архив VFS: {archive_path}"
            ) from error
        return data

    def save(self, destination):
        """Сохраняет исходные байты ZIP-архива в указанный путь."""
        if not destination:
            raise ValueError("Укажите путь: vfs-save путь")
        Path(destination).write_bytes(self.archive_bytes)
        return f"VFS сохранена: {destination}"

    def entries(self):
        """Возвращает список путей внутри архива для диагностики."""
        with zipfile.ZipFile(
            io.BytesIO(self.archive_bytes), "r"
        ) as archive:
            return archive.namelist()


class XmlLogger:
    """Записывает вызовы команд в XML-файл."""

    def __init__(self, log_path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if self.log_path.exists():
            try:
                self.tree = ET.parse(self.log_path)
                self.root = self.tree.getroot()
                if self.root.tag != "events":
                    raise ValueError("Корневой элемент должен быть events")
            except (ET.ParseError, ValueError):
                raise ValueError(
                    f"Некорректный XML-файл журнала: {self.log_path}"
                )
        else:
            self.root = ET.Element("events")
            self.tree = ET.ElementTree(self.root)
            self._write()

    def _write(self):
        """Записывает XML с декларацией кодировки."""
        ET.indent(self.tree, space="  ")
        self.tree.write(
            self.log_path,
            encoding="utf-8",
            xml_declaration=True,
        )

    def log(self, command, arguments, success, message):
        """Добавляет одно событие с датой и временем."""
        event = ET.SubElement(self.root, "event")
        event.set(
            "timestamp",
            dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        ET.SubElement(event, "command").text = command
        args_element = ET.SubElement(event, "arguments")
        for argument in arguments:
            ET.SubElement(args_element, "argument").text = argument
        ET.SubElement(event, "success").text = str(success).lower()
        ET.SubElement(event, "message").text = message
        self._write()


class ShellEmulator:
    """Обрабатывает команды оболочки и управляет GUI."""

    def __init__(self, vfs, logger):
        self.vfs = vfs
        self.logger = logger
        self.running = True
        self.username = os.environ.get("USER") or os.environ.get(
            "USERNAME", "user"
        )
        self.hostname = socket.gethostname()

    def prompt(self):
        """Формирует приглашение к вводу."""
        return f"{self.username}@{self.hostname}:~$ "

    def execute(self, line):
        """Разбирает и выполняет одну команду; возвращает статус и текст."""
        try:
            parts = shlex.split(line)
        except ValueError as error:
            message = f"Ошибка разбора команды: {error}"
            self.logger.log("<parse>", [line], False, message)
            return False, message

        if not parts:
            return True, ""

        command, arguments = parts[0], parts[1:]
        try:
            message = self._dispatch(command, arguments)
            success = True
        except (ValueError, OSError, KeyError) as error:
            message = f"Ошибка: {error}"
            success = False

        self.logger.log(command, arguments, success, message)
        return success, message

    def _dispatch(self, command, arguments):
        """Вызывает команду или сообщает об ошибке."""
        if command == "exit":
            if arguments:
                raise ValueError("команда exit не принимает аргументы")
            self.running = False
            return "Завершение работы."

        if command in ("ls", "cd"):
            return self._stub(command, arguments)

        if command == "vfs-save":
            if len(arguments) != 1:
                raise ValueError("использование: vfs-save путь")
            return self.vfs.save(arguments[0])

        if command == "vfs-info":
            if arguments:
                raise ValueError("команда vfs-info не принимает аргументы")
            entries = self.vfs.entries()
            if not entries:
                return f"{self.vfs.archive_name}: архив пуст"
            return (
                f"{self.vfs.archive_name}:\n"
                + "\n".join(entries)
            )

        raise ValueError(f"неизвестная команда: {command}")

    @staticmethod
    def _stub(command, arguments):
        """Заглушка для ls и cd на этапе REPL."""
        joined = " ".join(arguments)
        return f"{command}: аргументы: {joined or '(нет)'}"


class EmulatorWindow:
    """Создаёт окно приложения и запускает интерактивный цикл."""

    def __init__(self, emulator, args):
        self.emulator = emulator
        self.args = args
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} — {emulator.vfs.archive_name}")
        self.root.geometry("760x520")
        self.output = ScrolledText(
            self.root, wrap=tk.WORD, state=tk.DISABLED
        )
        self.output.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        bottom = tk.Frame(self.root)
        bottom.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.entry = tk.Entry(bottom)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", self._on_enter)
        tk.Button(
            bottom, text="Выполнить", command=self._on_enter
        ).pack(side=tk.LEFT, padx=(8, 0))
        self._print(
            f"VFS: {emulator.vfs.archive_name}\n"
            f"Пользователь: {emulator.username}\n"
            f"Компьютер: {emulator.hostname}\n"
            f"Журнал: {emulator.logger.log_path}\n"
            f"Стартовый скрипт: {args.script or '(не задан)'}\n"
            "Введите help для подсказки по доступным командам.\n"
        )
        self.entry.focus_set()
        if args.script:
            self.root.after(100, self._run_startup_script)

    def _print(self, text):
        """Добавляет текст в окно вывода."""
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def _run_command(self, line):
        """Показывает ввод и результат одной команды."""
        self._print(self.emulator.prompt() + line)
        if line.strip() == "help":
            self._print(
                "Команды: ls [аргументы], cd [аргументы], "
                "vfs-info, vfs-save путь, exit"
            )
            return True
        success, message = self.emulator.execute(line)
        if message:
            self._print(message)
        return success

    def _on_enter(self, event=None):
        """Обрабатывает команду из поля ввода."""
        line = self.entry.get()
        self.entry.delete(0, tk.END)
        success = self._run_command(line)
        if not self.emulator.running:
            self.root.destroy()
        elif not success:
            self.entry.focus_set()

    def _run_startup_script(self):
        """Выполняет скрипт; останавливается на первой ошибке."""
        script_path = Path(self.args.script)
        try:
            lines = script_path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            self._print(f"Ошибка стартового скрипта: {error}")
            return

        for number, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if not self._run_command(line):
                self._print(
                    f"Стартовый скрипт остановлен: ошибка в строке {number}."
                )
                return
            if not self.emulator.running:
                self.root.after(100, self.root.destroy)
                return

    def run(self):
        """Запускает главный цикл GUI."""
        self.root.mainloop()


def main():
    """Точка входа приложения."""
    args = parse_args()
    print("Параметры запуска:")
    print(f"  vfs = {args.vfs or '(VFS по умолчанию в памяти)'}")
    print(f"  log = {args.log}")
    print(f"  script = {args.script or '(не задан)'}")

    try:
        vfs = VirtualFileSystem(args.vfs)
        logger = XmlLogger(args.log)
    except (OSError, ValueError) as error:
        print(f"Ошибка запуска: {error}", file=sys.stderr)
        return 1

    emulator = ShellEmulator(vfs, logger)
    window = EmulatorWindow(emulator, args)
    window.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
