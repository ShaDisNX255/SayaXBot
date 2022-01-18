import html
import os
import re
import subprocess
import sys
from time import sleep
from telegram.error import Unauthorized
from telegram.ext.callbackqueryhandler import CallbackQueryHandler
from tg_bot import DEV_USERS, OWNER_ID, dispatcher, telethn, SYS_ADMIN, ALLOW_CHATS
from tg_bot.modules.helper_funcs.chat_status import dev_plus
from telegram import TelegramError, Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, Filters
import asyncio
from statistics import mean
from time import monotonic as time
from telethon import events
from tg_bot.modules.helper_funcs.decorators import kigcmd, register, kigcallback

@kigcmd(command='leave')
@dev_plus
def leave(update: Update, context: CallbackContext):
    bot = context.bot
    args = context.args
    this = update.effective_chat.linked_chat_id
    if args:
        chat_id = str(args[0])
        leave_msg = " ".join(args[1:])
        try:
            if len(leave_msg) >= 1:
                context.bot.send_message(chat_id, leave_msg)
            bot.leave_chat(int(chat_id))
            try:
                update.effective_message.reply_text("Left chat.")
            except Unauthorized:
                pass
        except TelegramError:
            update.effective_message.reply_text("Failed to leave chat for some reason.")
    elif update.effective_message.chat.type != "private":
        chat = update.effective_chat
        # user = update.effective_user
        kb = [[
            InlineKeyboardButton(text="I am sure of this action.", callback_data="leavechat_cb_({})".format(chat.id))
        ]]
        update.effective_message.reply_text("I'm going to leave {}, press the button below to confirm".format(chat.title), reply_markup=InlineKeyboardMarkup(kb))

@kigcallback(pattern=r"leavechat_cb_", run_async=True)
def leave_cb(update: Update, context: CallbackContext):
    bot = context.bot
    callback = update.callback_query
    if callback.from_user.id not in DEV_USERS:
        callback.answer(text="This isn't for you", show_alert=True)
        return

    match = re.match(r"leavechat_cb_\((.+?)\)", callback.data)
    chat = int(match.group(1))
    callback.edit_message_text("I'm outa here.")
    bot.leave_chat(chat_id=chat)

@kigcmd(command='gitpull')
@dev_plus
def gitpull(update: Update, context: CallbackContext):
    sent_msg = update.effective_message.reply_text(
        "Pulling all changes from remote and then attempting to restart."
    )
    subprocess.Popen("git pull", stdout=subprocess.PIPE, shell=True)

    sent_msg_text = sent_msg.text + "\n\nChanges pulled...I guess.. Restarting in "

    for i in reversed(range(5)):
        sent_msg.edit_text(sent_msg_text + str(i + 1))
        sleep(1)

    sent_msg.edit_text("Restarted.")

    os.system("restart.bat")
    os.execv("start.bat", sys.argv)

@kigcmd(command='restart')
@dev_plus
def restart(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        "Starting a new instance and shutting down this one"
    )

    os.execv(sys.executable, ['python3', '-m', 'tg_bot', '2>&1', '|', 'tee', 'logs.txt'])


class Store:
    def __init__(self, func):
        self.func = func
        self.calls = []
        self.time = time()
        self.lock = asyncio.Lock()

    def average(self):
        return round(mean(self.calls), 2) if self.calls else 0

    def __repr__(self):
        return f"<Store func={self.func.__name__}, average={self.average()}>"

    async def __call__(self, event):
        async with self.lock:
            if not self.calls:
                self.calls = [0]
            if time() - self.time > 1:
                self.time = time()
                self.calls.append(1)
            else:
                self.calls[-1] += 1
        await self.func(event)


async def nothing(event):
    pass


messages = Store(nothing)
inline_queries = Store(nothing)
callback_queries = Store(nothing)

telethn.add_event_handler(messages, events.NewMessage())
telethn.add_event_handler(inline_queries, events.InlineQuery())
telethn.add_event_handler(callback_queries, events.CallbackQuery())


# @telethn.on(events.NewMessage(pattern="[/!>]getstats", from_users=[SYS_ADMIN, OWNER_ID]))
@register(pattern='getstats', from_users=[SYS_ADMIN, OWNER_ID], no_args=True)
async def getstats(event):
    await event.reply(
        f"**__BOT EVENT STATISTICS__**\n**Average messages:** {messages.average()}/s\n**Average Callback Queries:** {callback_queries.average()}/s\n**Average Inline Queries:** {inline_queries.average()}/s",
        parse_mode='md'
    )

@kigcmd(command='pipinstall')
@dev_plus
def pip_install(update: Update, context: CallbackContext):
    message = update.effective_message
    args = context.args
    if not args:
        message.reply_text("Enter a package name.")
        return
    if len(args) >= 1:
        cmd = "py -m pip install {}".format(' '.join(args))
        process = subprocess.Popen(
            cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True,
        )
        stdout, stderr = process.communicate()
        reply = ""
        stderr = stderr.decode()
        stdout = stdout.decode()
        if stdout:
            reply += f"*Stdout*\n`{stdout}`\n"
        if stderr:
            reply += f"*Stderr*\n`{stderr}`\n"

        message.reply_text(text=reply, parse_mode=ParseMode.MARKDOWN)

@kigcmd(command='lockdown')
@dev_plus
def allow_groups(update: Update, context: CallbackContext):
    args = context.args
    global ALLOW_CHATS
    if not args:
        state = "Lockdown is " + "on" if not ALLOW_CHATS else "off"
        update.effective_message.reply_text(f"Current state: {state}")
        return
    if args[0].lower() in ["off", "no"]:
        ALLOW_CHATS = True
    elif args[0].lower() in ["yes", "on"]:
        ALLOW_CHATS = False
    else:
        update.effective_message.reply_text("Format: /lockdown Yes/No or Off/On")
        return
    update.effective_message.reply_text("Done! lockdown value toggled.")

@kigcmd(command='getinfo') # todo: flood fed rules gbanstat locks? reports
# ! make as chat and get current if possible
# ? spacing?
@dev_plus      
def get_chat_by_id(update: Update, context: CallbackContext):
    msg = update.effective_message
    args = context.args
    if not args:
        msg.reply_text("<i>Chat ID required</i>", parse_mode=ParseMode.HTML)
        return
    if len(args) >= 1:
        data = context.bot.get_chat(args[0])
        m = "<b>Found chat, below are the details.</b>\n\n"
        m += "<b>Title</b>: {}\n".format(html.escape(data.title))
        m += "<b>Members</b>: {}\n\n".format(data.get_member_count())
        if data.description:
            m += "<i>{}</i>\n\n".format(html.escape(data.description))
        if data.linked_chat_id:
            m += "<b>Linked chat</b>: {}\n".format(data.linked_chat_id)

        m += "<b>Type</b>: {}\n".format(data.type)
        if data.username:
            m += "<b>Username</b>: {}\n".format(html.escape(data.username))
        m += "<b>ID</b>: {}\n".format(data.id)
        m += "\n<b>Permissions</b>:\n <code>{}</code>\n".format(data.permissions)

        if data.invite_link:
            m += "\n<b>Invitelink</b>: {}".format(data.invite_link)

        msg.reply_text(text=m, parse_mode=ParseMode.HTML)



__mod_name__ = "Dev"
