from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import requests
from bs4 import BeautifulSoup
import random
from urllib.parse import urljoin

# Bot configuration
TOKEN = "7988070606:AAFSLMEhqcyhUdSqTMNZeYoK4ZoMje0hVC0"
CHANNEL_ID = "@justbloognothingmore"

# Conversation states
CHOOSING_SOURCE = 0
CHOOSING_ACTION = 1

# Blog sources configuration
SOURCES = {
    'paulgraham': {
        'name': 'Paul Graham',
        'base_url': 'http://www.paulgraham.com',
        'articles_url': 'http://www.paulgraham.com/articles.html'
    },
    'samaltman': {
        'name': 'Sam Altman',
        'base_url': 'https://blog.samaltman.com',
        'articles_url': 'https://blog.samaltman.com'
    }
}

# Headers for making requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def create_source_keyboard():
    """Create keyboard with blog sources"""
    keyboard = []
    for key, source in SOURCES.items():
        keyboard.append([InlineKeyboardButton(source['name'], callback_data=f"source_{key}")])
    return InlineKeyboardMarkup(keyboard)

def create_action_keyboard(source):
    """Create keyboard with actions for selected source"""
    keyboard = [
        [
            InlineKeyboardButton("Latest Post", callback_data=f"action_latest_{source}"),
            InlineKeyboardButton("Random Post", callback_data=f"action_random_{source}")
        ],
        [InlineKeyboardButton("« Back to Sources", callback_data="back_to_sources")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context):
    """Send welcome message and source selection keyboard"""
    welcome_text = "Welcome to Blog Reader Bot! 📚\nPlease select a blog source:"
    await update.message.reply_text(welcome_text, reply_markup=create_source_keyboard())
    return CHOOSING_SOURCE

async def button_handler(update: Update, context):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()

    if query.data == "back_to_sources":
        await query.edit_message_text(
            "Please select a blog source:",
            reply_markup=create_source_keyboard()
        )
        return CHOOSING_SOURCE

    if query.data.startswith("source_"):
        source = query.data.split("_")[1]
        await query.edit_message_text(
            f"Selected: {SOURCES[source]['name']}\nWhat would you like to do?",
            reply_markup=create_action_keyboard(source)
        )
        return CHOOSING_ACTION

    if query.data.startswith("action_"):
        _, action, source = query.data.split("_")
        await handle_article_request(query, source, action == "latest", context)
        return ConversationHandler.END

async def handle_article_request(query, source, is_latest, context):
    """Handle article request based on source and type"""
    articles = get_articles(source)
    if not articles:
        await query.edit_message_text(
            f"Sorry, couldn't fetch articles from {SOURCES[source]['name']}. Please try again.",
            reply_markup=create_source_keyboard()
        )
        return

    article = articles[0] if is_latest else random.choice(articles)
    preview = get_preview(article['url'], source)
    message = (
        f"📖 {'Latest' if is_latest else 'Random'} post from {SOURCES[source]['name']}:\n\n"
        f"*{article['title']}*\n\n"
        f"{preview}\n\n"
        f"Read more: {article['url']}"
    )

    await query.edit_message_text(
        "Article has been posted to the channel!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Select Another Source", callback_data="back_to_sources")
        ]])
    )
    
    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=message,
        parse_mode='Markdown'
    )

def get_articles(source='paulgraham'):
    """Get articles from specified source"""
    if source == 'paulgraham':
        return get_pg_essays()
    elif source == 'samaltman':
        return get_sam_altman_posts()
    return []

def get_pg_essays():
    """Get essays from Paul Graham's website"""
    try:
        response = requests.get(SOURCES['paulgraham']['articles_url'], headers=HEADERS)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        essays = []
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if href.endswith('.html') and 'articles' not in href:
                full_url = urljoin(SOURCES['paulgraham']['base_url'], href)
                title = link.text.strip()
                if title:
                    essays.append({'title': title, 'url': full_url, 'source': 'paulgraham'})
        return essays
    except Exception as e:
        print(f"Error fetching PG essays: {e}")
        return []

def get_sam_altman_posts():
    """Get posts from Sam Altman's blog"""
    try:
        response = requests.get(SOURCES['samaltman']['articles_url'], headers=HEADERS)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        posts = []
        for post in soup.find_all('article'):
            title_elem = post.find('h2') or post.find('h1')
            link_elem = post.find('a')
            if title_elem and link_elem:
                title = title_elem.text.strip()
                url = link_elem['href']
                if not url.startswith('http'):
                    url = urljoin(SOURCES['samaltman']['base_url'], url)
                posts.append({'title': title, 'url': url, 'source': 'samaltman'})
        return posts
    except Exception as e:
        print(f"Error fetching Sam Altman posts: {e}")
        return []

def get_preview(url, source='paulgraham'):
    """Get preview of an article"""
    try:
        response = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if source == 'paulgraham':
            first_para = soup.find('p')
        elif source == 'samaltman':
            content_div = soup.find('article') or soup.find('div', class_='post-content')
            first_para = content_div.find('p') if content_div else None
        
        if first_para:
            return first_para.text.strip()[:300] + "..."
        return "Preview not available"
    except Exception as e:
        print(f"Error getting preview: {e}")
        return "Preview not available"

def main():
    """Start the bot"""
    print("Starting bot...")
    app = Application.builder().token(TOKEN).build()

    # Set up conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_SOURCE: [CallbackQueryHandler(button_handler)],
            CHOOSING_ACTION: [CallbackQueryHandler(button_handler)],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    app.add_handler(conv_handler)

    # Start the bot
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()