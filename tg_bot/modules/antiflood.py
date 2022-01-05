import html
import re
from typing import Optional

from telegram import (
    Message,
    Chat,
    Update,
    Bot,
    User,
    ChatPermissions,
    ParseMode,
)

from tg_bot import SUDO_USERS, WHITELIST_USERS, dispatcher, spamcheck
from tg_bot.modules.sql.approve_sql import is_approved
from tg_bot.modules.helper_funcs.chat_status import (
    bot_admin,
    can_restrict,
    connection_status,
    is_user_admin,
    user_admin,
    user_can_restrict_no_reply,
)
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import antiflood_sql as sql
from telegram.error import BadRequest
from telegram.ext import (
    Filters,
    CallbackContext,
)
from telegram.utils.helpers import mention_html, escape_markdown
from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.chat_status import (
    is_user_admin,
    user_admin,
    can_restrict,
)
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import antiflood_sql as sql
from tg_bot.modules.connection import connected
from tg_bot.modules.helper_funcs.alternate import send_message
from tg_bot.modules.helper_funcs.decorators import kigcmd, kigcallback, kigmsg

from ..modules.helper_funcs.anonymous import user_admin as u_admin, AdminPerms, resolve_user as res_user, UserClass

FLOOD_GROUP = -5
from typing import Union
def mention_html_chat(chat_id: Union[int, str], name: str) -> str:
    return f'<a href="tg://t.me/{chat_id}">{html.escape(name)}</a>'

# @kigmsg((Filters.all & ~Filters.status_update & Filters.chat_type.groups & ~Filters.update.edited_message & ~Filters.sender_chat), run_async=True, group=FLOOD_GROUP)
@kigmsg((Filters.all & Filters.chat_type.groups & ~Filters.status_update & ~Filters.update.edited_message & ~Filters.user(136817688)), run_async=True, group=FLOOD_GROUP)
@connection_status
@loggable
def check_flood(update, context) -> Optional[str]:
    global execstrings
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    if not user:  # ignore channels
        return ""

     #ignore admins and whitelists
    if (
        is_user_admin(update, user.id)
        or user.id in WHITELIST_USERS
    ):
        sql.update_flood(chat.id, None)
        return ""
      # ignore approved users
    if is_approved(chat.id, user.id):
        sql.update_flood(chat.id, None)
        return

    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            chat.ban_member(user.id)
            execstrings = "Banned"
            tag = "BANNED"
        elif getmode == 2:
            chat.ban_member(user.id)
            chat.unban_member(user.id)
            execstrings = "Kicked"
            tag = "KICKED"
        elif getmode == 3:
            context.bot.restrict_chat_member(
                chat.id, user.id, permissions=ChatPermissions(can_send_messages=False)
            )
            execstrings = "Muted"
            tag = "MUTED"
        elif getmode == 4:
            bantime = extract_time(msg, getvalue)
            chat.ban_member(user.id, until_date=bantime)
            execstrings = "Banned for {}".format(getvalue)
            tag = "TBAN"
        elif getmode == 5:
            mutetime = extract_time(msg, getvalue)
            context.bot.restrict_chat_member(
                chat.id,
                user.id,
                until_date=mutetime,
                permissions=ChatPermissions(can_send_messages=False),
            )
            execstrings = "Muted for {}".format(getvalue)
            tag = "TMUTE"
        send_message(
            update.effective_message, "*Anti Flood Triggered!\n{}!".format(execstrings)
        )

        return (
            "<b>{}:</b>"
            "\n#{}"
            "\n<b>User:</b> {}"
            "\nFlooded the group.".format(
                tag, html.escape(chat.title), mention_html(user.id, user.first_name)
            )
        )

    except BadRequest:
        msg.reply_text(
            "I can't restrict people here, give me permissions first! Until then, I'll disable anti-flood."
        )
        sql.set_flood(chat.id, 0)
        return (
            "<b>{}:</b>"
            "\n#INFO"
            "\nDon't have enough permission to restrict users so automatically disabled anti-flood".format(
                chat.title
            )
        )

