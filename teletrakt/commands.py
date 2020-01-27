from telegram import Message, Update
from telegram.ext import CallbackContext, Filters

from teletrakt.updater import handler, commands_help


@handler('cmd', 'start', help="foo bar")
def start(update: Update, context: CallbackContext):
    m: Message = update.message
    m.reply_text("yes")


@handler('msg', Filters.text, help="foo bar")
def echo(update: Update, context: CallbackContext):
    m: Message = update.message
    m.reply_text(m.text)


@handler('cmd', 'help', help="show this message")
def help(update: Update, context: CallbackContext):
    lines = ["Available commands:"]
    for cmd, help_text in commands_help.items():
        lines.append(f"/{cmd} - {help_text}")
    m: Message = update.message
    m.reply_text("\n".join(lines))
