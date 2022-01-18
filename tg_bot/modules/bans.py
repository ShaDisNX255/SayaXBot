import html
from typing import Optional

from telegram import Update, ParseMode
from telegram.error import BadRequest
from telegram.ext import Filters, CallbackContext
from telegram.utils.helpers import mention_html

from tg_bot import (
    BAN_STICKER,
    DEV_USERS,
    MESSAGE_DUMP,
    MOD_USERS,
    SUDO_USERS,
    SUPPORT_USERS,
    OWNER_ID,
    WHITELIST_USERS,
    spamcheck,
    dispatcher,
)

from tg_bot.modules.helper_funcs.chat_status import (
    bot_admin,
    can_restrict,
    connection_status,
    is_user_admin,
    can_delete,
    is_user_ban_protected,
    is_user_in_chat,
    u_can_delete,
)
from tg_bot.modules.helper_funcs.extraction import extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable, gloggable
from tg_bot.modules.helper_funcs.decorators import kigcmd

def cannot_ban(user_id, message):

    if user_id == OWNER_ID:
        message.reply_text("I'd never ban my owner.")
    elif user_id in DEV_USERS:
        message.reply_text("I can't act against our own.")
    elif user_id in SUDO_USERS:
        message.reply_text("My sudos are ban immune")
    elif user_id in SUPPORT_USERS:
        message.reply_text("My support users are ban immune")
    elif user_id in WHITELIST_USERS:
        message.reply_text("Bring an order from My Devs to fight a Whitelist user.")
    elif user_id in MOD_USERS:
        message.reply_text("Moderators cannot be banned, report abuse at @SayaBotSupport.")
    else:
        message.reply_text("This user has immunity and cannot be banned.")

ban_myself = "Oh yeah, ban myself, noob!"

from ..modules.helper_funcs.anonymous import user_admin as u_admin, AdminPerms, resolve_user as res_user, UserClass

@kigcmd(command=('dban'), pass_args=True)
@kigcmd(command=('dsban'), pass_args=True)
@kigcmd(command=('sban'), pass_args=True)
@kigcmd(command=('ban'), pass_args=True)
@spamcheck
@connection_status
@bot_admin
@can_restrict
@u_admin(UserClass.MOD, AdminPerms.CAN_RESTRICT_MEMBERS)
@loggable
def ban(update: Update, context: CallbackContext):  # sourcery no-metrics
    chat = update.effective_chat  # type: Optional[Chat]
    u = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = context.args
    user = res_user(u, message.message_id, chat)
    # user = u
    log_message = ""
    reason = ""
    bot = context.bot
    log_message = ""
    reason = ""
    if message.reply_to_message and message.reply_to_message.sender_chat:

        if message.text.startswith(('/s','!s','>s')):
            silent = True
            if not can_delete(chat, context.bot.id):
                message.reply_text("I don't have permission to delete messages here!")
                return ""
        else:
            silent = False
        if message.text.startswith(('/d','!d','>d')):
            delban = True
            if not can_delete(chat, context.bot.id):
                message.reply_text("I dont't have permission to delete messages here!")
                return ""
            if not u_can_delete(chat, user.id):
                message.reply_text("You dont't have permission to delete messages here!")
                return ""
        else:
            delban = False
        if message.text.startswith(('/ds','!ds','>ds')):
            delsilent = True
            if not can_delete(chat, context.bot.id):
                message.reply_text("I dont't have permission to delete messages here!")
                return ""
            if not u_can_delete(chat, user.id):
                message.reply_text("You dont't have permission to delete messages here!")
                return ""

        r = bot.ban_chat_sender_chat(chat_id=chat.id, sender_chat_id=message.reply_to_message.sender_chat.id)

        logmsg  = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#BANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Channel:</b> {message.reply_to_message.sender_chat.title}"
        f"<b>Channel ID:</b> {message.reply_to_message.sender_chat.id}"
        )
        if silent:
            if delsilent and message.reply_to_message:
                message.reply_to_message.delete() 
            message.delete()
            return logmsg
        if delban:
            if message.reply_to_message:
                message.reply_to_message.delete()
        context.bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        if r:
            message.reply_text("Channel {} was banned successfully from {}".format(
                html.escape(message.reply_to_message.sender_chat.title),
                html.escape(chat.title)
            ),
                parse_mode="html"
            )
            return logmsg
        else:
            message.reply_text("Failed to ban channel")
        return ""

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("I doubt that's a user.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "User not found":
            raise
        message.reply_text("Can't seem to find this person.")
        return log_message

    if user_id == context.bot.id:
        message.reply_text(ban_myself)
        return log_message

    if is_user_ban_protected(update, user_id, member) and user.id not in DEV_USERS:
        cannot_ban(user_id, message)
        return log_message

    if message.text.startswith(('/s','!s','>s')):
        silent = True
        if not can_delete(chat, context.bot.id):
            message.reply_text("I dont't have permission to delete messages here!")
            return ""
    else:
        silent = False
    if message.text.startswith(('/d','!d','>d')):
        delban = True
        if not can_delete(chat, context.bot.id):
            message.reply_text("I dont't have permission to delete messages here!")
            return ""
        if not u_can_delete(chat, user.id):
            message.reply_text("You dont't have permission to delete messages here!")
            return ""
    else:
        delban = False
    if message.text.startswith(('/ds','!ds','>ds')):
        delsilent = True
        if not can_delete(chat, context.bot.id):
            message.reply_text("I dont't have permission to delete messages here!")
            return ""
        if not u_can_delete(chat, user.id):
            message.reply_text("You dont't have permission to delete messages here!")
            return ""
    else:
        delsilent = False
    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#BANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
    )
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    try:
        chat.ban_member(user_id)

        if silent:
            if delsilent and message.reply_to_message:
                message.reply_to_message.delete()
            message.delete()
            return log
        if delban:
            if message.reply_to_message:
                message.reply_to_message.delete()
        context.bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        if reason:
            context.bot.sendMessage(
                chat.id,
                "{} was banned by {} in <b>{}</b>\n<b>Reason</b>: <code>{}</code>".format(
                    mention_html(member.user.id, member.user.first_name), mention_html(user.id, user.first_name), message.chat.title, reason
                ),
                parse_mode=ParseMode.HTML,
            )
        else:
            context.bot.sendMessage(
                chat.id,
                "{} was banned by {} in <b>{}</b>".format(
                    mention_html(member.user.id, member.user.first_name), mention_html(user.id, user.first_name), message.chat.title
                ),
                parse_mode=ParseMode.HTML,
            )
        return log

    except BadRequest as excp:
        if excp.message == 'Reply message not found':
            message.reply_text('Banhammered!', quote=False)
            return log
        else:
            bot = dispatcher.bot
            bot.sendMessage(MESSAGE_DUMP, str(update))
            bot.sendMessage(
                MESSAGE_DUMP,
                'ERROR banning user {} in chat {} ({}) due to {}'.format(
                    user_id, chat.title, chat.id, excp.message
                ),
            )

            message.reply_text("Well damn, I can't ban that user.")
    return ""


