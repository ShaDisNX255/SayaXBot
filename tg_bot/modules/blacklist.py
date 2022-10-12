from enum import IntEnum
import html
import re
from typing import List

from telegram import ChatPermissions, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext, Filters
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.utils.helpers import mention_html
import tg_bot.modules.sql.blacklist_sql as sql
from .. import SUDO_USERS, log, spamcheck
from .sql.approve_sql import is_approved
from .helper_funcs.chat_status import connection_status
from .helper_funcs.extraction import extract_text
from .helper_funcs.misc import split_message
from .log_channel import loggable
from .warns import warn
from .helper_funcs.string_handling import extract_time
from .helper_funcs.decorators import kigcmd, kigmsg, kigcallback
from .helper_funcs.alternate import send_message, typing_action

from .helper_funcs.admin_status import (
    user_admin_check,
    bot_admin_check,
    AdminPerms,
    user_not_admin_check,
)

BLACKLIST_GROUP = -3


class BlacklistActions(IntEnum):
    default = 0
    delete = 1
    warn = 2
    mute = 3
    kick = 4
    ban = 5


@kigcmd(command=["blacklist", "blacklists", "blocklist", "blocklists"], pass_args=True, admin_ok=True)
@spamcheck
@user_admin_check()
@typing_action
def blacklist(update, context):
    chat = update.effective_chat
    args = context.args

    filter_list = "<b>Blacklist settings for {}</b>:\n".format(html.escape(chat.title))

    getmode, getvalue = sql.get_blacklist_setting(chat.id)
    bl_type = "Do nothing"
    match getmode:
        case 1:
            bl_type = "Delete"
        case 2:
            bl_type = "Warn"
        case 3:
            bl_type = "Mute"
        case 4:
            bl_type = "Kick"
        case 5:
            bl_type = "Ban"
        case 6:
            bl_type = "Temporarily Ban for {}".format(getvalue)
        case 7:
            bl_type = "Temporarily Mute for {}".format(getvalue)

    filter_list += "ㅤ<b>Current blacklist mode:</b>\n     {}\n".format(bl_type)
    all_blacklisted = sql.get_chat_blacklist(chat.id)
    filter_list += "\nㅤ<b>Current blacklisted words (<i>{}</i>):</b>\n".format(len(all_blacklisted))
    for i in all_blacklisted:
        trigger = i[0]
        action = BlacklistActions(i[1]).name
        filter_list += "  - <code>{}</code>\n    <b>Action:</b> {}\n".format(html.escape(trigger), action)

    split_text = split_message(filter_list)
    for text in split_text:
        if len(all_blacklisted) == 0:
            send_message(
                update.effective_message,
                "No blacklisted words in <b>{}</b>!".format(chat.title),
                parse_mode=ParseMode.HTML,
            )
            return
        send_message(update.effective_message, text, parse_mode=ParseMode.HTML)


@kigcmd(command=["addblacklist", "addblocklist"], pass_args=True)
@spamcheck
@connection_status
@bot_admin_check(AdminPerms.CAN_RESTRICT_MEMBERS)
@user_admin_check(AdminPerms.CAN_CHANGE_INFO)
@typing_action
def add_blacklist(update, _):
    msg = update.effective_message
    chat = update.effective_chat
    words = msg.text.split(None, 1)

    chat_name = html.escape(chat.title)

    act = BlacklistActions.default
    bl = ""
    if len(words) > 1:
        text = words[1]
        to_blacklist: List[str] = list({trigger.strip() for trigger in text.split("\n") if trigger.strip()})

        for trigger in to_blacklist:
            bl, action = extract_bl_and_action(trigger)
            if not sql.add_to_blacklist(chat.id, bl, action.value):
                return msg.reply_text("The maximum number of blacklists (100) has been reached for this chat.")
            act = action.name

        if len(to_blacklist) == 1:
            reply = "Added blacklist trigger: <code>{}</code> with <b>{}</b> action!"
            send_message(
                update.effective_message,
                reply.format(
                    html.escape(bl), act
                ),
                parse_mode=ParseMode.HTML,
            )

        else:
            reply = "Added blacklist <code>{}</code> in chat: <b>{}</b>!"
            send_message(
                update.effective_message,
                reply.format(
                    len(to_blacklist), chat_name
                ),
                parse_mode=ParseMode.HTML,
            )

    else:
        send_message(
            update.effective_message,
            "Tell me which words you would like to add in blacklist.",
        )


