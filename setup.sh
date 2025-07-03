#!/bin/bash
set -e # Прерывать выполнение при любой ошибке

echo "--- Установка зависимостей ---"
sudo apt update
sudo apt install -y python3-pip git
pip install requests astral timezonefinder --break-system-packages

echo "--- Копирование файлов скрипта ---"
# Создаем директории, если их нет
mkdir -p ~/.local/bin
mkdir -p ~/.config/systemd/user

# Копируем основной скрипт и делаем его исполняемым
cp mojave_kde.py ~/.local/bin/mojave_kde.py
chmod +x ~/.local/bin/mojave_kde.py

echo "--- Настройка сервиса автозапуска (systemd) ---"
# Копируем файлы сервиса
cp systemd/mojave-wallpaper.service ~/.config/systemd/user/
cp systemd/mojave-wallpaper.timer ~/.config/systemd/user/

# Заменяем плейсхолдер на реальный путь к скрипту
# Это делает скрипт универсальным для любого пользователя
USER_SCRIPT_PATH=$(realpath ~/.local/bin/mojave_kde.py)
sed -i "s|__SCRIPT_PATH__|${USER_SCRIPT_PATH}|g" ~/.config/systemd/user/mojave-wallpaper.service

echo "--- Включение и запуск таймера ---"
systemctl --user daemon-reload
systemctl --user enable --now mojave-wallpaper.timer

echo ""
echo "✅ Установка успешно завершена!"
echo ""
echo "➡️  Следующий шаг: запустите скрипт вручную для первоначальной настройки:"
echo "   ~/.local/bin/mojave_kde.py"
echo ""
