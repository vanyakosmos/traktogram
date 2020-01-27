from telegram import Message, Update
from telegram.ext import CallbackContext, Filters

from teletrakt.updater import commands_help, command_handler, message_handler


@command_handler('start', help="start")
def start_handler(update: Update, context: CallbackContext):
    m: Message = update.message
    m.reply_text("yes")


@message_handler(Filters.text)
def echo_handler(update: Update, context: CallbackContext):
    m: Message = update.message
    m.reply_text(m.text)


@command_handler('help', help="show this message")
def help_handler(update: Update, context: CallbackContext):
    lines = ["Available commands:"]
    for cmd, help_text in commands_help.items():
        lines.append(f"/{cmd} - {help_text}")
    m: Message = update.message
    m.reply_text("\n".join(lines))
