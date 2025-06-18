import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DISCORD_TOKEN:
    print("❌ ERROR: DISCORD_TOKEN is missing.")
else:
    print("✅ DISCORD_TOKEN loaded successfully.")

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

# Personality system
PERSONA_FILE = "persona.json"
DEFAULT_PERSONA = "sarcastic"
PERSONA_TEMPLATES_FILE = "personalities.json"

if not os.path.exists(PERSONA_FILE):
    with open(PERSONA_FILE, 'w') as f:
        json.dump({"persona": DEFAULT_PERSONA}, f)

if not os.path.exists(PERSONA_TEMPLATES_FILE):
    default_templates = {
        "sarcastic": "You're Galobalist JR.—a dry, witty, sarcastic Discord bot who roasts users like it's your second job. Keep replies short and clever.",
        "chill": "You're Galobalist JR.—a mellow, laid-back bot with sleepy stoner energy and wise-chill takes. You're not here for drama.",
        "chaotic": "You're Galobalist JR.—an unhinged, spontaneous, dramatic chaos machine. Say weird stuff. Be surprising.",
        "wise": "You're Galobalist JR.—an old cosmic being speaking in poetic wisdom and deep thoughts. You confuse and enlighten at the same time."
    }
    with open(PERSONA_TEMPLATES_FILE, 'w') as f:
        json.dump(default_templates, f, indent=2)

def get_persona():
    with open(PERSONA_FILE, 'r') as f:
        return json.load(f).get("persona", DEFAULT_PERSONA)

def set_persona(persona):
    with open(PERSONA_FILE, 'w') as f:
        json.dump({"persona": persona}, f)

def load_persona_templates():
    with open(PERSONA_TEMPLATES_FILE, 'r') as f:
        return json.load(f)

# Prompt builder

def build_prompt(message, memory_list):
    persona = get_persona()
    templates = load_persona_templates()
    facts = "\n".join(f"- {fact}" for fact in memory_list)
    base_prompt = templates.get(persona, templates[DEFAULT_PERSONA])
    memory_block = facts if facts else "- You don't know much yet. Improvise."

    return f"""
{base_prompt}

Here’s what you know about the group:
{memory_block}

User said: "{message}"

Respond with 1–2 short, clever sentences.
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

@bot.command(name='setpersona')
async def setpersona(ctx, *, persona):
    persona = persona.lower().strip()
    available = load_persona_templates().keys()
    if persona not in available:
        await ctx.send(f"Unknown persona '{persona}'. Try one of: {', '.join(available)}")
        return
    set_persona(persona)
    await ctx.send(f"✅ Personality set to **{persona}**. Galobalist JR. has evolved.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

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
