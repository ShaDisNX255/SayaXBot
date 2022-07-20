import re
import ast
import random
import html

from io import BytesIO
from typing import Optional

from .. import log, dispatcher, SUDO_USERS, spamcheck
from .log_channel import loggable
from .helper_funcs.parsing import Types, parse_filler, revertMd2HTML
from .helper_funcs.chat_status import connection_status
from .helper_funcs.misc import build_keyboard
from .helper_funcs.parsing import get_data, ENUM_FUNC_MAP
from .helper_funcs.handlers import MessageHandlerChecker
from .helper_funcs.string_handling import escape_invalid_curly_brackets

from .helper_funcs.admin_status import (
    user_admin_check,
    AdminPerms,
)

from .helper_funcs.decorators import kigcmd, kigmsg, kigcallback
import tg_bot.modules.sql.notes_sql as sql
from telegram import (
    MAX_MESSAGE_LENGTH,
    InlineKeyboardMarkup,
    Message,
    ParseMode,
    Update,
    InlineKeyboardButton,
)
from telegram.error import BadRequest
from telegram.utils.helpers import mention_html
from telegram.ext import (
    CallbackContext,
    Filters,
)


FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")
STICKER_MATCHER = re.compile(r"^###sticker(!photo)?###:")
BUTTON_MATCHER = re.compile(r"^###button(!photo)?###:(.*?)(?:\s|$)")
MYFILE_MATCHER = re.compile(r"^###file(!photo)?###:")
MYPHOTO_MATCHER = re.compile(r"^###photo(!photo)?###:")
MYAUDIO_MATCHER = re.compile(r"^###audio(!photo)?###:")
MYVOICE_MATCHER = re.compile(r"^###voice(!photo)?###:")
MYVIDEO_MATCHER = re.compile(r"^###video(!photo)?###:")
MYVIDEONOTE_MATCHER = re.compile(r"^###video_note(!photo)?###:")


# Do not async
def get(update: Update, context: CallbackContext, notename: str, show_none: bool = True, no_format: bool = False):
    # sourcery no-metrics
    bot = context.bot
    chat_id = update.effective_message.chat.id
    note_chat_id = update.effective_chat.id
    note = sql.get_note(note_chat_id, notename)
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user
    preview = True
    protect = False
    parseMode = ParseMode.HTML

    if note:
        if MessageHandlerChecker.check_user(update.effective_user.id):
            return
        # If we're replying to a message, reply to that message (unless it's an error)
        if message.reply_to_message:
            reply_id = message.reply_to_message.message_id
        else:
            reply_id = message.message_id
        VALID_NOTE_FORMATTERS = [
            "first",
            "last",
            "fullname",
            "username",
            "id",
            "chatname",
            "mention",
            "user",
            "admin",
            "preview",
            "protect",
        ]
        if valid_format := escape_invalid_curly_brackets(note.value, VALID_NOTE_FORMATTERS):
            if not no_format and "%%%" in valid_format:
                split = valid_format.split("%%%")
                text = random.choice(split) if all(split) else valid_format
            else:
                text = valid_format

            dont_send, preview, protect, text = parse_filler(update, user.id, text)

            if dont_send:
                return

        else:
            text = ""

        keyb = []
        buttons = sql.get_buttons(note_chat_id, notename)
        if no_format:
            text = revertMd2HTML(text, buttons)
        else:
            keyb = build_keyboard(buttons)

        keyboard = InlineKeyboardMarkup(keyb)

        try:
            if note.msgtype in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
                bot.send_message(
                        chat_id,
                        text,
                        reply_to_message_id=reply_id,
                        parse_mode=parseMode,
                        reply_markup=keyboard,
                        disable_web_page_preview=bool(preview),
                        protect_content=bool(protect)
                )
            elif ENUM_FUNC_MAP[note.msgtype] == dispatcher.bot.send_sticker:
                ENUM_FUNC_MAP[note.msgtype](
                        chat_id,
                        note.file,
                        reply_to_message_id=reply_id,
                        reply_markup=keyboard,
                )
            else:
                ENUM_FUNC_MAP[note.msgtype](
                        chat_id,
                        note.file,
                        caption=text,
                        reply_to_message_id=reply_id,
                        parse_mode=parseMode,
                        reply_markup=keyboard,
                        protect_content=bool(protect)
                )

        except BadRequest as excp:
            if excp.message == "Entity_mention_user_invalid":
                message.reply_text(
                        "Looks like you tried to mention someone I've never seen before. If you really "
                    "want to mention them, forward one of their messages to me, and I'll be able "
                    "to tag them!"
                )
            elif FILE_MATCHER.match(note.value):
                message.reply_text(
                        "This note was an incorrectly imported file from another bot - I can't use "
                    "it. If you really need it, you'll have to save it again. In "
                    "the meantime, I'll remove it from your notes list."
                )
                sql.rm_note(chat_id, notename)
            else:

                message.reply_text(
                        "This note could not be sent, as it is incorrectly formatted. "
                    "Try getting the noformat version or ask in @SayaBotSupport if you can't figure out why!"
                )
                log.exception(
                        "Could not parse message #%s in chat %s\n\nare you sure it's using the new format?",
                        notename, str(note_chat_id))
                log.warning("Message was: %s", str(note.value))
        return
    elif show_none:
        message.reply_text("This note doesn't exist")


