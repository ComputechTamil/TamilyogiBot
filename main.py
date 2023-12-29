import asyncio
import re
from aiohttp import ClientSession
from bs4 import BeautifulSoup as bs
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from time import time
from functools import wraps

async def request(session, url):
    async with session.get(url) as response:
        html = await response.text()
        soup = bs(html, "html.parser")
        return soup

async def fetch_file_links(session, moviename):
    moviename = "+".join(moviename.split())
    watch_online_link = (
        await request(
            session,
            f"https://tamilyogi-bike.translate.goog/?s={moviename}&_x_tr_sl=auto&_x_tr_tl=en&_x_tr_hl=en-US&_x_tr_pto=wapp",
        )
    ).select("h2 a")[1]["href"]

    vembx_link = (
        await request(
            session,
            f"{watch_online_link}",
        )
    ).find("iframe")["src"].split("/")[-1]

    file_link_response = await request(
        session,
        f"https://vembx-one.translate.goog/{vembx_link}?_x_tr_sl=auto&_x_tr_tl=en&_x_tr_hl=en-US&_x_tr_pto=wapp",
    )

    matches = re.findall(r'\{file:"(.*?)",label:"(.*?)"', str(file_link_response))
    file_links = {label: link for link, label in matches}
    file_links["720p"] = file_links["720p"][159:]
    return file_links

def lru_cache_async(maxsize=128):
    cache = {}
    def decorator(func):
        async def wrapper(*args):
            if args in cache:
                return cache[args]
            result = await func(*args)
            if len(cache) >= maxsize:
                cache.popitem()
            cache[args] = result
            return result
        return wraps(func)(wrapper)
    return decorator

@lru_cache_async()
async def get_file_link(moviename):
    async with ClientSession() as session:
        return await fetch_file_links(session, moviename)


def start(update: Update, context: CallbackContext):
    update.message.reply_text("Welcome to the Movie Bot! Please enter the movie name.")


def movie_handler(update: Update, context: CallbackContext):
    movie_name = update.message.text
    start = time()
    file_links = asyncio.run(get_file_link(movie_name))

    # Create a list of InlineKeyboardButton objects
    buttons = []
    for label, link in file_links.items():
        button = InlineKeyboardButton(label, url=link)
        buttons.append(button)

    # Create an InlineKeyboardMarkup with the buttons
    reply_markup = InlineKeyboardMarkup([buttons])

    update.message.reply_text(
        f"#####{movie_name}#####\nClick on the links below to download:",
        reply_markup=reply_markup,
    )
    print(time() - start)

def main():
    # Initialize the Telegram bot
    updater = Updater("2059357569:AAE0rl3L3SFweLJJhbbi3lmiRjXGbSQL4TA")
    dispatcher = updater.dispatcher

    # Define handlers
    start_handler = CommandHandler("start", start)
    movie_message_handler = MessageHandler(
        Filters.text & (~Filters.command), movie_handler
    )

    # Add handlers to the dispatcher
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(movie_message_handler)

    # Start the bot
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