@kigmsg((Filters.all & ~Filters.status_update & Filters.chat_type.groups & ~Filters.update.edited_message & Filters.user(136817688)), run_async=True, group=-6)
@connection_status
@loggable
def check_flooda(update, context) -> Optional[str]:
    global execstrings
    msg = update.effective_message  # type: Optional[Message]
    user = msg.sender_chat  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    if not user:  # only for channels
        return ""

    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        chat.ban_sender_chat(user.id)
        execstrings = "Banned Channel"
        tag = "BANNED"
        send_message(
            update.effective_message, "*Anti Flood Triggered!\n{}!".format(execstrings)
        )

        return (
            "<b>{}:</b>"
            "\n#{}"
            "\n<b>User:</b> {}"
            "\nFlooded the group.".format(
                tag, html.escape(chat.title), mention_html_chat(user.id, user.title)
            )
        )

    except BadRequest:
        msg.reply_text(
            "I can't restrict people here, give me permissions first! Until then, I'll disable anti-flood."
        )
        sql.set_flood(chat.id, 0)
        return (
            "<b>{}:</b>"
            "\n#INFO"
            "\nDon't have enough permission to restrict users so automatically disabled anti-flood".format(
                chat.title
            )
        )


@kigcallback(pattern=r"unmute_flooder")
@user_can_restrict_no_reply
@bot_admin
@loggable
def flood_button(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    query = update.callback_query
    user = update.effective_user
    chat = update.effective_chat
    admeme = chat.get_member(user.id)
    match = re.match(r"unmute_flooder\((.+?)\)", query.data)

    if match and admeme.status == "administrator":
        if (
            admeme.can_restrict_members
            or admeme.status != "creator"
            or user.id in SUDO_USERS
        ):
            user_id = match.group(1)
            chat = update.effective_chat.id
            try:
                bot.restrict_chat_member(
                    chat,
                    int(user_id),
                    permissions=ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True,
                    ),
                )
                update.effective_message.edit_text(
                    f"Unmuted by {mention_html(user.id, user.first_name)}.",
                    parse_mode="HTML",
                )
                logmsg = (
                        f"<b>{html.escape(chat.title)}:</b>\n"
                        f"#UNMUTE_FLOODER\n"
                        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
                        f"<b>User:</b> {mention_html(user_id, html.escape(user.first_name))}\n"
                )
                return logmsg
            except:
                pass

@kigcmd(command='setflood', pass_args=True, filters=Filters.chat_type.groups)
@spamcheck
@connection_status
@can_restrict
@u_admin(UserClass.ADMIN, AdminPerms.CAN_CHANGE_INFO)
@loggable
def set_flood(update, context) -> str:  # sourcery no-metrics
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    args = context.args
    u = update.effective_user  # type: Optional[User]
    user = res_user(u, message.message_id, chat)

    conn = connected(context.bot, update, chat, user.id, need_admin=True)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "This command is meant to use in group not in PM",
            )
            return ""
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if len(args) >= 1:
        val = args[0].lower()
        if val in ["off", "no", "0"]:
            sql.set_flood(chat_id, 0)
            if conn:
                text = message.reply_text(
                    "Antiflood has been disabled in {}.".format(chat_name)
                )
            else:
                text = message.reply_text("Antiflood has been disabled.")

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat_id, 0)
                if conn:
                    text = message.reply_text(
                        "Antiflood has been disabled in {}.".format(chat_name)
                    )
                else:
                    text = message.reply_text("Antiflood has been disabled.")
                return (
                    "<b>{}:</b>"
                    "\n#SETFLOOD"
                    "\n<b>Admin:</b> {}"
                    "\nDisable antiflood.".format(
                        html.escape(chat_name), mention_html(user.id, user.first_name)
                    )
                )

            elif amount <= 3:
                send_message(
                    update.effective_message,
                    "Antiflood must be either 0 (disabled) or number greater than 3!",
                )
                return ""

            else:
                sql.set_flood(chat_id, amount)
                if conn:
                    text = message.reply_text(
                        "Anti-flood has been set to {} in chat: {}".format(
                            amount, chat_name
                        )
                    )
                else:
                    text = message.reply_text(
                        "Successfully updated anti-flood limit to {}!".format(amount)
                    )
                return (
                    "<b>{}:</b>"
                    "\n#SETFLOOD"
                    "\n<b>Admin:</b> {}"
                    "\nSet antiflood to <code>{}</code>.".format(
                        html.escape(chat_name),
                        mention_html(user.id, user.first_name),
                        amount,
                    )
                )

        else:
            message.reply_text("Invalid argument please use a number, 'off' or 'no'")
    else:
        message.reply_text(
            (
                "Use `/setflood number` to enable anti-flood.\nOr use `/setflood off` to disable antiflood!."
            ),
            parse_mode="markdown",
        )
    return ""

