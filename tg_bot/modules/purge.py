import time
from asyncio import sleep
from telethon.events import NewMessage
from telethon.tl.types import ChannelParticipantsAdmins
from .helper_funcs.decorators import register
from .sql.clear_cmd_sql import get_clearcmd
from tg_bot import BOT_ID, telethn
from .helper_funcs.telethn.chatstatus import (
    can_delete_messages, user_can_purge, user_is_admin)
from telethon.errors.rpcerrorlist import MessageDeleteForbiddenError


@register(pattern='(?:(s)?purge|p)', groups_only=True, no_args=True)
async def purge_messages(event: NewMessage.Event):
    start = time.perf_counter()
    if event.from_id is None:
        return

    if not await user_is_admin(
            user_id=event.sender_id, message=event) and event.from_id not in [
                1087968824
            ]:
        await event.reply("Only Admins are allowed to use this command")
        return

    if not await user_can_purge(user_id=event.sender_id, message=event):
        await event.reply("You don't have the permission to delete messages")
        return

    if not await can_delete_messages(message=event):
        if event.chat.admin_rights is None:
            return await event.reply("I'm not an admin, do you mind promoting me first?")
        elif not event.chat.admin_rights.delete_messages:
            return await event.reply("I don't have the permission to delete messages!")

    reply_msg = await event.get_reply_message()
    if not reply_msg:
        await event.reply(
            "Reply to a message to select where to start purging from.")
        return
    messages = []
    message_id = reply_msg.id
    delete_to = event.message.id

    messages.append(event.reply_to_msg_id)
    for msg_id in range(message_id, delete_to + 1):
        messages.append(msg_id)
        if len(messages) == 100:
            await event.client.delete_messages(event.chat_id, messages)
            messages = []

    try:
        await event.client.delete_messages(event.chat_id, messages)
    except:
        pass
    if not event.pattern_match.group(1):
        time_ = time.perf_counter() - start
        text = f"Purged Successfully in {time_:0.2f} Second(s)"
        prmsg = await event.respond(text, parse_mode='markdown')

        cleartime = get_clearcmd(event.chat_id, "purge")

        if cleartime:
            await sleep(cleartime.time)
            await prmsg.delete()


@register(pattern='(del|d)', groups_only=True, no_args=True)
async def delete_messages(event):

    # async for user in telethn.iter_participants(
    #         event.chat_id, filter=ChannelParticipantsAdmins):
    #     print(user)


    if event.from_id is None:
        return

    if not await user_is_admin(
            user_id=event.sender_id, message=event) and event.from_id not in [
                1087968824
            ]:
        await event.reply("Only Admins are allowed to use this command")
        return

    if not await user_can_purge(user_id=event.sender_id, message=event):
        await event.reply("You don't have the permission to delete messages")
        return

    message = await event.get_reply_message()
    # elif event.chat.admin_rights:
    #     status = event.chat.admin_rights.delete_messages
    #     return status
                # if user_id == user.id:# and user_id.ChatAdminRights(delete_messages=True):
    if not message:
        await event.reply("Whadya want to delete?")
        return
    # print(message.sender.id)
    # print(BOT_ID)
    # # print(event.sender_id.ChatAdminRights)
    # print(event.chat.admin_rights)
    # print(event.stringify())
    if not await can_delete_messages(message=event) and not int(message.sender.id) == int(BOT_ID):
        if event.chat.admin_rights is None:
            await event.reply("I'm not an admin, do you mind promoting me first?")
        elif not event.chat.admin_rights.delete_messages:
            await event.reply("I don't have the permission to delete messages!")
        return

    chat = await event.get_input_chat()
    await event.client.delete_messages(chat, message)
    try:
        await event.client.delete_messages(chat, event.message)
    except MessageDeleteForbiddenError:
        print("error in deleting message {} in {}".format(event.message.id, event.chat.id))
        pass


from .language import gs

def get_help(chat):
    return gs(chat, "purge_help")




# PURGE_HANDLER = purge_messages, events.NewMessage(pattern="^[!/>]purge$")
# DEL_HANDLER = delete_messages, events.NewMessage(pattern="^[!/>]del$")

# telethn.add_event_handler(*PURGE_HANDLER)
# telethn.add_event_handler(*DEL_HANDLER)

__mod_name__ = "Purges"
__command_list__ = ["del", "purge"]
# __handlers__ = [PURGE_HANDLER, DEL_HANDLER]