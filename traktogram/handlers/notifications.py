import asyncio
import logging
from datetime import datetime, timedelta

from aiogram.types import CallbackQuery, Message

from traktogram.router import Router
from traktogram.services import (
    CalendarMultiNotification, CalendarMultiNotificationFlow, CalendarNotification,
    TraktClient, trakt_session,
)
from traktogram.storage import Storage


logger = logging.getLogger(__name__)
router = Router()
single_nt_cd = CalendarNotification.cd
multi_nt_cd = CalendarMultiNotification.cd


async def toggle_watched_status(sess: TraktClient, episode_id, watched: bool):
    logger.debug(f"was watched {watched}")
    if watched:
        await sess.remove_from_history(episode_id)
    else:
        await sess.add_to_history(episode_id)
    return not watched


async def postponed_delete(msg: Message, delay=5.):
    await asyncio.sleep(delay)
    await msg.delete()


@router.callback_query_handler(single_nt_cd.filter())
async def calendar_notification_watch_handler(query: CallbackQuery, callback_data: dict):
    user_id = query.from_user.id
    episode_id = callback_data['id']
    prev_watched = callback_data.get('watched') == '1'

    store = Storage.get_current()
    sess, user_pref = await asyncio.gather(
        trakt_session(user_id),
        store.get_pref(user=user_id)
    )
    on_watch = user_pref.get('on_watch', 'hide')
    watched = await sess.watched(episode_id)

    # if message was created more than 48 hours ago then it cannot be deleted
    now = datetime.now()
    delta = now - query.message.date
    if on_watch == 'delete' and delta >= timedelta(hours=48):
        warn = await query.message.reply("quick note: bot cannot delete messages older then 48 hours",
                                         disable_notification=True)
        asyncio.create_task(postponed_delete(warn, delay=5))
        on_watch = 'hide'
    # delete message if it is marked as watched
    if on_watch == 'delete':
        watched = await toggle_watched_status(sess, episode_id, watched)
        if watched:
            logger.debug("episode is watched and on_watch=delete")
            await asyncio.gather(
                store.update_data(user=user_id, data={'deleted_episode': episode_id}),
                query.message.delete(),
                query.answer("added to history"),
            )
            return
    # sync with current watch status
    else:
        if watched is prev_watched:
            watched = await toggle_watched_status(sess, episode_id, watched)
        else:
            msg = 'watched' if watched else 'unwatched'
            logger.debug(f"user already marked this as {msg}")

    se = await sess.search_by_episode_id(episode_id, extended=True)
    logger.debug(se)

    # update keyboard
    hide = on_watch == 'hide'
    markup = await CalendarNotification.markup(se, watched, hide=hide)
    await asyncio.gather(
        query.message.edit_text(query.message.html_text, reply_markup=markup,
                                disable_web_page_preview=hide and watched),
        query.answer("added to history" if watched else "removed from history"),
    )


@router.callback_query_handler(multi_nt_cd.filter(action='prev'))
async def calendar_multi_notification_prev_handler(query: CallbackQuery, callback_data: dict):
    f = CalendarMultiNotificationFlow(query)
    if f.index == 0:
        await query.answer("this is first episode in the queue")
        return
    f.move_index(-1)
    await f.fetch_episode_data()
    await f.update_message()


@router.callback_query_handler(multi_nt_cd.filter(action='next'))
async def calendar_multi_notification_next_handler(query: CallbackQuery, callback_data: dict):
    f = CalendarMultiNotificationFlow(query)
    if f.index == len(f.episodes_ids) - 1:
        await query.answer("this is last episode in the queue")
        return
    f.move_index(1)
    await f.fetch_episode_data()
    await f.update_message()


@router.callback_query_handler(multi_nt_cd.filter(action='watch'))
async def calendar_multi_notification_watch_handler(query: CallbackQuery, callback_data: dict):
    f = CalendarMultiNotificationFlow(query)
    async with f.fetch_episode_data_context() as sess:
        watched_current = await toggle_watched_status(sess, f.episode_id, f.watched)
        # patch helper's watch and se so that the right episode will be displayed
        if watched_current:
            f.move_index(1)
            f.watched = await sess.watched(f.episode_id)
        else:
            f.watched = False
    answer = f"marked as watched" if watched_current else "unwatched"
    await f.update_message(answer)
