# 🚀 Быстрый старт

## Запуск с Docker (рекомендуется)

```bash
# 1. Клонируйте репозиторий
git clone <repository-url>
cd rsue_backend

# 2. Запустите
docker-compose up -d

# 3. Откройте в браузере
# API: http://localhost:8000/papers
```

Готово! 🎉

## Остановка

```bash
docker-compose down
```

## Просмотр логов

```bash
docker-compose logs -f
```

## Локальная разработка

```bash
# 1. Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# 2. Установите зависимости
pip install -r req.txt

# 3. Настройте PostgreSQL и создайте БД
createdb rsue

# 4. Запустите
uvicorn app.main:app --reload
```

Подробнее: см. [README.md](README.md)

