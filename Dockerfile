# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливем рабочую директорию в контейнере
WORKDIR /app

# Установить зависимости для сборки C расширений
RUN apt-get update && \
    apt-get install -y gcc libportaudio2 libportaudiocpp0 portaudio19-dev python3-venv && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Настраиваем виртуальное окружение
RUN python3 -m venv venv

# Активируем виртуальное окружение и обновляем pip
ENV PATH="/app/venv/bin:$PATH"
RUN pip install --upgrade pip

# Копируем файл с зависимостями и устанавливаем их в виртуальное окружение
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект внутрь контейнера
COPY . .

# Экспорт порта
EXPOSE 8550

# Команда для запуска Flet-приложения в веб-режиме.
CMD ["python", "main_flet.py"]
