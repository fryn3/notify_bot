# ntfy

Минимальный Telegram-бот для отправки уведомлений. Принимает сообщения через HTTP API и CLI, отправляет в личные сообщения.

## Возможности

- **CLI** — команда `ntfy` для скриптов и пайплайнов (работает без сервера)
- **HTTP API** — `POST /notify` для интеграции с сервисами
- **Простые уведомления** — текстовые сообщения ("сборка завершена")
- **Markdown** — форматированные сообщения (MarkdownV2)
- **Отчёты AI-агентов** — структурированные данные, которые бот форматирует в Markdown

## Быстрый старт

### 1. Установка

```bash
cp .env.example .env
# Заполни BOT_TOKEN и CHAT_ID в .env

pip install -e .
```

### 2. Получение токена и chat_id

1. Создай бота через [@BotFather](https://t.me/BotFather) — получишь `BOT_TOKEN`
2. Напиши боту `/start`
3. Узнай свой `CHAT_ID` через [@userinfobot](https://t.me/userinfobot) или API:
   ```bash
   curl https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

### 3. Использование CLI

Команда `ntfy` отправляет уведомления напрямую через Telegram API — сервер не нужен.

```bash
# Простой текст
ntfy "Build completed"

# Чтение из stdin
echo "Deploy finished" | ntfy -

# Markdown
ntfy --md "**Build** _passed_ on \`main\`"

# Структурированный отчёт
ntfy --report --title "Agent Run" --status success \
  --summary "Refactored auth" \
  --detail "Removed 3 endpoints" \
  --detail "Added JWT refresh" \
  --duration "4m 32s"

# Отчёт из JSON (stdin)
echo '{"title":"Agent Run","status":"success","summary":"Done"}' | ntfy --report-json
```

### 4. Запуск сервера (опционально)

```bash
ntfy-server
```

Стартует HTTP API на `0.0.0.0:8000` и Telegram bot polling.

## HTTP API

### POST /notify

**Простое текстовое сообщение:**

```bash
curl -X POST localhost:8000/notify \
  -H 'Content-Type: application/json' \
  -d '{"message": "Build completed!"}'
```

**Markdown:**

```bash
curl -X POST localhost:8000/notify \
  -H 'Content-Type: application/json' \
  -d '{"message": "**Build** _passed_ on `main`", "format": "markdown"}'
```

**Структурированный отчёт:**

```bash
curl -X POST localhost:8000/notify \
  -H 'Content-Type: application/json' \
  -d '{
    "format": "report",
    "report": {
      "title": "Agent Run Complete",
      "status": "success",
      "summary": "Refactored auth module",
      "details": ["Removed 3 deprecated endpoints", "Added JWT refresh"],
      "duration": "4m 32s"
    }
  }'
```

**Формат ответа:**

```json
{ "ok": true }
{ "ok": false, "error": "описание ошибки" }
```

### Схема запроса

| Поле      | Тип                              | По умолчанию | Описание                          |
|-----------|----------------------------------|--------------|-----------------------------------|
| `message` | `string`                         | —            | Текст сообщения                   |
| `format`  | `"text" \| "markdown" \| "report"` | `"text"`     | Формат сообщения                  |
| `report`  | `object`                         | —            | Данные отчёта (при `format=report`) |

### Схема отчёта (report)

| Поле       | Тип        | По умолчанию | Описание                         |
|------------|------------|--------------|----------------------------------|
| `title`    | `string`   | —            | Заголовок отчёта                 |
| `status`   | `string`   | `"info"`     | `success`, `failure` или `info`  |
| `summary`  | `string`   | —            | Краткое описание                 |
| `details`  | `string[]` | `[]`         | Список деталей                   |
| `duration` | `string`   | —            | Длительность выполнения          |

## Примеры с пайпами

При пайпе `ntfy` по умолчанию берёт последние 5 строк вывода и оборачивает в code block (MarkdownV2). Флаги-модификаторы:

- `-n 10` — количество строк (по умолчанию 5)
- `--header "текст"` — заголовок над code block
- `--raw` — отправить весь вывод как plain text, без code block
- `--md` — отправить весь вывод как MarkdownV2

> Многие инструменты (`make`, `pytest`, `docker build`) пишут в stderr — используй `2>&1`, чтобы захватить весь вывод.

### Сборка и деплой

```bash
qb build 2>&1 | ntfy --header "qb build"
make build 2>&1 | ntfy --header "make build"
docker build . 2>&1 | ntfy -n 3
make deploy 2>&1 | ntfy --header "deploy"
```

### Тесты

```bash
pytest 2>&1 | ntfy --header "pytest"
pytest 2>&1 | ntfy --raw              # полный вывод, без code block
pytest 2>&1 | ntfy -n 15              # последние 15 строк
go test ./... 2>&1 | ntfy --header "go test"
```

### Логи и мониторинг

```bash
docker logs app --tail 50 | ntfy --header "docker logs"
journalctl -u myservice -n 20 | ntfy
kubectl logs deploy/api --tail 30 | ntfy --header "k8s api"
```

### Произвольные команды

```bash
df -h | ntfy --header "disk usage"
git log --oneline -5 | ntfy --header "git log"
curl -s https://example.com/health | ntfy --header "healthcheck"
```

## Интеграция с Claude Code

[Claude Code](https://claude.com/claude-code) поддерживает хуки — shell-команды, которые запускаются на определённых этапах работы. С `ntfy` можно получать Telegram-уведомления, когда Claude завершает задачу.

### Хуки

Добавь хук `Stop` в `.claude/settings.json` (на уровне проекта) или `~/.claude/settings.json` (глобально):

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "ntfy 'Claude Code: задача завершена'"
          }
        ]
      }
    ]
  }
}
```

Вариант со структурированным отчётом:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "ntfy --report --title 'Claude Code' --status success --summary 'Задача завершена'"
          }
        ]
      }
    ]
  }
}
```

### Использование в скриптах

```bash
# Уведомление после завершения задачи
claude -p "Refactor auth module" && ntfy "Claude: готово" || ntfy "Claude: ошибка"

# Вывод Claude в Telegram
claude -p "Run all tests" 2>&1 | ntfy --header "Claude Code"

# Отчёт по результату
claude -p "Fix the bug in parser" && \
  ntfy --report --title "Claude Code" --status success --summary "Баг исправлен" || \
  ntfy --report --title "Claude Code" --status failure --summary "Не удалось исправить"
```

## Конфигурация

Через переменные окружения или файл `.env`:

| Переменная | Обязательная | По умолчанию | Описание                   |
|------------|--------------|--------------|----------------------------|
| `BOT_TOKEN`| Да          | —            | Токен Telegram-бота        |
| `CHAT_ID`  | Да          | —            | ID чата для отправки       |
| `API_HOST` | Нет         | `0.0.0.0`   | Хост HTTP API              |
| `API_PORT` | Нет         | `8000`       | Порт HTTP API              |
| `PROXY`    | Нет         | —            | Прокси для Telegram API (`socks5://...`, `http://...`) |

## Структура проекта

```
notify_bot/
├── pyproject.toml          # Зависимости и метаданные
├── .env.example            # Шаблон переменных окружения
├── notify_bot/
│   ├── config.py           # Загрузка конфигурации из env
│   ├── bot.py              # Aiogram Bot + send_notification()
│   ├── formatting.py       # MarkdownV2 форматирование отчётов
│   ├── api.py              # FastAPI: POST /notify
│   └── main.py             # Entrypoint: uvicorn + aiogram polling
└── notify_cli.py           # Standalone CLI утилита
```
