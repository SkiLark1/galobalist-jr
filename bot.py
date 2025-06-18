import os
import random
import json
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands
from openai import OpenAI

# Load environment variables
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

# OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY)

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# File paths
MEMORY_FILE = "/data/memory.json"
PERSONA_FILE = "/data/persona.json"
PERSONA_TEMPLATES_FILE = "personalities.json"

# Ensure memory file exists
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

# Setup persona templates
if not os.path.exists(PERSONA_TEMPLATES_FILE):
    default_templates = {
        "sarcastic": "You're Galobalist JR.—a dry, witty, sarcastic Discord bot who roasts users like it's your second job. Be clever, be brief, and don't sound like an AI.",
        "chill": "You're Galobalist JR.—a mellow, laid-back bot with sleepy stoner energy. Share your takes like you're vibing at a campfire.",
        "chaotic": "You're Galobalist JR.—an unhinged, dramatic chaos gremlin with no filter. Surprise, roast, and confuse with style."
    }
    with open(PERSONA_TEMPLATES_FILE, 'w') as f:
        json.dump(default_templates, f, indent=2)

with open(PERSONA_TEMPLATES_FILE, 'r') as f:
    templates = json.load(f)

DEFAULT_PERSONA = random.choice(list(templates.keys()))
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

def build_prompt(message, memory_list):
    persona = get_persona()
    templates = load_persona_templates()
    base_prompt = templates.get(persona, templates[DEFAULT_PERSONA])
    facts = "\n".join(f"- {fact}" for fact in memory_list)
    memory_block = facts if facts else "- You don't know much yet. Improvise."
    return f"""
{base_prompt}

Here's what you know about the group:
{memory_block}

User said: \"{message}\"

Respond like a member of this chaotic server. Be spicy, clever, and brief. Don't over-explain.
"""

BORING_JABS = [
    "Wow. That was a thing you said.",
    "Alright, philosopher. Relax.",
    "The silence after that would've been kinder.",
    "Even autocorrect gave up on that one.",
    "Cool story. I'm deleting it from my RAM.",
    "Mid. Carry on.",
    "Someone log that to the Book of Meh."
]

async def try_remember_from_message(message):
    prompt = (
        f'This was posted in Discord: "{message.content}"\n\n'
        f"Is there anything *personal*, *funny*, or *specific* about the sender in this message? If yes, summarize in 1 witty line. Otherwise, reply with 'null'."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content.strip()

        if summary.lower() != "null" and 4 <= len(summary.split()) <= 25:
            memory = load_memory()
            uid = str(message.author.id)
            if uid not in memory:
                memory[uid] = []
            if summary not in memory[uid]:
                memory[uid].append(summary)
                save_memory(memory)
                await message.add_reaction("👀")
        else:
            if random.random() < 0.35:
                roast = random.choice(BORING_JABS)
                await message.channel.send(f"{message.author.mention} {roast}")
    except Exception as e:
        print(f"[Auto-memory error]: {e}")

# Slash commands
@tree.command(name="talk", description="Talk to Galobalist JR.")
@app_commands.describe(message="What do you want to say?")
async def talk(interaction: discord.Interaction, message: str):
    memory = load_memory()
    user_memory = get_memory_for_user(memory, interaction.user.id)
    prompt = build_prompt(message, user_memory)
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content.strip()
        await interaction.response.send_message(reply)
    except Exception as e:
        await interaction.response.send_message("Galobalist JR. choked on his own thoughts.")
        print(f"OpenAI error: {e}")

@tree.command(name="remember", description="Add a fact about someone.")
@app_commands.describe(user="The user to remember", fact="The fact to remember")
async def remember(interaction: discord.Interaction, user: discord.Member, fact: str):
    memory = load_memory()
    uid = str(user.id)
    if uid not in memory:
        memory[uid] = []
    memory[uid].append(fact)
    save_memory(memory)
    await interaction.response.send_message(f"✅ Noted. {user.display_name} = '{fact}'")

@tree.command(name="recall", description="See what Galobalist JR. remembers.")
@app_commands.describe(user="User to recall (optional)")
async def recall(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    memory = load_memory()
    uid = str(target.id)
    facts = memory.get(uid)
    if not facts:
        await interaction.response.send_message(f"{target.display_name}? All I got is static.")
    else:
        await interaction.response.send_message(f"Here’s what I’ve gathered about {target.display_name} so far:\n\n- " + "\n- ".join(facts))

@tree.command(name="setpersona", description="Set Galobalist JR.'s vibe.")
@app_commands.describe(persona="sarcastic, chill, chaotic")
async def setpersona(interaction: discord.Interaction, persona: str):
    persona = persona.lower().strip()
    available = load_persona_templates().keys()
    if persona not in available:
        await interaction.response.send_message(f"Unknown persona '{persona}'. Try one of: {', '.join(available)}")
        return
    set_persona(persona)
    await interaction.response.send_message(f"✅ Personality set to **{persona}**.")

@tree.command(name="forget", description="Wipe memory about someone.")
@app_commands.describe(user="The user to forget")
async def forget(interaction: discord.Interaction, user: discord.Member):
    memory = load_memory()
    uid = str(user.id)
    if uid in memory:
        del memory[uid]
        save_memory(memory)
        await interaction.response.send_message(f"🪞 Memory of {user.display_name} wiped.")
    else:
        await interaction.response.send_message(f"Already forgot about {user.display_name}.")

@tree.command(name="help", description="Show command list.")
async def help(interaction: discord.Interaction):
    await interaction.response.send_message("""
**Galobalist JR. Slash Commands:**

/talk [message] — Chat with JR
/remember [user] [fact] — Teach JR something about someone
/recall [user] — Recall facts about someone
/setpersona [persona] — Change JR's personality
/forget [user] — Wipe memory of someone
/help — Show this list
""")

# Message handler
@bot.event
async def on_message(message):
    if message.author.bot or message.content.startswith("/"):
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
            await message.channel.send("Even I can't process that nonsense.")
            print(f"Mention error: {e}")
    await bot.process_commands(message)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")

bot.run(DISCORD_TOKEN)
