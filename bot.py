import os
from dotenv import load_dotenv

load_dotenv()

# Fallback: hard-inject OPENAI_API_KEY from OPENAI_KEY if needed
if not os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_KEY"):
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_KEY")

DISCORD_TOKEN = "MTM4NDY3MzU2MzY5MjM2ODAwNA.Gt_yOc.0tV8OC-KXhqScCY0b5C31C3xW-3uTwAoT52cUM"
if not DISCORD_TOKEN:
    print("❌ ERROR: DISCORD_TOKEN is missing.")
else:
    print(f"✅ DISCORD_TOKEN loaded successfully.")
OPENAI_API_KEY = "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"

if not OPENAI_API_KEY:
    print("❌ ERROR: OPENAI_API_KEY is missing.")
else:
    print("✅ OPENAI_API_KEY loaded successfully.")

from openai import OpenAI
import discord
from discord.ext import commands
import json
client = OpenAI(api_key=OPENAI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Load memory
MEMORY_FILE = "memory.json"
if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, 'w') as f:
        json.dump({}, f)

def load_memory():
    with open(MEMORY_FILE, 'r') as f:
        return json.load(f)

def save_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=2)

def get_memory_for_user(memory, user_id):
    return memory.get(str(user_id), [])

# Prompt builder
def build_prompt(message, memory_list):
    facts = "\n".join(f"- {fact}" for fact in memory_list)
    return f"""
You are Galobalist JR., a chill, sarcastic Discord bot that roasts users gently and replies like you're one of the Global Galobalists. Here's what you know about this group:
{facts if facts else '- You don\'t know much yet. Make up for it with spicy sarcasm.'}

User said: "{message}"

Reply with a short, clever, slightly roasty or witty response. Don't explain yourself.
"""

# Commands
@bot.command(name='talk')
async def talk(ctx, *, message):
    memory = load_memory()
    user_memory = get_memory_for_user(memory, ctx.author.id)
    prompt = build_prompt(message, user_memory)

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content.strip()
        await ctx.send(reply)
    except Exception as e:
        await ctx.send("Galobalist JR. had a minor existential crisis.")
        print(f"OpenAI error: {e}")

@bot.command(name='remember')
async def remember(ctx, user: discord.Member, *, fact):
    memory = load_memory()
    uid = str(user.id)
    if uid not in memory:
        memory[uid] = []
    memory[uid].append(fact)
    save_memory(memory)
    await ctx.send(f"Got it. I will forever associate @**{user.display_name}** with: \"{fact}\"")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Respond when bot is mentioned
    if bot.user.mentioned_in(message):
        memory = load_memory()
        user_memory = get_memory_for_user(memory, message.author.id)
        prompt = build_prompt(message.content, user_memory)

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            reply = response.choices[0].message.content.strip()
            await message.channel.send(reply)
        except Exception as e:
            await message.channel.send("Even I can't process what you just said.")
            print(f"Mention error: {e}")

    await bot.process_commands(message)

# Run the bot
bot.run(DISCORD_TOKEN)
