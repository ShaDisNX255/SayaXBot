import html
from typing import Optional
from telegram.callbackquery import CallbackQuery
import re
from telegram.inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.user import User

from tg_bot import (
    WHITELIST_USERS, 
    spamcheck,
    DEV_USERS,
    MOD_USERS,
    SUDO_USERS,
    SUPPORT_USERS,
    OWNER_ID,
    WHITELIST_USERS,
)
from tg_bot.modules.helper_funcs.chat_status import (
    bot_admin,
    can_restrict,
    connection_status,
    is_user_ban_protected,
    user_can_restrict_no_reply,
)
from tg_bot.modules.helper_funcs.extraction import extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable
from telegram import Bot, Chat, ChatPermissions, ParseMode, Update, replymarkup
from telegram.error import BadRequest
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html
from tg_bot.modules.language import gs
from tg_bot.modules.helper_funcs.decorators import kigcmd, kigcallback

from ..modules.helper_funcs.anonymous import user_admin as u_admin, AdminPerms, resolve_user as res_user, UserClass


def check_user(user_id: int, bot: Bot, update: Update) -> Optional[str]:
    if not user_id:
        return "You don't seem to be referring to a user or the ID specified is incorrect.."

    try:
        member = update.effective_chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == 'User not found':
            return "I can't seem to find this user"
        else:
            raise
    if user_id == bot.id:
        return "I'm not gonna MUTE myself, How high are you?"

    if is_user_ban_protected(update, user_id, member) and user_id not in DEV_USERS:
        if user_id == OWNER_ID:
            return "I'd never ban my owner."
        elif user_id in DEV_USERS:
            return "I can't act against our own."
        elif user_id in SUDO_USERS:
            return "My sudos are ban immune"
        elif user_id in SUPPORT_USERS:
            return "My support users are ban immune"
        elif user_id in WHITELIST_USERS:
            return "Bring an order from My Devs to fight a Whitelist user."
        elif user_id in MOD_USERS:
            return "Moderators cannot be muted, report abuse at @SayaBotSupport."
        else:
            return "Can't. Find someone else to mute but not this one."

    return None


@kigcmd(command='mute')
@spamcheck
@connection_status
@bot_admin
@can_restrict
@u_admin(UserClass.MOD, AdminPerms.CAN_RESTRICT_MEMBERS)
@loggable
def mute(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    args = context.args

    chat = update.effective_chat
    u = update.effective_user
    message = update.effective_message
    user = res_user(u, message.message_id, chat)

    user_id, reason = extract_user_and_text(message, args)
    reply = check_user(user_id, bot, update)

    if reply:
        message.reply_text(reply)
        return ""

    member = chat.get_member(user_id)

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#MUTE\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
    )

    if reason:
        log += f"\n<b>Reason:</b> {reason}"

    if member.can_send_messages is None or member.can_send_messages:
        chat_permissions = ChatPermissions(can_send_messages=False)
        bot.restrict_chat_member(chat.id, user_id, chat_permissions)
        mutemsg = "{} was muted by {} in <b>{}</b>".format(
                    mention_html(member.user.id, member.user.first_name), user.first_name, message.chat.title
        )
        if reason:
            mutemsg += f"\n<b>Reason</b>: <code>{reason}</code>"


        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔊 Unmute", callback_data="cb_unmute({})".format(user_id)
                    )
                ]
            ]
        )

        context.bot.send_message(
            chat.id,
            mutemsg,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
            )


        return log

    else:
        message.reply_text("This user is already muted!")

    return ""



@kigcallback(pattern=r"cb_unmute")
@user_can_restrict_no_reply
@bot_admin
@loggable
def button(update: Update, context: CallbackContext) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    user: Optional[User] = update.effective_user
    chat = update.effective_chat
    admeme = chat.get_member(user.id)
    match = re.match(r"cb_unmute\((.+?)\)", query.data)
    if match and admeme.status == "administrator":

        bot = context.bot
        user_id = match.group(1)
        chat: Optional[Chat] = update.effective_chat
        user_member = chat.get_member(user_id)

        if user_member.status in ["kicked", "left"]:
            user_member.reply_text(
                "This user isn't even in the chat, unmuting them won't make them talk more than they "
                "already do!"
            )

        elif (
                user_member.can_send_messages
                and user_member.can_send_media_messages
                and user_member.can_send_other_messages
                and user_member.can_add_web_page_previews
            ):
            update.effective_message.edit_tex("This user already has the right to speak.")
        else:
            chat_permissions = ChatPermissions(
                can_send_messages=True,
                can_invite_users=True,
                can_pin_messages=True,
                can_send_polls=True,
                can_change_info=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            )
            try:
                bot.restrict_chat_member(chat.id, int(user_id), chat_permissions)
            except BadRequest:
                pass


            update.effective_message.edit_text(
                "{} was unmuted by {}.".format(mention_html(user_id, user_member.user.first_name), user.first_name),
                parse_mode=ParseMode.HTML,
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#UNMUTE\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"<b>User:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"
            )