def extract_bl_and_action(text: str) -> (str, BlacklistActions):
    if not text or not ("{" and "}" in text):
        return text, BlacklistActions.default

    action = text[text.rindex("{") + 1: text.rindex("}")]

    if action not in BlacklistActions.__members__:
        return "", BlacklistActions.default

    return text[:text.rindex("{") - 1], BlacklistActions[action]


@kigcmd(command=["unblacklist", "unblocklist"], pass_args=True)
@spamcheck
@typing_action
@connection_status
@bot_admin_check(AdminPerms.CAN_RESTRICT_MEMBERS)
@user_admin_check(AdminPerms.CAN_CHANGE_INFO)
def unblacklist(update, _):
    msg = update.effective_message
    chat = update.effective_chat
    words = msg.text.split(None, 1)

    chat_id = chat.id
    chat_name = html.escape(chat.title)

    if len(words) > 1:
        text = words[1]
        to_unblacklist = list(
            {
                trigger.strip()
                for trigger in text.split("\n")
                if trigger.strip()
            }
        )

        successful = 0
        for trigger in to_unblacklist:
            success = sql.rm_from_blacklist(chat_id, trigger.lower())
            if success:
                successful += 1

        if len(to_unblacklist) == 1:
            if successful:
                send_message(
                    update.effective_message,
                    "Removed <code>{}</code> from blacklist in <b>{}</b>!".format(
                        html.escape(to_unblacklist[0]), chat_name
                    ),
                    parse_mode=ParseMode.HTML,
                )
            else:
                send_message(
                    update.effective_message, "This is not a blacklist trigger!"
                )

        elif successful == len(to_unblacklist):
            send_message(
                update.effective_message,
                "Removed <code>{}</code> from blacklist in <b>{}</b>!".format(
                    successful, chat_name
                ),
                parse_mode=ParseMode.HTML,
            )

        elif not successful:
            send_message(
                update.effective_message,
                "None of these triggers exist so it can't be removed.".format(
                    successful, len(to_unblacklist) - successful
                ),
                parse_mode=ParseMode.HTML,
            )

        else:
            send_message(
                update.effective_message,
                "Removed <code>{}</code> from blacklist. {} did not exist, "
                "so were not removed.".format(
                    successful, len(to_unblacklist) - successful
                ),
                parse_mode=ParseMode.HTML,
            )
    else:
        send_message(
            update.effective_message,
            "Tell me which words you would like to remove from blacklist!",
        )


@kigcmd(command=["blacklistmode", "blocklistmode"], pass_args=True)
@spamcheck
@typing_action
@connection_status
@bot_admin_check(AdminPerms.CAN_RESTRICT_MEMBERS)
@user_admin_check(AdminPerms.CAN_CHANGE_INFO)
@loggable
def blacklist_mode(update, context):  # sourcery no-metrics
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    args = context.args

    chat_id = chat.id
    chat_name = html.escape(chat.title)

    if args:
        if args[0].lower() in ["off", "nothing", "no"]:
            settypeblacklist = "do nothing"
            sql.set_blacklist_strength(chat_id, 0, "0")
        elif args[0].lower() in ["del", "delete"]:
            settypeblacklist = "will delete blacklisted message"
            sql.set_blacklist_strength(chat_id, 1, "0")
        elif args[0].lower() == "warn":
            settypeblacklist = "warn the sender"
            sql.set_blacklist_strength(chat_id, 2, "0")
        elif args[0].lower() == "mute":
            settypeblacklist = "mute the sender"
            sql.set_blacklist_strength(chat_id, 3, "0")
        elif args[0].lower() == "kick":
            settypeblacklist = "kick the sender"
            sql.set_blacklist_strength(chat_id, 4, "0")
        elif args[0].lower() == "ban":
            settypeblacklist = "ban the sender"
            sql.set_blacklist_strength(chat_id, 5, "0")
        elif args[0].lower() == "tban":
            if len(args) == 1:
                teks = """It looks like you tried to set time value for blacklist but you didn't specified time; Try, `/blacklistmode tban <timevalue>`.

Examples of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return ""
            restime = extract_time(msg, args[1])
            if not restime:
                teks = """Invalid time value!
