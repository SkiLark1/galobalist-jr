import discord
from discord.ext import commands
import random
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
# Load the API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Set up intents

intents = discord.Intents.default()
intents.message_content = True

# Create bot instance
bot = commands.Bot(command_prefix='!', intents=intents)

# Define ai debate creator
def get_ai_debate_topic():
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": "Give me a short, inticing, and debatable hot take or controversial opinion that would spark a heated discussion among friends on Discord."
            }]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return random.choice(topics)

# Load topics from a file
DEBATE_FILE = 'debates.json'
def load_debate_topics():
    default_topics = [
        "Cereal is a soup.",
        "Pineapple belongs on pizza.",
        "Cats are better than dogs."
    ]

    if not os.path.exists(DEBATE_FILE) or os.stat(DEBATE_FILE).st_size == 0:
        with open(DEBATE_FILE, 'w') as f:
            json.dump(default_topics, f)

    try:
        with open(DEBATE_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        # If the file is corrupted, reset it
        with open(DEBATE_FILE, 'w') as f:
            json.dump(default_topics, f)
        return default_topics
    
topics = load_debate_topics()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command(name='debate')
async def post_debate(ctx):
    topic = get_ai_debate_topic()
    message = await ctx.send(f"**🔥 Daily Debate 🔥**\n{topic}")
    await message.add_reaction("✅")
    await message.add_reaction("❌")

@bot.command(name='suggestdebate')
async def suggest_debate(ctx, *, suggestion):
    topics.append(suggestion)
    with open(DEBATE_FILE, 'w') as f:
        json.dump(topics, f, indent=2)
    await ctx.send(f"Thanks for the suggestion, {ctx.author.mention}!")

# Replace with your bot token
bot.run("DISCORD_TOKEN")