@kigcmd(command="flood", filters=Filters.chat_type.groups) #? add flood mode here and perms
@connection_status
@spamcheck
@user_admin
def flood(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message

    conn = connected(context.bot, update, chat, user.id, need_admin=False)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "This command is meant to use in group not in PM",
            )
            return
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    limit = sql.get_flood_limit(chat_id)
    getmode, getvalue = sql.get_flood_setting(chat.id)
    if getmode == 1:
        settypeflood = "ban"
    elif getmode == 2:
        settypeflood = "kick"
    elif getmode == 3:
        settypeflood = "mute"
    elif getmode == 4:
        settypeflood = "tban for {}".format(getvalue)
    elif getmode == 5:
        settypeflood = "tmute for {}".format(getvalue)
    if limit == 0:
        if conn:
            text = msg.reply_text(
                "I'm not enforcing any flood control in {}!".format(chat_name)
            )
        else:
            text = msg.reply_text("I'm not enforcing any flood control here!")


    elif conn:
        text = msg.reply_text(
            "I'm currently restricting members after {} consecutive messages in {}.\nThe current flood mode is:\n  {}".format(
                limit, chat_name, settypeflood
            )
        )
    else:
        text = msg.reply_text(
            "I'm currently restricting members after {} consecutive messages.\nThe current flood mode is:\n  {}".format(
                limit, settypeflood
            )
        )

@kigcmd(command="setfloodmode", pass_args=True, filters=Filters.chat_type.groups) # ! make loggable
@spamcheck
@u_admin(UserClass.ADMIN, AdminPerms.CAN_CHANGE_INFO)
def set_flood_mode(update, context):  # sourcery no-metrics
    global settypeflood
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    args = context.args
    u = update.effective_user  # type: Optional[User]
    user = res_user(u, msg.message_id, chat)

    conn = connected(context.bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "This command is meant to use in group not in PM",
            )
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if args:
        if args[0].lower() == "ban":
            settypeflood = "ban"
            sql.set_flood_strength(chat_id, 1, "0")
        elif args[0].lower() == "kick":
            settypeflood = "kick"
            sql.set_flood_strength(chat_id, 2, "0")
        elif args[0].lower() == "mute":
            settypeflood = "mute"
            sql.set_flood_strength(chat_id, 3, "0")
        elif args[0].lower() == "tban":
            if len(args) == 1:
                teks = """It looks like you tried to set time value for antiflood but you didn't specified time; Try, `/setfloodmode tban <timevalue>`.
Examples of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = "tban for {}".format(args[1])
            sql.set_flood_strength(chat_id, 4, str(args[1]))
        elif args[0].lower() == "tmute":
            if len(args) == 1:
                teks = (
                    update.effective_message,
                    """It looks like you tried to set time value for antiflood but you didn't specified time; Try, `/setfloodmode tmute <timevalue>`.
Examples of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks.""",
                )
                send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = "tmute for {}".format(args[1])
            sql.set_flood_strength(chat_id, 5, str(args[1]))
        else:
            send_message(
                update.effective_message, "I only understand ban/kick/mute/tban/tmute!"
            )
            return
        if conn:
            text = msg.reply_text(
                "Exceeding consecutive flood limit will result in {} in {}!".format(
                    settypeflood, chat_name
                )
            )
        else:
            text = msg.reply_text(
                "Exceeding consecutive flood limit will result in {}!".format(
                    settypeflood
                )
            )
        return (
            "<b>{}:</b>\n"
            "<b>Admin:</b> {}\n"
            "Has changed antiflood mode. User will {}.".format(
                settypeflood,
                html.escape(chat.title),
                mention_html(user.id, user.first_name),
            )
        )
    else:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            settypeflood = "ban"
        elif getmode == 2:
            settypeflood = "kick"
        elif getmode == 3:
            settypeflood = "mute"
        elif getmode == 4:
            settypeflood = "tban for {}".format(getvalue)
        elif getmode == 5:
            settypeflood = "tmute for {}".format(getvalue)
        if conn:
            text = msg.reply_text(
                "Sending more messages than flood limit will result in {} in {}.".format(
                    settypeflood, chat_name
                )
            )
        else:
            text = msg.reply_text(
                "Sending more message than flood limit will result in {}.".format(
                    settypeflood
                )
            )
    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return "Not enforcing to flood control."
    else:
        return "Antiflood has been set to`{}`.".format(limit)

from tg_bot.modules.language import gs

def get_help(chat):
    return gs(chat, "antiflood_help")

__mod_name__ = "Anti-Flood"