@kigcmd(command="get")
@spamcheck
@connection_status
def cmd_get(update: Update, context: CallbackContext):
    args = context.args
    if len(args) >= 2:
        get(update, context, args[0].lower(), show_none=True, no_format=bool(args[1].lower() in ["raw", "noformat"]))
    elif len(args) >= 1:
        get(update, context, args[0].lower(), show_none=True)
    else:
        update.effective_message.reply_text("Specify a note name!")


@kigmsg((Filters.regex(r"^#[^\s]+")), group=-14, friendly='get')
@spamcheck
@connection_status
def hash_get(update: Update, context: CallbackContext):
    msg = update.effective_message.text.split()
    no_hash = msg[0][1:].lower()
    if len(msg) >= 2:
        return get(update, context, no_hash, show_none=False, no_format=msg[1].lower() in ["raw", "noformat"])

    get(update, context, no_hash, show_none=False)


@kigmsg((Filters.regex(r"^[/!>]\d+$")), group=-16, friendly='get')
@spamcheck
@connection_status
def slash_get(update: Update, context: CallbackContext):
    message, chat_id = update.effective_message.text, update.effective_chat.id
    no_slash = message[1:]
    note_list = sql.get_all_chat_notes(chat_id)

    try:
        noteid = note_list[int(no_slash) - 1]
        note_name = str(noteid).strip(">").split()[1]
        get(update, context, note_name, show_none=False)
    except IndexError:
        update.effective_message.reply_text("Wrong Note ID!")


@kigcmd(command='save')
@spamcheck
@connection_status
@user_admin_check(AdminPerms.CAN_CHANGE_INFO, allow_mods = True)
@loggable
def save(update: Update, _: CallbackContext) -> Optional[str]:
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat
    user = update.effective_user

    m = msg.text.split(' ', 1)
    if len(m) == 1:
        msg.reply_text("Provide something to save.")
        return
    note_name, text, data_type, content, buttons = get_data(msg)
    note_name = note_name.lower()
    if data_type == Types.TEXT and len(text.strip()) == 0:
        msg.reply_text("Should i save... nothing?")
        return

    sql.add_note_to_db(
        chat_id, note_name, text, data_type, buttons=buttons, file=content
    )

    logmsg = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#SAVENOTE\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>Note:</b> {note_name}"
    )

    msg.reply_text(
        f"Saved Note `{note_name}`!",
        parse_mode=ParseMode.MARKDOWN,
    )

    if msg.reply_to_message and msg.reply_to_message.from_user.is_bot and not msg.text:
        msg.reply_text(
            "Bots are kinda handicapped by telegram, making it hard for bots to "
            "interact with other bots, so I can't save this message "
            "like I usually would - do you mind forwarding it and "
            "then saving that new message? Thanks!"
        )
    return logmsg


