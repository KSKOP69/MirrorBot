from time import time
from asyncio import sleep as asleep

from pyrogram import filters, Client
from pyrogram.types import CallbackQuery, Message

from bot import CATEGORY_NAMES, btn_listener, bot, download_dict, download_dict_lock
from bot.helper.ext_utils.bot_utils import MirrorStatus, get_category_buttons, getDownloadByGid, getUserTDs
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage


@bot.on_message(filters.command(BotCommands.SelectCategory) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def category_change(c: Client, message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) == 1:
        gid = args[0]
        dl = getDownloadByGid(gid)
        if not dl:
            await sendMessage(f"GID <code>{gid}</code> Not Found!", c, message)
            return
    elif message.reply_to_message:
        mirror_msg = message.reply_to_message
        async with download_dict_lock:
            if mirror_msg.id in download_dict:
                dl = download_dict[mirror_msg.id]
            else:
                dl = None
        if not dl:
            await sendMessage("This is not an active task make sure you reply to an active task!", c, message)
            return
    elif len(args) == 0:
        msg = f'''Reply to an active /{BotCommands.SelectCategory} which was used to start the download or add gid along with {BotCommands.SelectCategory}
        This command mainly for change category incase you decided to change category from already added donwload.
        But you can always use /{BotCommands.MirrorCommand[0]} with to select category before download start.
        '''
        await sendMessage(msg, c, message)
        return
    if not CustomFilters.owner_query(user_id) and dl.message.from_user.id != user_id:
        await sendMessage("This task is not for you!", c, message)
        return
    if dl.status() not in [MirrorStatus.STATUS_DOWNLOADING, MirrorStatus.STATUS_PAUSED, MirrorStatus.STATUS_WAITING]:
        sendMessage(
            f'Task should be on {MirrorStatus.STATUS_DOWNLOADING} or {MirrorStatus.STATUS_PAUSED} or {MirrorStatus.STATUS_WAITING}', c, message)
        return
    listener = dl.listener() if dl and hasattr(dl, 'listener') else None
    if listener and (len(CATEGORY_NAMES) > 1 or len(getUserTDs(user_id)[0]) > 1) and not listener.isLeech:
        msg_id = message.id
        timeout = 60
        btn_listener[msg_id] = [dl.gid(), timeout, time(), listener,
                                listener.c_index, listener.u_index]
        text, btns = get_category_buttons(
            'change', timeout, msg_id, listener.c_index, listener.u_index, listener.user_id)
        engine = await sendMessage(text, c, message, btns)
        await _auto_select(engine, msg_id, timeout)
    else:
        await sendMessage("Cannot change the category for this task!", c, message)


async def _auto_select(msg, msg_id, timeout):
    await asleep(timeout)
    try:
        info = btn_listener[msg_id]
        del btn_listener[msg_id]
        listener = info[3]
        if listener.u_index is None:
            medium = f"Drive {CATEGORY_NAMES[listener.c_index]}"
        else:
            medium = f"Drive {getUserTDs(listener.user_id)[0][listener.u_index]}"
        if listener.isLeech:
            medium = 'Leech'
        if listener.isZip:
            medium += ' As Zip'
        elif listener.extract:
            medium += ' As Unzip'
        listener.mode = medium
        await editMessage(f"Time exceeded! Task has be set.\n\n<b>Upload:</b> {medium}", msg)
    except:
        pass

@bot.on_callback_query(filters.regex(r"^change"))
async def confirm_category(c: Client, query: CallbackQuery):
    user_id = query.from_user.id
    message = query.message
    data = query.data
    data = data.split()
    msg_id = int(data[2])
    try:
        categoryInfo = btn_listener[msg_id]
    except KeyError:
        return await editMessage(f"<b>Old Task!</b>", message)
    listener = categoryInfo[3]
    if user_id != listener.message.from_user.id and not CustomFilters.owner_query(user_id):
        await query.answer("This task is not for you!", show_alert=True)
    elif data[1] == 'scat':
        c_index = int(data[3])
        u_index = None
        if listener.c_index == c_index:
            return await query.answer(f"{CATEGORY_NAMES[c_index]} is selected already!", show_alert=True)
        await query.answer()
        listener.c_index = c_index
        listener.u_index = u_index
    elif data[1] == 'ucat':
        u_index = int(data[3])
        c_index = 0
        if listener.u_index == u_index:
            return await query.answer(f"{getUserTDs(listener.user_id)[0][u_index]} is selected already!", show_alert=True)
        await query.answer()
        listener.c_index = c_index
        listener.u_index = u_index
    elif data[1] == 'cancel':
        await query.answer()
        listener.c_index = categoryInfo[4]
        listener.u_index = categoryInfo[5]
        if listener.u_index is None:
            medium = f"Drive {CATEGORY_NAMES[listener.c_index]}"
        else:
            medium = f"Drive {getUserTDs(listener.user_id)[0][listener.u_index]}"
        if listener.isLeech:
            medium = 'Telegram'
        if listener.isZip:
            medium += ' As Zip'
        elif listener.extract:
            medium += ' As Unzip'
        listener.mode = medium
        del btn_listener[msg_id]
        return await editMessage(f"<b>Task has been cancelled!</b>", message)
    elif data[1] == 'start':
        await query.answer()
        del btn_listener[msg_id]
        if listener.u_index is None:
            medium = f"Drive {CATEGORY_NAMES[listener.c_index]}"
        else:
            medium = f"Drive {getUserTDs(listener.user_id)[0][listener.u_index]}"
        if listener.isLeech:
            medium = 'Telegram'
        if listener.isZip:
            medium += ' As Zip'
        elif listener.extract:
            medium += ' As Extract'
        listener.mode = medium
        return await editMessage(f"Task has been updated!\n\n<b>Upload:</b> {medium}", message)
    timeout = categoryInfo[1] - (time() - categoryInfo[2])
    text, btns = get_category_buttons(
        'change', timeout, msg_id, c_index, u_index, listener.user_id)
    await editMessage(text, message, btns)

