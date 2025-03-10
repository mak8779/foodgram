# Foodgram - сайт с рецептами

## О проекте
Foodgram - это веб-платформа, где пользователи могут создавать, сохранять и делиться кулинарными рецептами. Кроме того, пользователи могут подписываться на других авторов, добавлять рецепты в избранное и формировать списки покупок с возможностью их скачивания в формате PDF.

### Возможности проекта:
- Регистрация, авторизация, смена пароля, управление токенами.
- CRUD (создание, получение, обновление, удаление) рецептов.
- Получение списка ингредиентов (добавление и редактирование доступно только администраторам).
- Получение списка тэгов (изменение и добавление только для администраторов).
- Добавление рецептов в избранное и их удаление.
- Формирование списка покупок и скачивание его в PDF.
- Подписка и отписка от авторов рецептов.

👉 [Перейти на сайт Foodgram](https://foodgramic.sytes.net)

---

## Технологии
- **Python** 3.9.13
- **Django**
- **Django REST Framework**
- **React**
- **PostgreSQL**
- **Docker**

## Автор
**Тарасенко Максим Александрович**  
📌 [GitHub профиль](https://github.com/mak8779)

---

## Развертывание проекта
### 1. Развертывание с Docker
#### Локальный запуск с Docker:
1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/mak8779/foodgram.git
   cd mak8779/foodgram
   ```
2. Перейдите в директорию с файлом `docker-compose.yml`.
3. Создайте файл `.env` и заполните его на основе `example.env`.
4. Поднимите контейнеры:
   ```bash
   docker-compose up -d --build
   ```
5. Выполните миграции базы данных:
   ```bash
   docker-compose exec backend python manage.py migrate
   ```
6. Создайте суперпользователя:
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```
7. Импортируйте фикстуры (если необходимо):
   ```bash
   docker-compose exec backend python manage.py loaddata fixtures.json
   ```
8. Соберите статику:
   ```bash
   docker-compose exec backend python manage.py collectstatic --noinput
   ```
9. Запустите сервер:
   ```bash
   docker-compose up
   ```

### 2. Развертывание без Docker
1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/mak8779/foodgram.git
   cd mak8779/foodgram
   ```
2. Создайте и активируйте виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # для MacOS/Linux
   venv\Scripts\activate  # для Windows
   ```
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Создайте и заполните файл `.env` на основе `example.env`.
5. Выполните миграции базы данных:
   ```bash
   python manage.py migrate
   ```
6. Создайте суперпользователя:
   ```bash
   python manage.py createsuperuser
   ```
7. Импортируйте фикстуры или данные из CSV:
   ```bash
   python manage.py loaddata fixtures.json
   ```
8. Запустите сервер:
   ```bash
   python manage.py runserver
   ```

### Пример файла .env
example.env
```bash
POSTGRES_DB=foodgram
POSTGRES_USER=*Имя пользователя БД*
POSTGRES_PASSWORD=*Пароль пользователя БД*
DB_NAME=*Имя БД*
DB_HOST=db
DEBUG=*false для продакшена и true для тестов*
SECRET_KEY=*Секретный ключ Django*
ALLOWED_HOSTS=127.0.0.1,localhost, *доп. хосты*
```
---

## Документация API
Полное описание API доступно по адресу:
👉 [Локальный сервер API документации](http://127.0.0.1:8000/api/docs/)

