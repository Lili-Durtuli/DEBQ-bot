import json
import os
from typing import Dict, List

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# ====== НАСТРОЙКИ ТЕСТА (DEBQ) ======
# Шкалы (индексы вопросов начинаются с 1)
RESTRAINED_RANGE = range(1, 11)     # 1–10
EMOTIONAL_RANGE  = range(11, 24)    # 11–23
EXTERNAL_RANGE   = range(24, 34)    # 24–33

# Вопросы с обратным кодированием (для DEBQ — только 31)
REVERSE_SCORED = {31}

# Нормы из методики (средние значения шкал)
NORMS = {
    "restrained": 2.4,   # Ограничительное/диетическое
    "emotional":  1.8,   # Эмоциональное
    "external":   2.7,   # Экстернальное
}

# Подписи для шкал
SCALE_LABELS_RU = {
    "restrained": "Ограничительное (диетическое) пищевое поведение",
    "emotional":  "Эмоциональное пищевое поведение",
    "external":   "Экстернальное пищевое поведение",
}

# Подсказки-интерпретации (кратко; развернутое описание — в итоговом сообщении)
def interpret(scale_key: str, mean_score: float) -> str:
    norm = NORMS[scale_key]
    # «Вокруг нормы» считаем ±0.2 — при желании можно сузить/расширить
    if mean_score < norm - 0.2:
        if scale_key == "restrained":
            return "ниже нормы — тенденция к бесконтрольному приёму пищи"
        if scale_key == "emotional":
            return "ниже нормы — выраженного заедания эмоций не отмечается"
        if scale_key == "external":
            return "ниже нормы — обычно не переедаете из-за внешних стимулов"
    elif mean_score > norm + 0.2:
        if scale_key == "restrained":
            return "выше нормы — «осторожный/профессиональный» едок, напряжённые отношения с едой"
        if scale_key == "emotional":
            return "выше нормы — склонность «заедать» эмоции"
        if scale_key == "external":
            return "выше нормы — склонность переедать из-за доступности/вида еды"
    else:
        # около нормы
        if scale_key == "restrained":
            return "в пределах нормы — гибкие и разумные ограничения"
        if scale_key == "emotional":
            return "в пределах нормы — не склонны заедать эмоции"
        if scale_key == "external":
            return "в пределах нормы — внешние стимулы мало влияют на объём пищи"
    return ""


# ====== ЗАГРУЗКА ВОПРОСОВ ======
def load_questions(path: str = "questions.json") -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Ожидаемый формат: [{"id": 1, "text": "..."}, ..., {"id": 33, "text": "..."}]
    # где id идут от 1 до 33 без пропусков.
    ids = [q["id"] for q in data]
    if sorted(ids) != list(range(1, 34)):
        raise ValueError("В файле questions.json должны быть вопросы с id 1..33 без пропусков.")
    return data


QUESTIONS = load_questions()

# ====== УТИЛИТЫ ======
LIKERT_OPTIONS = [
    ("Никогда", 1),
    ("Редко", 2),
    ("Иногда", 3),
    ("Часто", 4),
    ("Очень часто", 5),
]

def reverse_score(score: int) -> int:
    # 1<->5, 2<->4, 3->3
    return {1:5, 2:4, 3:3, 4:2, 5:1}[score]

def compute_results(answers: Dict[int, int]) -> Dict[str, float]:
    """Возвращает средние значения по 3 шкалам."""
    # Применяем обратное кодирование для нужных вопросов
    scored = {}
    for qid, val in answers.items():
        scored[qid] = reverse_score(val) if qid in REVERSE_SCORED else val

    def mean_for(rng: range) -> float:
        vals = [scored[i] for i in rng]
        return round(sum(vals) / len(vals), 2)

    return {
        "restrained": mean_for(RESTRAINED_RANGE),
        "emotional":  mean_for(EMOTIONAL_RANGE),
        "external":   mean_for(EXTERNAL_RANGE),
    }

def results_text(results: Dict[str, float]) -> str:
    r, e, ex = results["restrained"], results["emotional"], results["external"]
    lines = []
    lines.append("🧮 *Ваши результаты (средние баллы по шкалам)*")
    lines.append(f"• {SCALE_LABELS_RU['restrained']}: *{r}* (норма {NORMS['restrained']}) — {interpret('restrained', r)}")
    lines.append(f"• {SCALE_LABELS_RU['emotional']}: *{e}* (норма {NORMS['emotional']}) — {interpret('emotional', e)}")
    lines.append(f"• {SCALE_LABELS_RU['external']}: *{ex}* (норма {NORMS['external']}) — {interpret('external', ex)}")
    # Развёрнутые подсказки из методички (сжато, без медицины)
    lines.append(
        "\nℹ️ Пояснения:\n"
        "— По ограничительной шкале около нормы — проблем с гибкими ограничениями нет; выше нормы — напряжённые отношения с едой; "
        "ниже нормы — склонность к бесконтрольному приёму пищи. "
        "— Эмоциональная шкала: выше нормы — трудность справляться с эмоциями без еды; норма — обычно не «заедаете»; "
        "— Экстернальная шкала: выше нормы — переедание из-за вида/доступности еды; ниже — внешние стимулы мало влияют."
    )
    lines.append(
        "\n⚠️ Это скрининг, а не диагноз. При выраженных беспокойствах стоит обратиться к врачу/психологу, "
        "особенно если есть подозрения на РПП."
    )
    return "\n".join(lines)

def make_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"ans:{value}")]
        for (label, value) in LIKERT_OPTIONS
    ]
    return InlineKeyboardMarkup(buttons)

# ====== ОБРАБОТЧИКИ БОТА ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Это DEBQ-тест (33 вопроса) про пищевое поведение. "
        "Ответы: Никогда–Очень часто. Нажмите /test чтобы начать.\n\n"
        "Важно: это не медицинский диагноз."
    )

async def cmd_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"] = {}
    context.user_data["current_q"] = 1
    await send_question(update, context, 1)

async def send_question(update_or_query, context: ContextTypes.DEFAULT_TYPE, qid: int):
    q = next(q for q in QUESTIONS if q["id"] == qid)
    text = f"Вопрос {qid}/33\n\n{q['text']}\n\nВыберите вариант:"
    keyboard = make_keyboard()

    if hasattr(update_or_query, "callback_query") and update_or_query.callback_query:
        await update_or_query.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update_or_query.message.reply_text(text=text, reply_markup=keyboard)

async def on_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data.startswith("ans:"):
        return
    score = int(data.split(":")[1])

    qid = context.user_data.get("current_q", 1)
    answers: Dict[int, int] = context.user_data.get("answers", {})
    answers[qid] = score
    context.user_data["answers"] = answers

    next_q = qid + 1
    if next_q <= 33:
        context.user_data["current_q"] = next_q
        await send_question(update, context, next_q)
    else:
        # Все ответы получены
        res = compute_results(answers)
        text = results_text(res)
        await query.edit_message_text(text=text, parse_mode="Markdown")
        # Сброс состояния (при желании можно оставить ответы)
        context.user_data.pop("current_q", None)

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Установите переменную окружения BOT_TOKEN с токеном Telegram бота.")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", cmd_test))
    app.add_handler(CallbackQueryHandler(on_answer))

    app.run_polling()

if __name__ == "__main__":
    main()