Example of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return ""
            settypeblacklist = "temporarily ban for {}".format(args[1])
            sql.set_blacklist_strength(chat_id, 6, str(args[1]))
        elif args[0].lower() == "tmute":
            if len(args) == 1:
                teks = """It looks like you tried to set time value for blacklist but you didn't specified  time; try, `/blacklistmode tmute <timevalue>`.

Examples of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return ""
            restime = extract_time(msg, args[1])
            if not restime:
                teks = """Invalid time value!
Examples of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return ""
            settypeblacklist = "temporarily mute for {}".format(args[1])
            sql.set_blacklist_strength(chat_id, 7, str(args[1]))
        else:
            send_message(
                update.effective_message,
                "I only understand: off/del/warn/ban/kick/mute/tban/tmute!",
            )
            return ""
        text = "Changed blacklist mode: `{}`!".format(settypeblacklist)
        send_message(update.effective_message, text, parse_mode="markdown")
        return (
            "<b>{}:</b>\n"
            "<b>Admin:</b> {}\n"
            "Changed the blacklist mode. will {}.".format(
                html.escape(chat.title),
                mention_html(user.id, user.first_name),
                settypeblacklist,
            )
        )
    else:
        getmode, getvalue = sql.get_blacklist_setting(chat.id)
        bl_type = "Do nothing"
        match getmode:
            case 1:
                bl_type = "Delete"
            case 2:
                bl_type = "Warn"
            case 3:
                bl_type = "Mute"
            case 4:
                bl_type = "Kick"
            case 5:
                bl_type = "Ban"
            case 6:
                bl_type = "Temporarily Ban for {}".format(getvalue)
            case 7:
                bl_type = "Temporarily Mute for {}".format(getvalue)
        text = "Current blacklistmode: *{}*.".format(bl_type)
        send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)
    return ""


def findall(p, s):
    i = s.find(p)
    while i != -1:
        yield i
        i = s.find(p, i + 1)


@kigmsg(((Filters.text | Filters.command | Filters.sticker | Filters.photo) & Filters.chat_type.groups),
        group=BLACKLIST_GROUP)
@user_not_admin_check
def del_blacklist(update: Update, context: CallbackContext):  # sourcery no-metrics
    chat = update.effective_chat
    message = update.effective_message
    user = message.sender_chat or update.effective_user
    bot = context.bot
    to_match = extract_text(message)
    if not to_match:
        return
    if is_approved(chat.id, user.id):
        return
    getmode, value = sql.get_blacklist_setting(chat.id)

    chat_filters = sql.get_chat_blacklist(chat.id)

    for item in chat_filters:
        trigger = str(item[0])
        getmode = (int(item[1]) if int(item[1]) > 0 else getmode)

        pattern = r"( |^|[^\w])" + re.escape(trigger) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            try:
                match getmode:
                    case 0:
                        return
                    case 1:
                        message.delete()
                    case 2:
                        message.delete()
                        warn(
                            update.effective_user,
                            update,
                            ("Using blacklisted trigger: {}".format(trigger)),
                            message,
                            update.effective_user,
                        )
                        return
                    case 3:
                        message.delete()
                        bot.restrict_chat_member(
                            chat.id,
                            update.effective_user.id,
                            permissions=ChatPermissions(can_send_messages=False),
                        )
                        bot.sendMessage(
                            chat.id,
                            f"Muted {user.first_name} for using Blacklisted word: {trigger}!",
                        )
                        return
                    case 4:
                        message.delete()
                        res = chat.unban_member(update.effective_user.id)
                        if res:
                            bot.sendMessage(
                                chat.id,
                                f"Kicked {user.first_name} for using Blacklisted word: {trigger}!",
                            )
                        return
                    case 5:
                        message.delete()
                        chat.ban_member(user.id)
                        bot.sendMessage(
                            chat.id,
                            f"Banned {user.first_name} for using Blacklisted word: {trigger}",
                        )
                        return
                    case 6:
                        message.delete()
                        bantime = extract_time(message, value)
                        chat.ban_member(user.id, until_date=bantime)
                        bot.sendMessage(
                            chat.id,
                            f"Banned {user.first_name} until '{value}' for using Blacklisted word: {trigger}!",
                        )
                        return
                    case 7:
                        message.delete()
                        mutetime = extract_time(message, value)
                        bot.restrict_chat_member(
                            chat.id,
                            user.id,
                            until_date=mutetime,
                            permissions=ChatPermissions(can_send_messages=False),
                        )
                        bot.sendMessage(
                            chat.id,
                            f"Muted {user.first_name} until '{value}' for using Blacklisted word: {trigger}!",
                        )
                        return
            except BadRequest as excp:
                if excp.message != "Message to delete not found":
                    log.exception("Error while deleting blacklist message.")
            break


