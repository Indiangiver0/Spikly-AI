# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Установить зависимости для сборки C расширений
RUN apt-get update && \
    apt-get install -y gcc libportaudio2 libportaudiocpp0 portaudio19-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Копируем файл с зависимостями и устанавливаем их
# Убедитесь, что flet и другие зависимости есть в requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект внутрь контейнера
COPY . .

# Flet по умолчанию запускает веб-сервер на порту 8502, если не указано иное.
# Если ваше приложение main_flet.py настроено на другой порт (например, 8550),
# измените его здесь и в команде CMD.
EXPOSE 8550

# Команда для запуска Flet-приложения в веб-режиме.
# Убедитесь, что в main_flet.py у вас есть:
# ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8550, host="0.0.0.0")
# или аналогичный запуск для веб-режима.
# Параметр --host 0.0.0.0 нужен, чтобы приложение было доступно извне контейнера.
CMD ["python", "main_flet.py"]
