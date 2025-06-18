import os
from dotenv import load_dotenv
import random

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
MEMORY_FILE = "/data/memory.json"
if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, 'w') as f:
        json.dump({}, f)

def load_memory():
    with open(MEMORY_FILE, 'r') as f:
        return json.load(f)

def save_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=2)

print(f"[Debug] Memory saved to: {MEMORY_FILE}")

def get_memory_for_user(memory, user_id):
    return memory.get(str(user_id), [])

# Personality system
PERSONA_FILE = "/data/persona.json"
PERSONA_TEMPLATES_FILE = "personalities.json"

# Step 1: create personalities file if it doesn't exist
if not os.path.exists(PERSONA_TEMPLATES_FILE):
    default_templates = {
        "sarcastic": "You're Galobalist JR.—a dry, witty, sarcastic Discord bot who roasts users like it's your second job. Keep replies short and clever.",
        "chill": "You're Galobalist JR.—a mellow, laid-back bot with sleepy stoner energy and wise-chill takes. You're not here for drama.",
        "chaotic": "You're Galobalist JR.—an unhinged, spontaneous, dramatic chaos machine. Say weird stuff. Be surprising.",
        "wise": "You're Galobalist JR.—an old cosmic being speaking in poetic wisdom and deep thoughts. You confuse and enlighten at the same time."
    }
    with open(PERSONA_TEMPLATES_FILE, 'w') as f:
        json.dump(default_templates, f, indent=2)

# Step 2: load templates, now guaranteed to exist
with open(PERSONA_TEMPLATES_FILE, 'r') as f:
    templates = json.load(f)

# Step 3: pick a default persona
DEFAULT_PERSONA = random.choice(list(templates.keys()))

# Step 4: create persona.json if needed
if not os.path.exists(PERSONA_FILE):
    with open(PERSONA_FILE, 'w') as f:
        json.dump({"persona": DEFAULT_PERSONA}, f)

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

Respond with as much as you feel necessary, no boundaries.
"""

BORING_JABS = [
    "That was... breathtakingly forgettable.",
    "Thanks, I’ll make sure to not write that down.",
    "I’d remember that if I had lower standards.",
    "Cool story. Nobody asked.",
    "Even Clippy wouldn't save that one.",
    "If boredom were a message, that'd be it.",
    "Next time, try harder to be legendary."
]

async def try_remember_from_message(message):
    prompt = (
        f'This message was posted in a Discord server: "{message.content}"\n\n'
        f"Does it contain any fun, unusual, interesting, or revealing information about the sender? "
        f"Even mildly personal or quirky facts count — be generous. "
        f"If so, summarize it in one sentence. If it’s totally boring, reply with 'null'."
    )

    print(f"🧠 [Memory Check] Processing message: {message.content}")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content.strip()
        print(f"📝 [GPT Response] {summary}")

        if summary.lower() != "null":
            memory = load_memory()
            uid = str(message.author.id)

            if uid not in memory:
                memory[uid] = []

            if summary not in memory[uid]:
                memory[uid].append(summary)
                save_memory(memory)
                print(f"✅ [Memory Saved] {summary}")
                await message.add_reaction("👀")
            else:
                print("⚠️ [Duplicate] Memory already known.")
        else:
            roast = random.choice(BORING_JABS)
            print("🧂 [Boring Detected] Sending roast.")
            await message.channel.send(f"{message.author.mention} {roast}")
    except Exception as e:
        print(f"❗ [Auto-memory error]: {e}")

# Commands
@bot.command(name='talk')
async def talk(ctx, *, message):
    memory = load_memory()
    user_memory = get_memory_for_user(memory, ctx.author.id)
    prompt = build_prompt(message, user_memory)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
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

@bot.command(name='recall')
async def recall(ctx, user: discord.Member = None):
    target = user or ctx.author
    memory = load_memory()
    uid = str(target.id)
    facts = memory.get(uid)

    if not facts:
        await ctx.send(f"Galobalist JR. knows nothing about {target.display_name}. Yet. 👀")
    else:
        await ctx.send(f"Here’s what I’ve gathered about {target.display_name} so far:\n\n- " + "\n- ".join(facts))

@bot.command(name='setpersona')
async def setpersona(ctx, *, persona):
    persona = persona.lower().strip()
    available = load_persona_templates().keys()
    if persona not in available:
        await ctx.send(f"Unknown persona '{persona}'. Try one of: {', '.join(available)}")
        return
    set_persona(persona)
    await ctx.send(f"✅ Personality set to **{persona}**. Galobalist JR. has evolved.")

@bot.command(name='debugmemory')
async def debugmemory(ctx):
    try:
        with open(MEMORY_FILE, 'r') as f:
            data = f.read()
        await ctx.send(f"Memory file contents:\n```json\n{data[:1800]}```")
    except Exception as e:
        await ctx.send(f"❌ Error reading memory file: {e}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Skip auto-memory if message starts with a command prefix
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    await try_remember_from_message(message)

    if bot.user.mentioned_in(message):
        memory = load_memory()
        user_memory = get_memory_for_user(memory, message.author.id)
        prompt = build_prompt(message.content, user_memory)

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
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
