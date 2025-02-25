import sqlite3
import json

# Путь к базе данных и JSON-файлу
db_path = "D:/Dev/foodgram/backend/db.sqlite3"
json_path = "ingredients.json"

try:
    # Подключение к базе данных
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Удаление всех данных из таблицы
    cursor.execute("DELETE FROM recipes_ingredient;")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='recipes_ingredient';")
    print("Все данные из таблицы 'recipes_ingredient' удалены.")

    # Чтение JSON-файла с правильной кодировкой
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Вставка данных
    for item in data:
        cursor.execute('''
        INSERT INTO recipes_ingredient (name, measurement_unit)
        VALUES (?, ?)
        ''', (item['name'], item['measurement_unit']))

    # Сохранение изменений
    conn.commit()
    print(f"Загружено {len(data)} записей в таблицу 'recipes_ingredient'.")

except sqlite3.Error as e:
    print(f"Ошибка SQLite: {e}")

except FileNotFoundError:
    print(f"Файл {json_path} не найден.")

except json.JSONDecodeError as e:
    print(f"Ошибка в формате JSON-файла: {e}")

finally:
    if conn:
        conn.close()
        print("Соединение с базой данных закрыто.")
