import html
import json
import os
from typing import List, Optional

from telegram import Update, ParseMode, TelegramError
from telegram.ext import CommandHandler, run_async, CallbackContext, Filters
from telegram.utils.helpers import mention_html
from telethon import events
from tg_bot import (
    MOD_USERS,
    dispatcher,
    WHITELIST_USERS,
    SUPPORT_USERS,
    SUDO_USERS,
    DEV_USERS,
    OWNER_ID,
    SYS_ADMIN,
)
from .helper_funcs.chat_status import whitelist_plus, dev_plus, sudo_plus
from .helper_funcs.extraction import extract_user
from .log_channel import gloggable
from .sql import nation_sql as sql
from .helper_funcs.decorators import kigcmd

def check_user_id(user_id: int, context: CallbackContext) -> Optional[str]:
    bot = context.bot
    if not user_id:
        return "That...is a chat! baka ka omae?"

    elif user_id == bot.id:
        return "This does not work that way."

    else:
        return None

@kigcmd(command='addsudo')
@dev_plus
@gloggable
def addsudo(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUDO_USERS:
        message.reply_text("This member is already a Sudo user")
        return ""

    if user_id in SUPPORT_USERS:
        rt += "Requested My Devs to promote a Support user to Sudo."
        SUPPORT_USERS.remove(user_id)

    if user_id in WHITELIST_USERS:
        rt += "Requested My Devs to promote a Whitelist user to Sudo."
        WHITELIST_USERS.remove(user_id)

    if user_id in MOD_USERS:
        rt += "Requested A Dev to promote a Moderator to Sudo."
        MOD_USERS.remove(user_id)

    # will add or update their role
    sql.set_royal_role(user_id, "sudos")
    SUDO_USERS.append(user_id)

    update.effective_message.reply_text(
        rt
        + "\nSuccessfully promoted {} to Sudo!".format(
            user_member.first_name
        )
    )

    log_message = (
        f"#SUDO\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@kigcmd(command='addsupport')
@dev_plus
@gloggable
def addsupport(
    update: Update,
    context: CallbackContext,
) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUDO_USERS:
        rt += "Requested My Devs to demote this Sudo to Support"
        SUDO_USERS.remove(user_id)

    if user_id in SUPPORT_USERS:
        message.reply_text("This user is already a Support user.")
        return ""

    if user_id in WHITELIST_USERS:
        rt += "Requested My Devs to promote this Whitelist user to Support"
        WHITELIST_USERS.remove(user_id)

    if user_id in MOD_USERS:
        rt += "Requested A Dev to promote this Moderator to Support"
        MOD_USERS.remove(user_id)

    sql.set_royal_role(user_id, "supports")
    SUPPORT_USERS.append(user_id)

    update.effective_message.reply_text(
        rt + f"\n{user_member.first_name} was added as a Support user!"
    )

    log_message = (
        f"#SUPPORT\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@kigcmd(command='addwhitelist')
@dev_plus
@gloggable
def addwhitelist(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUDO_USERS:
        rt += "This member is a Sudo user, Demoting to Whitelisted user."
        SUDO_USERS.remove(user_id)

    if user_id in SUPPORT_USERS:
        rt += "This user is already a Support user, Demoting to Whitelisted user."
        SUPPORT_USERS.remove(user_id)

    if user_id in MOD_USERS:
        rt += "This user is already a Moderator, Promoting to Whitelisted user."
        MOD_USERS.remove(user_id)

    if user_id in WHITELIST_USERS:
        message.reply_text("This user is already a Whitelist user.")
        return ""

    sql.set_royal_role(user_id, "whitelists")
    WHITELIST_USERS.append(user_id)

    update.effective_message.reply_text(
        rt + f"\nSuccessfully promoted {user_member.first_name} to a Whitelist user!"
    )

    log_message = (
        f"#WHITELIST\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))} \n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message




@kigcmd(command=['addmoderator', 'addmod'])
@dev_plus
@gloggable
def addmod(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUDO_USERS:
        rt += "This member is a Sudo user, Demoting to Moderator."
        SUDO_USERS.remove(user_id)

    if user_id in SUPPORT_USERS:
        rt += "This user is already a Support user, Demoting to Moderator."
        SUPPORT_USERS.remove(user_id)

    if user_id in WHITELIST_USERS:
        rt += "This user is already a Whitelist user, Demoting to Moderator."
        WHITELIST_USERS.remove(user_id)

    if user_id in MOD_USERS:
        message.reply_text("This user is already a Moderator.")
        return ""

    sql.set_royal_role(user_id, "mods")
    MOD_USERS.append(user_id)

    update.effective_message.reply_text(
        rt + f"\nSuccessfully promoted {user_member.first_name} to a Moderator!"
    )

    log_message = (
        f"#MODERATOR\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))} \n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@kigcmd(command=['removesudo', 'rmsudo'])
@dev_plus
@gloggable
def removesudo(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUDO_USERS:
        message.reply_text("Requested My Devs to demote this user to Civilian")
        SUDO_USERS.remove(user_id)
        sql.remove_royal(user_id)

        log_message = (
            f"#UNSUDO\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = "<b>{}:</b>\n".format(html.escape(chat.title)) + log_message

        return log_message

    else:
        message.reply_text("This user is not a Sudo user!")
        return ""


@kigcmd(command=['removesupport', 'rmsupport'])
@dev_plus
@gloggable
def removesupport(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUPPORT_USERS:
        message.reply_text("Requested My Devs to demote this user to Civilian")
        SUPPORT_USERS.remove(user_id)
        sql.remove_royal(user_id)

        log_message = (
            f"#UNSUPPORT\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message

    else:
        message.reply_text("This user is not a Support user!")
        return ""


@kigcmd(command=['removewhitelist', 'rmwhitelist'])
@dev_plus
@gloggable
def removewhitelist(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in WHITELIST_USERS:
        message.reply_text("Demoting to normal user")
        WHITELIST_USERS.remove(user_id)
        sql.remove_royal(user_id)

        log_message = (
            f"#UNWHITELIST\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message
    else:
        message.reply_text("This user is not a Whitelist user!")
        return ""


@kigcmd(command=['removemod', 'removemoderator', 'rmmod'])
@dev_plus
@gloggable
def removemod(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, context)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in MOD_USERS:
        message.reply_text("Demoting to normal user")
        MOD_USERS.remove(user_id)
        sql.remove_royal(user_id)

        log_message = (
            f"#UNMODERATOR\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message
    else:
        message.reply_text("This user is not a Moderator!")
        return ""


# I added extra new lines
nations = """Some users have access levels we call as *"Super Users"*
\nThey are users with special bot priveleges and have commands that can only be used by them.
\n*God* - Only one exists, bot owner.
\nOwner has complete bot access, including bot adminship in chats this bot is at.
\n*Devs* - Devs who can access the bots server and can execute, edit, modify bot code. Can manage other Nations
\n*SUDOS* - Have super user access to the bot.
\n*Support* - Have access to globally ban users across the bot.
\n*Whitelist* - Cannot be banned, muted flood kicked but can be manually banned by admins and can unban themselves if banned.
\n*Moderators* - They have some admin permissions, and cannot be banned, muted flood kicked but can be manually banned by admins.
\n*Disclaimer*: The Super Users in the bot are there for troubleshooting, support, banning potential scammers.
\nReport abuse or ask us more on these at the Support chat.
\nYou can visit @SayaBotSupport to query more about these.
"""


def send_nations(update):
    update.effective_message.reply_text(
        nations, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
    )


@kigcmd(command=['moderators', 'modslist'])
@whitelist_plus
def modslist(update: Update, context: CallbackContext):
    bot = context.bot
    true_mods = list(set(MOD_USERS) - set(DEV_USERS))
    reply = "<b>Known Moderator Members :</b>\n"
    for each_user in true_mods:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)

            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)


@kigcmd(command="whitelistlist")
@whitelist_plus
def whitelistlist(update: Update, context: CallbackContext):
    bot = context.bot
    reply = "<b>Known Whitelist Members :</b>\n"
    for each_user in WHITELIST_USERS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)

@kigcmd(command=["supportlist", "sakuras"])
@whitelist_plus
def supportlist(update: Update, context: CallbackContext):
    bot = context.bot
    reply = "<b>Known Support Members :</b>\n"
    for each_user in SUPPORT_USERS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)

@kigcmd(command=["sudolist", "royals"])
@whitelist_plus
def sudolist(update: Update, context: CallbackContext):
    bot = context.bot
    true_sudo = list(set(SUDO_USERS) - set(DEV_USERS))
    reply = "<b>Known SuperUsers :</b>\n"
    for each_user in true_sudo:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)

@kigcmd(command=["devlist", "eagle"])
@whitelist_plus
def devlist(update: Update, context: CallbackContext):
    bot = context.bot
    true_dev = list(set(DEV_USERS) - {OWNER_ID} - {SYS_ADMIN})
    reply = "<b>My Developers :</b>\n"
    for each_user in true_dev:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)

@kigcmd(command="sysadmins", filters=Filters.user(SYS_ADMIN) | Filters.user(OWNER_ID))
def syslist(update: Update, context: CallbackContext):
    bot = context.bot
    true_adm = list(set({SYS_ADMIN}))
    reply = "<b>System Admins :</b>\n"
    for each_user in true_adm:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)


# from .language import gs

# def get_help(chat):
#     return gs(chat, "nation_help")

__mod_name__ = "Nations"

@kigcmd(command='nationshelp')
def nationshelpp(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    cmdlisttt = "List of commands that can be used bu the nations:\
        \n <b>selfunban</b> : unban user from a group (sudo+ and whitelist)\
        \n <b>rban</b> : remotely ban a user from a group (sudo+)\
        \n <b>runban</b> : remotely unban a user from a group (sudo+)\
        \n <b>rpunch</b> / <b>rkick</b> : remotely kick a user from a group (sudo+)\
        \n <b>rmute</b> : remotely mute a user from a group (sudo+)\
        \n <b>runmute</b> : remotely unmute a user from a group (sudo+)\
        \n <b>speedtest</b> : test the server speed (sudo+)\
        \n <b>chatlist</b> : get the chats that the bot has joined (sudo+)\
        \n <b>echo</b> : echos a message (sudo+)\
        \n <b>lockgroups</b> : toggles enabling joining the groups (dev+)\
        \n <b>getchats</b> : gets the chats where the user has in common with the bot (dev+)\
        \n <b>getinfo</b> : gets user info from a group (dev+)\
        \n <b>stats</b> : get bot stats (sys_admin)\
        \n <b>getstats</b> : get bot avg usage stats (sys_admin)\
        \n <b>ping</b> : ping (sys_admin)\
        \n <b>sh</b> (sys_admin)\
        \n <b>exec</b> (sys_admin)\
        \n <b>eval</b> (sys_admin)\
        \n <b>broadcast(all/group/users)</b> : broadcast a message (sys_admin)"
    if user_id is not (OWNER_ID|SYS_ADMIN) and user_id not in SUDO_USERS and user_id not in DEV_USERS and user_id not in SUPPORT_USERS and user_id not in WHITELIST_USERS:
        return
    else:
        update.effective_message.reply_text(cmdlisttt, parse_mode=ParseMode.HTML)
