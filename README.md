@'
# DEBQ-bot

Telegram-бот для опросника **DEBQ** (Nederlands Vragenlijst voor Eetgedrag).
- Шкалы: Ограничительное (1–10), Эмоциональное (11–23), Экстернальное (24–33, п.31 обратный).
- Ответы: 1=Никогда … 5=Очень часто. Подсчёт: среднее по каждой подшкале.

## Локальный запуск
```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:BOT_TOKEN="ВАШ_ТОКЕН_ОТ_BOTFATHER"
python DEBQ_bot.py