@kigcmd(command=["removeallblacklists", "removeallblocklists", "unblacklistall"], filters=Filters.chat_type.groups)
@spamcheck
def rmall_filters(update, context):
    chat = update.effective_chat
    user = update.effective_user
    member = chat.get_member(user.id)
    if member.status != "creator" and user.id not in SUDO_USERS:
        update.effective_message.reply_text(
            "Only the chat owner can clear all blacklists at once."
        )
    else:
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="Remove all Blacklists", callback_data="blacklists_rmall"
                    )
                ],
                [InlineKeyboardButton(text="Cancel", callback_data="blacklists_cancel")],
            ]
        )
        update.effective_message.reply_text(
            f"Are you sure you would like to stop ALL blacklists in {chat.title}? This action cannot be undone.",
            reply_markup=buttons,
            parse_mode=ParseMode.MARKDOWN,
        )


@kigcallback(pattern=r"blacklists_.*")
@loggable
def rmall_callback(update, context) -> str:
    query = update.callback_query
    chat = update.effective_chat
    msg = update.effective_message
    member = chat.get_member(query.from_user.id)
    user = query.from_user
    if query.data == "blacklists_rmall":
        if member.status == "creator" or query.from_user.id in SUDO_USERS:
            allfilters = sql.get_chat_blacklist(chat.id)
            if not allfilters:
                msg.edit_text("No blacklists in this chat, nothing to stop!")
                return ""

            count = 0
            filterlist = []
            for x in allfilters:
                count += 1
                filterlist.append(x)
            print(filterlist)
            for i in filterlist:
                sql.rm_from_blacklist(chat.id, i[0])

            msg.edit_text(f"Cleaned {count} bl in {chat.title}")

            log_message = (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#CLEAREDALLBLACKLISTS\n"
                f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}"
            )
            return log_message

        if member.status == "administrator":
            query.answer("Only owner of the chat can do this.")
            return ""

        if member.status == "member":
            query.answer("You need to be admin to do this.")
            return ""
    elif query.data == "blacklists_cancel":
        if member.status == "creator" or query.from_user.id in SUDO_USERS:
            msg.edit_text("Clearing of all filters has been cancelled.")
            return ""
        if member.status == "administrator":
            query.answer("Only owner of the chat can do this.")
            return ""
        if member.status == "member":
            query.answer("You need to be admin to do this.")
            return ""


def __import_data__(chat_id, data):
    # set chat blacklist
    blacklist = data.get("blacklist", {})
    for trigger in blacklist:
        sql.add_to_blacklist(chat_id, trigger)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    blacklisted = sql.num_blacklist_chat_filters(chat_id)
    return "There are {} blacklisted words.".format(blacklisted)


def __stats__():
    return "• {} blacklist triggers, across {} chats.".format(
        sql.num_blacklist_filters(), sql.num_blacklist_filter_chats()
    )


__mod_name__ = "Blacklists"

from .language import gs


def get_help(chat):
    return gs(chat, "blacklist_help")
