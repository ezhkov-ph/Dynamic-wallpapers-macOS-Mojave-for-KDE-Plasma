#!/usr/bin/env python3
import os
import subprocess
import shutil
import json
import requests
from datetime import datetime, timezone, timedelta
from astral import LocationInfo
from astral.geocoder import database, lookup
from astral.sun import sun
# Наша новая библиотека для определения часового пояса
from timezonefinder import TimezoneFinder

# --- НАСТРОЙКИ ---
IMAGE_PATH = os.path.expanduser("~/Изображения/Mojave")
IMAGE_PREFIX = "mojave_dynamic_"
IMAGE_EXTENSION = ".jpeg"
CONFIG_FILE = os.path.expanduser("~/.local/bin/location.json")
# --- КОНЕЦ НАСТРОЕК ---

def save_location_to_config(location_obj):
    location_data = {
        "name": location_obj.name, "region": location_obj.region,
        "timezone": location_obj.timezone, "latitude": location_obj.latitude,
        "longitude": location_obj.longitude
    }
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(location_data, f, indent=4)
    print(f"\nДанные о местоположении сохранены в: {CONFIG_FILE}")

def find_city_online(city_name):
    """Ищет город в онлайн-базе OpenStreetMap и определяет его часовой пояс."""
    print(f"Пытаюсь найти '{city_name}' в онлайн-базе OpenStreetMap...")
    try:
        # Отправляем запрос к Nominatim API (сервис OpenStreetMap)
        headers = {'User-Agent': 'MojaveWallpaperScript/1.0'}
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        results = response.json()

        if not results:
            return None # Ничего не найдено

        # Берем первый, самый релевантный результат
        data = results[0]
        lat = float(data['lat'])
        lon = float(data['lon'])

        # Определяем часовой пояс по координатам
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lng=lon, lat=lat)

        if not timezone_str:
            print("Не удалось определить часовой пояс для найденных координат.")
            return None

        # Собираем все данные вместе
        display_name = data.get('display_name', city_name).split(',')[0]
        return LocationInfo(display_name, "", timezone_str, lat, lon)

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при обращении к онлайн-сервису: {e}")
        return None

def get_location_manually():
    """Запускает ручной ввод, который сначала ищет локально, а потом онлайн."""
    print("\n--- Попытка №2: Ручной ввод ---")
    db = database()
    while True:
        try:
            city_name = input("Введите название вашего города на английском (или оставьте пустым для отмены): ")
            if not city_name: return None

            # Сначала ищем в быстрой, но ограниченной локальной базе
            try:
                location = lookup(city_name, db=db)
                print(f"Город найден в локальной базе: {location.name}, {location.region}")
                return location
            except KeyError:
                # Если в локальной базе нет - ищем онлайн!
                location = find_city_online(city_name)
                if location:
                    print(f"Город найден онлайн: {location.name} (TZ: {location.timezone})")
                    return location
                else:
                    print(f"Не удалось найти '{city_name}' ни в локальной, ни в онлайн-базе. Проверьте написание.")

        except (KeyboardInterrupt, EOFError): return None

# --- Все остальные функции остаются без изменений ---
def get_location_interactively():
    print("--- Первоначальная настройка местоположения ---")
    try:
        print("Попытка №1: Автоматическое определение по IP...")
        response = requests.get("https://ipinfo.io/json", timeout=5)
        response.raise_for_status()
        data = response.json()
        lat, lon = data['loc'].split(',')
        detected_location = LocationInfo(data.get('city'), data.get('country'), data.get('timezone'), float(lat), float(lon))
        prompt = f"Мы определили ваш город как '{detected_location.name}, {detected_location.region}'. Это верно? [Y/n]: "
        answer = input(prompt).lower().strip()
        if answer in ['', 'y', 'yes', 'д', 'да']: return detected_location
    except requests.exceptions.RequestException: print("Не удалось определить город автоматически (возможно, из-за VPN или ошибки сети).")
    return get_location_manually()

def get_location():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
            return LocationInfo(data['name'], data['region'], data['timezone'], data['latitude'], data['longitude'])
        except (json.JSONDecodeError, KeyError): os.remove(CONFIG_FILE)
    location = get_location_interactively()
    if location:
        save_location_to_config(location)
        return location
    else:
        print("\nНастройка отменена. Используются значения по умолчанию (Нижний Новгород).")
        return LocationInfo("Nizhny Novgorod", "Russia", "Europe/Moscow", 56.32, 44.00)

def set_kde_wallpaper(image_path):
    try:
        subprocess.run(['plasma-apply-wallpaperimage', image_path], check=True, capture_output=True, text=True)
        print(f"Обои успешно установлены: {os.path.basename(image_path)}")
        return
    except (FileNotFoundError, subprocess.CalledProcessError): pass
    qdbus_commands = ['qdbus-qt6', 'qdbus-qt5', 'qdbus']
    found_command = next((cmd for cmd in qdbus_commands if shutil.which(cmd)), None)
    if not found_command: return
    script = f"""var allDesktops = desktops();for (i=0; i < allDesktops.length; i++) {{ d = allDesktops[i]; d.wallpaperPlugin = "org.kde.image"; d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General"); d.writeConfig("Image", "file://{image_path}"); }}"""
    try:
        subprocess.run([found_command, 'org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.evaluateScript', script], check=True, capture_output=True, env=os.environ.copy())
        print(f"Обои успешно установлены через qdbus: {os.path.basename(image_path)}")
    except subprocess.CalledProcessError: pass

def get_image_index(location):
    s = sun(location.observer, date=datetime.now(), tzinfo=location.timezone)
    now_utc = datetime.now(timezone.utc)
    dawn, sunrise, sunset, dusk = s['dawn'], s['sunrise'], s['sunset'], s['dusk']
    if sunrise <= now_utc < sunset:
        day_duration = sunset - sunrise
        golden_hour_duration = day_duration / 8
        if now_utc < sunrise + golden_hour_duration: return 3
        if now_utc >= sunset - golden_hour_duration: return 12
        midday_start, midday_duration = sunrise + golden_hour_duration, day_duration - (2 * golden_hour_duration)
        if midday_duration.total_seconds() <= 0: return 7
        progress = (now_utc - midday_start) / midday_duration
        return min(4 + int(progress * 8), 11)
    if sunset <= now_utc < dusk: return 13 if now_utc < sunset + (dusk - sunset) / 2 else 14
    if dawn <= now_utc < sunrise: return 1 if now_utc < dawn + (sunrise - dawn) / 2 else 2
    yesterday_s = sun(location.observer, date=datetime.now() - timedelta(days=1), tzinfo=location.timezone)
    middle_of_night = yesterday_s['dusk'] + (dawn - yesterday_s['dusk']) / 2
    if now_utc > dusk: middle_of_night = dusk + ((dawn + timedelta(days=1)) - dusk) / 2
    return 15 if now_utc < middle_of_night else 16

def main():
    location = get_location()
    if not os.path.isdir(IMAGE_PATH):
        print(f"Ошибка: Папка с изображениями не найдена: {IMAGE_PATH}")
        return
    index = get_image_index(location)
    if index is None: return
    image_file = f"{IMAGE_PREFIX}{index}{IMAGE_EXTENSION}"
    full_path = os.path.join(IMAGE_PATH, image_file)
    if not os.path.exists(full_path): return
    set_kde_wallpaper(full_path)

if __name__ == "__main__":
    main()