@kigcmd(command='clear')
@spamcheck
@connection_status
@user_admin_check(AdminPerms.CAN_CHANGE_INFO, allow_mods = True)
@loggable
def clear(update: Update, context: CallbackContext) -> str:
    args = context.args
    chat = update.effective_chat
    chat_id = chat.id
    user = update.effective_user

    if len(args) >= 1:
        notename = args[0].lower()

        if sql.rm_note(chat_id, notename):
            update.effective_message.reply_text(f"Cleared note '{notename}'.")
            logmsg = (
                    f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#CLEARNOTE\n"
                    f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
                    f"<b>Note:</b> {notename}"
            )
            return logmsg
        else:
            update.effective_message.reply_text("That's not a note in my database!")
            return ''
    else:
        update.effective_message.reply_text("Provide a notename.")
        return ''


@kigcmd(command=['removeallnotes', 'clearall'])
@spamcheck
def clearall(update: Update, _: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user
    member = chat.get_member(user.id)
    if member.status != "creator" and user.id not in SUDO_USERS:
        update.effective_message.reply_text(
            "Only the chat owner can clear all notes at once."
        )
    else:
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="Delete all notes", callback_data="notes_rmall"
                    )
                ],
                [InlineKeyboardButton(text="Cancel", callback_data="notes_cancel")],
            ]
        )
        update.effective_message.reply_text(
            f"Are you sure you would like to clear ALL notes in {chat.title}? This action cannot be undone.",
            reply_markup=buttons,
            parse_mode=ParseMode.MARKDOWN,
        )


@kigcallback(pattern=r"notes_.*")
@loggable
def clearall_btn(update: Update, _: CallbackContext) -> str:
    query = update.callback_query
    chat = update.effective_chat
    message = update.effective_message
    member = chat.get_member(query.from_user.id)
    user = query.from_user
    if query.data == "notes_rmall":
        if member.status == "creator" or query.from_user.id in SUDO_USERS:
            note_list = sql.get_all_chat_notes(chat.id)
            try:
                for notename in note_list:
                    note = notename.name.lower()
                    sql.rm_note(chat.id, note)
                message.edit_text("Deleted all notes.")

                log_message = (
                    f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#CLEAREDALLNOTES\n"
                    f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}"
                )
                return log_message

            except BadRequest:
                return ""

        if member.status == "administrator":
            query.answer("Only owner of the chat can do this.")
            return ""

        if member.status == "member":
            query.answer("You need to be admin to do this.")
            return ""
    elif query.data == "notes_cancel":
        if member.status == "creator" or query.from_user.id in SUDO_USERS:
            message.edit_text("Clearing of all notes has been cancelled.")
            return ""
        if member.status == "administrator":
            query.answer("Only owner of the chat can do this.")
            return ""
        if member.status == "member":
            query.answer("You need to be admin to do this.")
            return ""


