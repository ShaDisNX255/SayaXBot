from telegram.utils.helpers import escape_markdown
from tg_bot import dispatcher
from .helper_funcs.decorators import kigcallback
from telegram import (
    ParseMode,
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import CallbackContext
from .language import gs

def fmt_md_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        gs(update.effective_chat.id, "md_help"),
        parse_mode=ParseMode.HTML,
    )


def fmt_filling_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        gs(update.effective_chat.id, "filling_help"),
        parse_mode=ParseMode.HTML,
    )



@kigcallback(pattern=r"fmt_help_")
def fmt_help(update: Update, context: CallbackContext):
    query = update.callback_query
    bot = context.bot
    help_info = query.data.split("fmt_help_")[1]
    if help_info == "md":
        help_text = gs(update.effective_chat.id, "md_help")
    elif help_info == "filling":
        help_text = gs(update.effective_chat.id, "filling_help") 
    query.message.edit_text(
        text=help_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="Back", callback_data=f"help_module({__mod_name__.lower()})"),
            InlineKeyboardButton(text='Support', url='https://t.me/SayaBotSupport')]]
        ),
    )
    bot.answer_callback_query(query.id)

__mod_name__ = 'Formatting'

def get_help(chat):
    return [gs(chat, "formt_help_bse".format(escape_markdown(dispatcher.bot.username))),
    [
        InlineKeyboardButton(text="Markdown", callback_data="fmt_help_md"),
        InlineKeyboardButton(text="Filling", callback_data="fmt_help_filling")
    ]
]