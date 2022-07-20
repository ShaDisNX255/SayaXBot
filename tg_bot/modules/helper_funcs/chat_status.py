from functools import wraps

from tg_bot import (
    DEL_CMDS,
    DEV_USERS,
    SUDO_USERS,
    SUPPORT_USERS,
    WHITELIST_USERS,
    dispatcher,
    MOD_USERS
)

from telegram import Update, TelegramError
from telegram.ext import CallbackContext


def is_whitelist_plus(user_id: int) -> bool:
    return any(
        user_id in user
        for user in [
            WHITELIST_USERS,
            SUPPORT_USERS,
            SUDO_USERS,
            DEV_USERS,
            MOD_USERS
        ]
    )


def is_support_plus(user_id: int) -> bool:
    return user_id in SUPPORT_USERS or user_id in SUDO_USERS or user_id in DEV_USERS


def is_sudo_plus(user_id: int) -> bool:
    return user_id in SUDO_USERS or user_id in DEV_USERS


def dev_plus(func):
    @wraps(func)
    def is_dev_plus_func(update: Update, context: CallbackContext, *args, **kwargs):
        # bot = context.bot
        user = update.effective_user

        if user.id in DEV_USERS:
            return func(update, context, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                update.effective_message.delete()
            except TelegramError:
                pass
        else:
            update.effective_message.reply_text(
                "This is a developer restricted command."
                " You do not have permissions to run this."
            )

    return is_dev_plus_func


def sudo_plus(func):
    @wraps(func)
    def is_sudo_plus_func(update: Update, context: CallbackContext, *args, **kwargs):
        # bot = context.bot
        user = update.effective_user

        if user and is_sudo_plus(user.id):
            return func(update, context, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                update.effective_message.delete()
            except TelegramError:
                pass
        else:
            update.effective_message.reply_text(
                "This command is restricted to users with special access, you can't use it."
            )

    return is_sudo_plus_func


def support_plus(func):
    @wraps(func)
    def is_support_plus_func(update: Update, context: CallbackContext, *args, **kwargs):
        # bot = context.bot
        user = update.effective_user

        if user and is_support_plus(user.id):
            return func(update, context, *args, **kwargs)
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                update.effective_message.delete()
            except TelegramError:
                pass

    return is_support_plus_func


def whitelist_plus(func):
    @wraps(func)
    def is_whitelist_plus_func(
            update: Update, context: CallbackContext, *args, **kwargs
    ):
        user = update.effective_user

        if user and is_whitelist_plus(user.id):
            return func(update, context, *args, **kwargs)
        else:
            update.effective_message.reply_text(
                "You don't have access to use this.\nVisit @SayaBotSupport"
            )

    return is_whitelist_plus_func


def connection_status(func):
    @wraps(func)
    def connected_status(update: Update, context: CallbackContext, *args, **kwargs):
        if update.effective_chat is None or update.effective_user is None:
            return
        if conn := connected(
                context.bot,
                update,
                update.effective_chat,
                update.effective_user.id,
                need_admin=False,
        ):
            chat = dispatcher.bot.getChat(conn)
            update.__setattr__("_effective_chat", chat)
            return func(update, context, *args, **kwargs)
        elif update.effective_message.chat.type == "private":
            update.effective_message.reply_text(
                    "Send /connect in a group that you and I have in common first."
            )
            return connected_status
        return func(update, context, *args, **kwargs)

    return connected_status

# Workaround for circular import with connection.py
from tg_bot.modules import connection

connected = connection.connected