@kigcmd(command=["notes", "saved"])
@spamcheck
@connection_status
def list_notes(update: Update, _: CallbackContext):
    chat_id = update.effective_chat.id
    note_list = sql.get_all_chat_notes(chat_id)
    notes = len(note_list) + 1
    msg = "Get note by `/notenumber` or `#notename` \n\n  *ID*    *Note* \n"
    for note_id, note in zip(range(1, notes), note_list):
        if note_id < 10:
            note_name = f"`{note_id:2}.`  `#{(note.name.lower())}`\n"
        else:
            note_name = f"`{note_id}.`  `#{(note.name.lower())}`\n"
        if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
        msg += note_name
    if not note_list:
        update.effective_message.reply_text("No notes in this chat!")

    elif msg != '':
        update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def __import_data__(chat_id, data):  # sourcery no-metrics
    failures = []
    for notename, notedata in data.get("extra", {}).items():
        match = FILE_MATCHER.match(notedata)
        matchsticker = STICKER_MATCHER.match(notedata)
        matchbtn = BUTTON_MATCHER.match(notedata)
        matchfile = MYFILE_MATCHER.match(notedata)
        matchphoto = MYPHOTO_MATCHER.match(notedata)
        matchaudio = MYAUDIO_MATCHER.match(notedata)
        matchvoice = MYVOICE_MATCHER.match(notedata)
        matchvideo = MYVIDEO_MATCHER.match(notedata)
        matchvn = MYVIDEONOTE_MATCHER.match(notedata)

        if match:
            failures.append(notename)
            if notedata := notedata[match.end():].strip():
                sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)
        elif matchsticker:
            if content := notedata[matchsticker.end():].strip():
                sql.add_note_to_db(
                    chat_id, notename[1:], notedata, sql.Types.STICKER, file=content
                )
        elif matchbtn:
            parse = notedata[matchbtn.end():].strip()
            notedata = parse.split("<###button###>")[0]
            buttons = parse.split("<###button###>")[1]
            if buttons := ast.literal_eval(buttons):
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.BUTTON_TEXT,
                    buttons=buttons,
                )
        elif matchfile:
            file = notedata[matchfile.end():].strip()
            file = file.split("<###TYPESPLIT###>")
            notedata = file[1]
            if content := file[0]:
                sql.add_note_to_db(
                    chat_id, notename[1:], notedata, sql.Types.DOCUMENT, file=content
                )
        elif matchphoto:
            photo = notedata[matchphoto.end():].strip()
            photo = photo.split("<###TYPESPLIT###>")
            notedata = photo[1]
            if content := photo[0]:
                sql.add_note_to_db(
                    chat_id, notename[1:], notedata, sql.Types.PHOTO, file=content
                )
        elif matchaudio:
            audio = notedata[matchaudio.end():].strip()
            audio = audio.split("<###TYPESPLIT###>")
            notedata = audio[1]
            if content := audio[0]:
                sql.add_note_to_db(
                    chat_id, notename[1:], notedata, sql.Types.AUDIO, file=content
                )
        elif matchvoice:
            voice = notedata[matchvoice.end():].strip()
            voice = voice.split("<###TYPESPLIT###>")
            notedata = voice[1]
            if content := voice[0]:
                sql.add_note_to_db(
                    chat_id, notename[1:], notedata, sql.Types.VOICE, file=content
                )
        elif matchvideo:
            video = notedata[matchvideo.end():].strip()
            video = video.split("<###TYPESPLIT###>")
            notedata = video[1]
            if content := video[0]:
                sql.add_note_to_db(
                    chat_id, notename[1:], notedata, sql.Types.VIDEO, file=content
                )
        elif matchvn:
            video_note = notedata[matchvn.end():].strip()
            video_note = video_note.split("<###TYPESPLIT###>")
            notedata = video_note[1]
            if content := video_note[0]:
                sql.add_note_to_db(
                    chat_id, notename[1:], notedata, sql.Types.VIDEO_NOTE, file=content
                )
        else:
            sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)

    if failures:
        with BytesIO(str.encode("\n".join(failures))) as output:
            output.name = "failed_imports.txt"
            dispatcher.bot.send_document(
                chat_id,
                document=output,
                filename="failed_imports.txt",
                caption="These files/photos failed to import due to originating "
                "from another bot. This is a telegram API restriction, and can't "
                "be avoided. Sorry for the inconvenience!",
            )


def __stats__():
    return f"• {sql.num_notes()} notes, across {sql.num_chats()} chats."


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, _):
    notes = sql.get_all_chat_notes(chat_id)
    return f"There are `{len(notes)}` notes in this chat."


from .language import gs


def get_help(chat):
    return gs(chat, "notes_help")


__mod_name__ = "Notes"