@kigcmd(command='unmute')
@spamcheck
@connection_status
@bot_admin
@can_restrict
@u_admin(UserClass.MOD, AdminPerms.CAN_RESTRICT_MEMBERS)
@loggable
def unmute(update: Update, context: CallbackContext) -> str:
    bot, args = context.bot, context.args
    chat = update.effective_chat
    u = update.effective_user
    message = update.effective_message
    user = res_user(u, message.message_id, chat)

    user_id, reason = extract_user_and_text(message, args)
    if not user_id:
        message.reply_text(
            "You'll need to either give me a username to unmute, or reply to someone to be unmuted."
        )
        return ""

    member = chat.get_member(int(user_id))

    if member.status in ["kicked", "left"]:
        message.reply_text(
            "This user isn't even in the chat, unmuting them won't make them talk more than they "
            "already do!"
        )

    elif (
            member.can_send_messages
            and member.can_send_media_messages
            and member.can_send_other_messages
            and member.can_add_web_page_previews
    ):
        message.reply_text("This user already has the right to speak.")
    else:
        chat_permissions = ChatPermissions(
            can_send_messages=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_send_polls=True,
            can_change_info=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
        )
        try:
            bot.restrict_chat_member(chat.id, int(user_id), chat_permissions)
        except BadRequest:
            pass
        unmutemsg = "{} was unmuted by {} in <b>{}</b>".format(
            mention_html(member.user.id, member.user.first_name), user.first_name, message.chat.title
        )
        if reason:
            unmutemsg += "\n<b>Reason</b>: <code>{}</code>".format(reason)
        bot.sendMessage(
        chat.id,
       unmutemsg,
        parse_mode=ParseMode.HTML,
        )
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#UNMUTE\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
        )
    return ""


@kigcmd(command=['tmute', 'tempmute'])
@spamcheck
@connection_status
@bot_admin
@can_restrict
@u_admin(UserClass.MOD, AdminPerms.CAN_RESTRICT_MEMBERS)
@loggable
def temp_mute(update: Update, context: CallbackContext) -> str:
    bot, args = context.bot, context.args
    chat = update.effective_chat
    u = update.effective_user
    message = update.effective_message
    user = res_user(u, message.message_id, chat)

    user_id, reason = extract_user_and_text(message, args)
    reply = check_user(user_id, bot, update)

    if reply:
        message.reply_text(reply)
        return ""

    member = chat.get_member(user_id)

    if not reason:
        message.reply_text("You haven't specified a time to mute this user for!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    reason = split_reason[1] if len(split_reason) > 1 else ""
    mutetime = extract_time(message, time_val)

    if not mutetime:
        return ""

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#TEMP MUTED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}\n"
        f"<b>Time:</b> {time_val}"
    )
    if reason:
        log += f"\n<b>Reason:</b> {reason}"

    try:
        if member.can_send_messages is None or member.can_send_messages:
            chat_permissions = ChatPermissions(can_send_messages=False)
            bot.restrict_chat_member(
                chat.id, user_id, chat_permissions, until_date=mutetime
            )
            bot.sendMessage(
                chat.id,
                f"Muted <b>{html.escape(member.user.first_name)}</b> for {time_val}!\n<b>Reason</b>: <code>{reason}</code>",
                parse_mode=ParseMode.HTML,
            )
            return log
        else:
            message.reply_text("This user is already muted.")

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text(f"Muted for {time_val}!", quote=False)
            return log
        else:
            log.warning(update)
            log.exception(
                "ERROR muting user %s in chat %s (%s) due to %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("Well damn, I can't mute that user.")

    return ""


def get_help(chat):
    return gs(chat, "muting_help")


__mod_name__ = "Muting"
