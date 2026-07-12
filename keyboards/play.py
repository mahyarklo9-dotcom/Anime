"""Gameplay handlers: starting rounds (single/group) and playing them out."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from game import GuessOutcome, game_engine
from keyboards.game_kb import in_game_kb, play_mode_kb, round_over_kb
from models.app import GameMode, User
from utils.formatting import render_board

logger = logging.getLogger(__name__)
router = Router(name="play")


def _mode_for_chat(message: Message) -> GameMode:
    return GameMode.GROUP if message.chat.type in ("group", "supergroup") else GameMode.SINGLE


async def _start_round(message: Message, db_user: User, mode: GameMode) -> None:
    if game_engine.has_active_round(message.chat.id):
        await message.answer(
            "A round is already in progress here. Use /stop to end it first, "
            "or just jump in and start guessing!"
        )
        return

    await game_engine.refresh_alias_cache()
    try:
        state = await game_engine.start_round(
            chat_id=message.chat.id, host_id=db_user.id, mode=mode
        )
    except RuntimeError as exc:
        await message.answer(f"⚠️ {exc}")
        return

    await message.answer(render_board(state), reply_markup=in_game_kb())


@router.message(Command("play"))
async def cmd_play(message: Message, db_user: User) -> None:
    if message.chat.type in ("group", "supergroup"):
        await _start_round(message, db_user, GameMode.GROUP)
    else:
        await message.answer(
            "Choose a game mode:", reply_markup=play_mode_kb()
        )


@router.callback_query(F.data == "menu:play")
async def cb_menu_play(callback: CallbackQuery, db_user: User) -> None:
    if callback.message.chat.type in ("group", "supergroup"):
        await callback.answer()
        await _start_round(callback.message, db_user, GameMode.GROUP)
        return
    await callback.message.edit_text("Choose a game mode:", reply_markup=play_mode_kb())
    await callback.answer()


@router.callback_query(F.data == "play:single")
async def cb_play_single(callback: CallbackQuery, db_user: User) -> None:
    await callback.answer()
    await _start_round(callback.message, db_user, GameMode.SINGLE)


@router.callback_query(F.data == "play:group")
async def cb_play_group(callback: CallbackQuery, db_user: User) -> None:
    await callback.answer()
    await _start_round(callback.message, db_user, GameMode.GROUP)


@router.message(Command("join"))
async def cmd_join(message: Message) -> None:
    await message.answer(
        "✅ You're in! Everyone in this chat can guess once a round starts — "
        "just type your answer as a normal message."
    )


@router.message(Command("leave"))
async def cmd_leave(message: Message) -> None:
    await message.answer("👋 Noted — you'll be skipped, but feel free to jump back in anytime.")


@router.message(Command("stop"))
async def cmd_stop(message: Message) -> None:
    await _stop_round(message.chat.id, message)


@router.callback_query(F.data == "game:stop")
async def cb_stop(callback: CallbackQuery) -> None:
    await callback.answer()
    await _stop_round(callback.message.chat.id, callback.message)


async def _stop_round(chat_id: int, message: Message) -> None:
    if not game_engine.has_active_round(chat_id):
        await message.answer("There's no active round here.")
        return
    await game_engine.skip_round(chat_id)
    await message.answer("🛑 Round stopped. Use /play to start a new one.", reply_markup=round_over_kb())


@router.message(Command("skip"))
async def cmd_skip(message: Message, db_user: User) -> None:
    await _skip_round(message, db_user)


@router.callback_query(F.data == "game:skip")
async def cb_skip(callback: CallbackQuery, db_user: User) -> None:
    await callback.answer()
    await _skip_round(callback.message, db_user, edit=True)


async def _skip_round(message: Message, db_user: User, edit: bool = False) -> None:
    chat_id = message.chat.id
    if not game_engine.has_active_round(chat_id):
        await message.answer("There's no active round to skip.")
        return
    await game_engine.skip_round(chat_id)
    await message.answer("⏭ Question skipped. Starting a new one...")
    await _start_round(message, db_user, _mode_for_chat(message))


@router.message(Command("hint"))
async def cmd_hint(message: Message) -> None:
    await _use_hint(message)


@router.callback_query(F.data == "game:hint")
async def cb_hint(callback: CallbackQuery) -> None:
    await callback.answer()
    await _use_hint(callback.message)


async def _use_hint(message: Message) -> None:
    chat_id = message.chat.id
    if not game_engine.has_active_round(chat_id):
        await message.answer("There's no active round right now.")
        return
    revealed = await game_engine.use_hint(chat_id)
    if revealed is None:
        await message.answer("No hints available — the board is already clear!")
        return
    state = game_engine.get_round(chat_id)
    await message.answer(
        f"💡 Hint: <b>{revealed.text.title()}</b> was revealed (reduced points).",
    )
    if state:
        await message.answer(render_board(state), reply_markup=in_game_kb())


@router.message(F.text, ~F.text.startswith("/"))
async def handle_guess(message: Message, db_user: User) -> None:
    """Any plain-text message is treated as a guess if a round is active."""
    chat_id = message.chat.id
    if not game_engine.has_active_round(chat_id):
        return  # Not a guess context; ignore silently.

    result = await game_engine.submit_guess(chat_id, db_user.id, message.text)
    state = game_engine.get_round(chat_id)

    if result.outcome == GuessOutcome.BANNED:
        return

    if result.outcome == GuessOutcome.ALREADY_REVEALED:
        await message.reply("That answer's already on the board! Try another.")
        return

    if result.outcome == GuessOutcome.CORRECT:
        assert result.match is not None
        await message.reply(
            f"✅ <b>{result.match.answer_text.title()}</b> — +{result.match.points} pts!"
        )
        if result.round_finished:
            await message.answer(
                f"🎉 <b>Board cleared! You won the round!</b>\n\n{render_board(state)}",
                reply_markup=round_over_kb(),
            )
        elif state:
            await message.answer(render_board(state), reply_markup=in_game_kb())
        return

    if result.outcome == GuessOutcome.WRONG:
        if result.round_finished:
            await message.reply("❌ Wrong! That's strike three — round over.")
            await message.answer(
                f"💀 <b>Out of strikes!</b> Here's what was on the board:\n\n{render_board(state)}",
                reply_markup=round_over_kb(),
            )
        else:
            await message.reply(f"❌ Wrong! Strike {result.strikes}/{result.max_strikes}.")
        return
