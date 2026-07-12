"""Basic admin panel: /admin.

Scope for v1: view statistics, broadcast a message to all known users,
and ban/unban users by Telegram ID. All admin-only handlers are guarded
by :class:`filters.is_admin.IsAdmin`, which checks the sender against
``ADMIN_IDS`` from the environment -- never trust callback data alone for
authorization.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from database import AppSession
from filters.is_admin import IsAdmin
from keyboards.admin_kb import admin_cancel_kb, admin_menu_kb
from models.app import User
from services.question_service import question_service

logger = logging.getLogger(__name__)
router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class AdminForm(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_ban_target = State()
    waiting_for_unban_target = State()


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    await message.answer("🛠 <b>Admin Panel</b>", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("🛠 <b>Admin Panel</b>", reply_markup=admin_menu_kb())
    await callback.answer("Cancelled.")


@router.callback_query(F.data == "admin:stats")
async def cb_stats(callback: CallbackQuery) -> None:
    async with AppSession() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar_one()
        banned_users = (
            await session.execute(select(func.count(User.id)).where(User.is_banned == True))  # noqa: E712
        ).scalar_one()
        total_xp = (await session.execute(select(func.coalesce(func.sum(User.xp), 0)))).scalar_one()

    total_questions = await question_service.count_questions()

    text = (
        "📊 <b>Bot Statistics</b>\n\n"
        f"👥 Total users: <b>{total_users}</b>\n"
        f"🚫 Banned users: <b>{banned_users}</b>\n"
        f"⭐ Total XP earned: <b>{total_xp}</b>\n"
        f"❓ Questions in database: <b>{total_questions}</b>"
    )
    await callback.message.edit_text(text, reply_markup=admin_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:broadcast")
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminForm.waiting_for_broadcast)
    await callback.message.edit_text(
        "📣 Send the message you want to broadcast to all users.",
        reply_markup=admin_cancel_kb(),
    )
    await callback.answer()


@router.message(AdminForm.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with AppSession() as session:
        result = await session.execute(select(User.id).where(User.is_banned == False))  # noqa: E712
        user_ids = [row[0] for row in result.all()]

    sent, failed = 0, 0
    for user_id in user_ids:
        try:
            await message.bot.send_message(user_id, message.text or "")
            sent += 1
        except Exception:  # noqa: BLE001 - broadcasting must never crash the loop
            failed += 1
        await asyncio.sleep(0.05)  # gentle rate limiting

    await message.answer(f"📣 Broadcast complete. Sent: {sent}, Failed: {failed}.")


@router.callback_query(F.data == "admin:ban")
async def cb_ban_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminForm.waiting_for_ban_target)
    await callback.message.edit_text(
        "🚫 Send the Telegram user ID to ban (optionally followed by a reason), "
        "e.g. <code>123456789 spamming answers</code>",
        reply_markup=admin_cancel_kb(),
    )
    await callback.answer()


@router.message(AdminForm.waiting_for_ban_target)
async def process_ban(message: Message, state: FSMContext) -> None:
    await state.clear()
    parts = (message.text or "").strip().split(maxsplit=1)
    if not parts or not parts[0].isdigit():
        await message.answer("⚠️ Invalid format. Please provide a numeric Telegram user ID.")
        return

    target_id = int(parts[0])
    reason = parts[1] if len(parts) > 1 else None

    async with AppSession() as session:
        user = await session.get(User, target_id)
        if user is None:
            await message.answer("⚠️ That user hasn't interacted with the bot yet.")
            return
        user.is_banned = True
        user.ban_reason = reason
        await session.commit()

    await message.answer(f"🚫 User {target_id} has been banned.")


@router.callback_query(F.data == "admin:unban")
async def cb_unban_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminForm.waiting_for_unban_target)
    await callback.message.edit_text(
        "✅ Send the Telegram user ID to unban.",
        reply_markup=admin_cancel_kb(),
    )
    await callback.answer()


@router.message(AdminForm.waiting_for_unban_target)
async def process_unban(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("⚠️ Invalid format. Please provide a numeric Telegram user ID.")
        return

    target_id = int(text)
    async with AppSession() as session:
        user = await session.get(User, target_id)
        if user is None:
            await message.answer("⚠️ That user hasn't interacted with the bot yet.")
            return
        user.is_banned = False
        user.ban_reason = None
        await session.commit()

    await message.answer(f"✅ User {target_id} has been unbanned.")