@kigcmd(command='tban', pass_args=True)
@connection_status
@spamcheck
@bot_admin
@can_restrict
@u_admin(UserClass.MOD, AdminPerms.CAN_RESTRICT_MEMBERS)
@loggable
def temp_ban(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    u = update.effective_user
    message = update.effective_message
    log_message = ""
    reason = ""
    bot, args = context.bot, context.args
    user = res_user(u, message.message_id, chat)

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("I doubt that's a user.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != 'User not found':
            raise
        message.reply_text("I can't seem to find this user.")
        return log_message
    if user_id == bot.id:
        message.reply_text(ban_myself)
        return log_message

    if is_user_ban_protected(update, user_id, member) and user not in DEV_USERS:
        cannot_ban(user_id, message)
        return log_message

    if not reason:
        message.reply_text("You haven't specified a time to ban this user for!")
        return log_message

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    reason = split_reason[1] if len(split_reason) > 1 else ""
    bantime = extract_time(message, time_val)

    if not bantime:
        return log_message

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        "#TEMP_BANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}\n"
        f"<b>Time:</b> {time_val}"
    )
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    try:
        chat.ban_member(user_id, until_date=bantime)
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker

        if reason:
            bot.sendMessage(
                chat.id,
                f"Banned! User {mention_html(member.user.id, member.user.first_name)} will be banned for {time_val}.\nReason: {reason}",
                parse_mode=ParseMode.HTML,
            )

        else:
            bot.sendMessage(
                chat.id,
                f"Banned! User {mention_html(member.user.id, member.user.first_name)} will be banned for {time_val}.",
                parse_mode=ParseMode.HTML,
            )

        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text(
                f"Banned! User will be banned for {time_val}.", quote=False
            )
            return log
        else:
            bot.sendMessage(MESSAGE_DUMP, str(update))
            bot.sendMessage(MESSAGE_DUMP, 
                "ERROR banning user {} in chat {} ({}) due to {}".format(
                user_id,
                chat.title,
                chat.id,
                excp.message)
            )
            message.reply_text("Well damn, I can't ban that user.")

    return log_message


@kigcmd(command=['kick', 'punch'], pass_args=True)
@spamcheck
@connection_status
@bot_admin
@can_restrict
@u_admin(UserClass.MOD, AdminPerms.CAN_RESTRICT_MEMBERS)
@loggable
def kick(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    u = update.effective_user
    message = update.effective_message
    log_message = ""
    bot, args = context.bot, context.args
    user = res_user(u, message.message_id, chat)
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("I doubt that's a user.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != 'User not found':
            raise
        message.reply_text("I can't seem to find this user.")
        return log_message
    if user_id == bot.id:
        message.reply_text("Yeahhh I'm not gonna do that.")
        return log_message

    if is_user_ban_protected(update, user_id, member) and user not in DEV_USERS:
        cannot_ban(user_id, message)
        return log_message

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker

        if reason:

            bot.sendMessage(
                chat.id,
                f"{mention_html(member.user.id, member.user.first_name)} was kicked by {mention_html(user.id, user.first_name)} in {message.chat.title}\n<b>Reason</b>: <code>{reason}</code>",
                parse_mode=ParseMode.HTML,
            )

        else:

            bot.sendMessage(
                chat.id,
                f"{mention_html(member.user.id, member.user.first_name)} was kicked by {mention_html(user.id, user.first_name)} in {message.chat.title}",
                parse_mode=ParseMode.HTML,
            )

        log = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#KICKED\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
        )
        if reason:
            log += f"\n<b>Reason:</b> {reason}"

        return log

    else:
        message.reply_text("Well damn, I can't kick that user.")

    return log_message


@kigcmd(command='kickme', pass_args=True, filters=Filters.chat_type.groups)
@bot_admin
@can_restrict
@loggable
@spamcheck
def kickme(update: Update, context: CallbackContext) -> str:
    user_id = update.effective_message.from_user.id
    user = update.effective_message.from_user
    chat = update.effective_chat
    if is_user_admin(update, user_id):
        update.effective_message.reply_text("Haha you're stuck with us here.")
        return

    res = update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text("*kicks you out of the group*")

        log = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#KICKED\n"
            "self kick"
            f"<b>User:</b> {mention_html(user.id, user.first_name)}\n"
        )

        return log

    else:
        update.effective_message.reply_text("Huh? I can't :/")


@kigcmd(command='unban', pass_args=True)
@connection_status
@spamcheck
@bot_admin
@can_restrict
@u_admin(UserClass.MOD, AdminPerms.CAN_RESTRICT_MEMBERS)
@loggable
def unban(update: Update, context: CallbackContext) -> Optional[str]:
    message = update.effective_message
    u = update.effective_user
    chat = update.effective_chat
    log_message = ""
    bot, args = context.bot, context.args
    user = res_user(u, message.message_id, chat)

    if message.reply_to_message and message.reply_to_message.sender_chat:
        r = bot.unban_chat_sender_chat(chat_id=chat.id, sender_chat_id=message.reply_to_message.sender_chat.id)
        if r:
            message.reply_text("Channel {} was unbanned successfully from {}".format(
                html.escape(message.reply_to_message.sender_chat.title),
                html.escape(chat.title)
            ),
                parse_mode="html"
            )
            logmsg  = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Channel:</b> {message.reply_to_message.sender_chat.title}"
        f"<b>Channel ID:</b> {message.reply_to_message.sender_chat.id}"
        )
            return logmsg
        else:
            message.reply_text("Failed to ban channel")
        return ""

    user_id, reason = extract_user_and_text(message, args)
    if not user_id:
        message.reply_text("I doubt that's a user.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != 'User not found':
            raise
        message.reply_text("I can't seem to find this user.")
        return log_message
    if user_id == bot.id:
        message.reply_text("How would I unban myself if I wasn't here...?")
        return log_message

    if is_user_in_chat(chat, user_id):
        message.reply_text("Isn't this person already here??")
        return log_message

    chat.unban_member(user_id)

    if reason:

        bot.sendMessage(
                chat.id,
                "{} was unbanned by {} in <b>{}</b>\n<b>Reason</b>: <code>{}</code>".format(
                    mention_html(member.user.id, member.user.first_name), mention_html(user.id, user.first_name), message.chat.title, reason
                ),
                parse_mode=ParseMode.HTML,
            )

    else:

        bot.sendMessage(
                chat.id,
                "{} was unbanned by {} in <b>{}</b>".format(
                    mention_html(member.user.id, member.user.first_name), mention_html(user.id, user.first_name), message.chat.title
                ),
                parse_mode=ParseMode.HTML,
            )


    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
    )
    if reason:
        log += f"\n<b>Reason:</b> {reason}"

    return log


@kigcmd(command='selfunban', pass_args=True)
@connection_status
@bot_admin
@can_restrict
@gloggable
def selfunban(update: Update, context: CallbackContext) -> Optional[str]:
    message = update.effective_message
    user = update.effective_user
    bot, args = context.bot, context.args
    if user.id not in SUDO_USERS or user.id not in WHITELIST_USERS:
        return

    try:
        chat_id = int(args[0])
    except:
        message.reply_text("Give a valid chat ID.")
        return

    chat = bot.getChat(chat_id)

    try:
        member = chat.get_member(user.id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("I can't seem to find this user.")
            return
        else:
            raise

    if is_user_in_chat(chat, user.id):
        message.reply_text("Aren't you already in the chat??")
        return

    chat.unban_member(user.id)
    message.reply_text("Yep, I have unbanned you.")

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
    )

    return log


from tg_bot.modules.language import gs


def get_help(chat):
    return gs(chat, "bans_help")


__mod_name__ = "Bans"
