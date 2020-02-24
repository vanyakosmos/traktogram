import asyncio
import logging

from aiogram.types import CallbackQuery

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


@router.callback_query_handler(single_nt_cd.filter())
async def calendar_notification_watch_handler(query: CallbackQuery, callback_data: dict):
    episode_id = callback_data['id']
    prev_watched = callback_data.get('watched') == '1'

    store = Storage.get_current()
    sess, user_data = await asyncio.gather(
        trakt_session(query.from_user.id),
        store.get_data(user=query.from_user.id)
    )
    on_watch = user_data.get('on_watch', 'hide')
    watched = await sess.watched(episode_id)

    # delete message if it is marked as watched
    if on_watch == 'delete':
        watched = await toggle_watched_status(sess, episode_id, watched)
        if watched:
            logger.debug("episode is watched and on_watch=delete")
            await asyncio.gather(
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
