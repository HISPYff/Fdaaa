# EBIKE PARTS — Telegram каталог v2

Красивый каталог комплектующих для электровелосипедов:
- главное меню;
- категории;
- карточки товаров;
- фотографии;
- поиск по названию, описанию и категории;
- кнопки «Предыдущий / Следующий» внутри категории;
- связь с продавцом;
- админка для управления каталогом.

## Запуск

Python 3.10+.

```bash
pip install -r requirements.txt
```

Переменные окружения:
```text
BOT_TOKEN=токен_бота
ADMIN_ID=ваш_Telegram_ID
SELLER_USERNAME=username_продавца_без_@
```

Linux/macOS:
```bash
export BOT_TOKEN="..."
export ADMIN_ID="123456789"
export SELLER_USERNAME="seller"
python bot.py
```

Windows PowerShell:
```powershell
$env:BOT_TOKEN="..."
$env:ADMIN_ID="123456789"
$env:SELLER_USERNAME="seller"
python bot.py
```

## Админ-команды

`/admin` — список команд  
`/addcat` — добавить раздел  
`/addproduct` — добавить товар с фото  
`/cats` — список разделов  
`/products` — список товаров  
`/delcat ID` — удалить раздел  
`/delproduct ID` — удалить товар

## Настройка

Токен получают через официального Telegram-бота @BotFather.
Не публикуйте токен.
