import asyncio
import logging

from aiogram.types import CallbackQuery

from traktogram.router import Router
from traktogram.services import (
    CalendarMultiNotification, CalendarMultiNotificationFlow, CalendarNotification,
    TraktClient, trakt_session,
)


logger = logging.getLogger(__name__)
router = Router()
single_nt_cd = CalendarNotification.cd
multi_nt_cd = CalendarMultiNotification.cd


async def toggle_watched_status(sess: TraktClient, episode_id, watched: bool):
    logger.debug(f"watched {watched}")
    if watched:
        await sess.remove_from_history(episode_id)
    else:
        await sess.add_to_history(episode_id)
    return not watched


@router.callback_query_handler(single_nt_cd.filter(action='watch'))
async def calendar_notification_watch_handler(query: CallbackQuery, callback_data: dict):
    episode_id = callback_data['id']

    sess = await trakt_session(query.from_user.id)
    watched = await sess.watched(episode_id)
    watched = await toggle_watched_status(sess, episode_id, watched)
    se = await sess.search_by_episode_id(episode_id, extended=True)
    logger.debug(se)
    # update keyboard
    markup = await CalendarNotification.markup(se, watched)
    await asyncio.gather(
        query.message.edit_text(query.message.html_text, reply_markup=markup,
                                disable_web_page_preview=watched),
        query.answer("marked as watched" if watched else "unwatched"),
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
