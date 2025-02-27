# Cropper 📋

[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-brightgreen)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-in_development-yellow)](https://github.com/grigvlwork/cropper)

## Описание проекта

**Cropper** — это программа для нарезки сканированных бланков, разработанная с целью подготовки датасета для обучения нейросети. После обучения нейросеть сможет автоматически обрабатывать данные с бланков и выставлять оценки студентам.

Таким образом, программа решает проблему большого количества сканированных бланков, позволяя эффективно создавать структурированные данные для машинного обучения.

---

## Основные функции

- Полуавтоматическая нарезка изображений бланков.
- Подготовка и разметка датасета для дальнейшего обучения нейросети.


---

## Технологии

Проект был разработан с использованием следующих технологий:

- **Язык программирования**: Python 3.8+
- **Библиотеки**:
  - PyQt6 (GUI)
  - OpenCV (обработка изображений)
- **Другие зависимости**: см. файл [requirements.txt](requirements.txt)

---

## Установка

Чтобы установить проект локально, выполните следующие шаги:

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/grigvlwork/cropper.git
   ```
2. Перейдите в директорию проекта:
   ```bash
   cd cropper
   ```
3. Создайте виртуальное окружение (рекомендуется):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Для Linux/MacOS
   venv\Scripts\activate     # Для Windows
   ```
4. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
5. Запустите программу
   ```bash
   python cropper.py
   ```
## Использование
После запуска программы откроется графический интерфейс, где можно загрузить сканированные бланки и выполнить их нарезку. Детальная инструкция по использованию будет добавлена позже.

## Документация
На данный момент документации нет. Она будет добавлена в будущем.

## Вклад в проект
Мы приветствуем любой вклад в развитие проекта! Если вы хотите предложить изменения или исправить ошибки, пожалуйста, свяжитесь с автором по адресу: grigvlwork@gmail.com .

## Лицензия
Этот проект распространяется под лицензией MIT. Подробнее см. файл LICENSE .

## Автор
Григорович Владимир
GitHub: [grigvlwork](https://github.com/grigvlwork)
Email: grigvlwork@gmail.com
## Благодарности
Огромное спасибо всем, кто помогал в разработке этого проекта! Особую благодарность выражаем следующим проектам и библиотекам:

- [Python](https://www.python.org/)
- [PyQt6](https://pypi.org/project/PyQt6/)
- [OpenCV](https://opencv.org/)
