Эмулятор оболочки ОС (этапы 1–3)

Проект реализует GUI-эмулятор командной оболочки на Python с помощью
`tkinter`. VFS загружается из ZIP-архива в память. Архив не распаковывается
на диск, а `vfs-save` записывает сохранённые исходные байты ZIP в указанный
файл.

## Реализовано

### Этап 1. REPL
- GUI с заголовком, содержащим имя VFS.
- Разбор команды и аргументов через `shlex.split`, включая кавычки.
- Заглушки `ls` и `cd`, печатающие команду и аргументы.
- `exit` для завершения работы.
- Сообщения об неизвестных командах и неверных аргументах.

### Этап 2. Конфигурация
- `--vfs PATH` — путь к ZIP-архиву VFS.
- `--log PATH` — путь к XML-журналу.
- `--script PATH` — стартовый скрипт.
- Параметры запуска выводятся в консоль в формате ключ–значение.
- В XML записываются вызовы команд, аргументы, статус, сообщение,
  дата и время события.
- Стартовый скрипт показывает ввод и вывод; пустые строки и строки,
  начинающиеся с `#`, пропускаются. При первой ошибке скрипт останавливается.

### Этап 3. VFS
- ZIP читается в память и не извлекается на диск.
- `vfs-info` показывает список элементов архива.
- `vfs-save PATH` сохраняет ZIP в исходном бинарном формате.
- Если `--vfs` не указан, создаётся пустой ZIP в памяти.

## Требования
- Python 3.10 или новее.
- `tkinter` (обычно включён в стандартную поставку Python; в Linux может
  потребоваться системный пакет `python3-tk`).

## Запуск

Из корня проекта:

```bash
python -m src.main
python -m src.main --vfs testdata/nested.zip
python -m src.main --vfs testdata/multiple.zip --log logs/run.xml
python -m src.main --vfs testdata/nested.zip --log logs/run.xml --script scripts/startup_demo.txt
python -m src.main --vfs testdata/nested.zip --log logs/error.xml --script scripts/startup_error.txt
```

На Windows замените `python` при необходимости на `py`.

## Команды
- `ls [аргументы]` — заглушка этапа 1.
- `cd [аргументы]` — заглушка этапа 1.
- `vfs-info` — показать элементы ZIP-архива.
- `vfs-save PATH` — сохранить ZIP-архив в исходном формате.
- `exit` — завершить работу.
- `help` — показать краткую подсказку.

Пути в командах `vfs-save` с пробелами можно заключать в кавычки.

## Тестирование

```bash
python -m unittest discover -s tests -v
```

Скрипты запуска для Linux/macOS находятся в `scripts/*.sh`, для Windows —
в `scripts/*.bat`. Скрипты используют разные варианты VFS из `testdata/`.

## Примеры ZIP-VFS
- `minimal.zip` — пустой архив.
- `multiple.zip` — несколько файлов.
- `nested.zip` — вложенность не менее трёх уровней.

## Пример коммитов по этапам

```bash
git add README.md .gitignore src tests scripts testdata
git commit -m "feat(stage-1): add GUI shell REPL"
git commit --allow-empty -m "feat(stage-2): add CLI config and XML logging"
git commit --allow-empty -m "feat(stage-3): add in-memory ZIP VFS"
```

