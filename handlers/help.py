"""Interactive /help system: rules, commands, scoring, examples, tips, FAQ."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from keyboards.help_kb import help_home_kb, help_section_kb

router = Router(name="help")

HELP_HOME_TEXT = "📖 <b>Help Center</b>\n\nChoose a topic to learn more:"

SECTIONS: dict[str, str] = {
    "rules": (
        "📜 <b>Game Rules</b>\n\n"
        "1. You'll see a question and a hidden board of top answers.\n"
        "2. Type your guess as a normal message — no command needed.\n"
        "3. Correct guesses reveal their spot and add points to the score.\n"
        "4. Wrong guesses cost you a strike.\n"
        "5. Three strikes and the round ends.\n"
        "6. Clear the whole board to win the round!"
    ),
    "commands": (
        "⌨ <b>Commands</b>\n\n"
        "/play — start a new game\n"
        "/profile — view your profile\n"
        "/stats — quick stats summary\n"
        "/top — leaderboard\n"
        "/rank — your global rank\n"
        "/join — join a group match\n"
        "/leave — leave a group match\n"
        "/hint — reveal a weak answer (costs points)\n"
        "/skip — skip the current question\n"
        "/stop — end the current round\n"
        "/settings — notification &amp; preferences\n"
        "/about — about this bot\n"
        "/report — report a bug or bad question\n"
        "/admin — admin panel (admins only)"
    ),
    "scoring": (
        "🧮 <b>Scoring</b>\n\n"
        "• Each answer's point value is shown once revealed.\n"
        "• +10 XP for every correct answer.\n"
        "• +50 XP bonus for winning the round.\n"
        "• +100 XP bonus for completing the Daily Challenge.\n"
        "• Using a hint reveals an answer at a reduced point value."
    ),
    "examples": (
        "💡 <b>Examples</b>\n\n"
        "Question: <i>Name a famous Shonen anime</i>\n"
        "You type: <code>one piece</code> → matches \"One Piece\" ✅\n"
        "You type: <code>OP</code> → also matches via alias ✅\n"
        "You type: <code>one pece</code> → still matches via fuzzy matching ✅"
    ),
    "tips": (
        "💡 <b>Tips</b>\n\n"
        "• Don't overthink spelling — the matcher is forgiving.\n"
        "• Common abbreviations (AOT, MHA, JJK...) are recognized.\n"
        "• Use /hint if you're stuck, but it costs some points.\n"
        "• In group matches, anyone in the chat can guess — fastest correct answer wins the spot."
    ),
    "faq": (
        "❓ <b>FAQ</b>\n\n"
        "<b>Q: My correct answer wasn't accepted?</b>\n"
        "A: Try /report so we can add it as an alias.\n\n"
        "<b>Q: Can I play in a group?</b>\n"
        "A: Yes — use /play in any group chat.\n\n"
        "<b>Q: How do I increase my level?</b>\n"
        "A: Earn XP by answering correctly and winning rounds."
    ),
}


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_HOME_TEXT, reply_markup=help_home_kb())


@router.callback_query(F.data == "menu:help")
async def cb_help_home(callback: CallbackQuery) -> None:
    await callback.message.edit_text(HELP_HOME_TEXT, reply_markup=help_home_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("help:"))
async def cb_help_section(callback: CallbackQuery) -> None:
    key = callback.data.split(":", 1)[1]
    text = SECTIONS.get(key, "Section not found.")
    await callback.message.edit_text(text, reply_markup=help_section_kb())
    await callback.answer()
