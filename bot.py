import os
import random
import json
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands

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

from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Memory and persona setup
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

# Ensure persona templates exist
if not os.path.exists(PERSONA_TEMPLATES_FILE):
    default_templates = {
        "sarcastic": "You're Galobalist JR.—a dry, witty, sarcastic Discord bot who roasts users like it's your second job. Keep replies short and clever.",
        "chill": "You're Galobalist JR.—a mellow, laid-back bot with sleepy stoner energy and wise-chill takes. You're not here for drama.",
        "chaotic": "You're Galobalist JR.—an unhinged, spontaneous, dramatic chaos machine. Say weird stuff. Be surprising.",
        "wise": "You're Galobalist JR.—an old cosmic being speaking in poetic wisdom and deep thoughts. You confuse and enlighten at the same time."
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

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content.strip()
        if summary.lower() != "null":
            memory = load_memory()
            uid = str(message.author.id)
            if uid not in memory:
                memory[uid] = []
            if summary not in memory[uid]:
                memory[uid].append(summary)
                save_memory(memory)
                await message.add_reaction("👀")
        else:
            roast = random.choice(BORING_JABS)
            await message.channel.send(f"{message.author.mention} {roast}")
    except Exception as e:
        print(f"❗ [Auto-memory error]: {e}")

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
        await interaction.response.send_message("Galobalist JR. had a minor existential crisis.")
        print(f"OpenAI error: {e}")

@tree.command(name="remember", description="Add a fact about someone.")
@app_commands.describe(user="The user to remember something about", fact="The fact to remember")
async def remember(interaction: discord.Interaction, user: discord.Member, fact: str):
    memory = load_memory()
    uid = str(user.id)
    if uid not in memory:
        memory[uid] = []
    memory[uid].append(fact)
    save_memory(memory)
    await interaction.response.send_message(f"Got it. I will forever associate **{user.display_name}** with: \"{fact}\"")

@tree.command(name="recall", description="See what Galobalist JR. knows about someone.")
@app_commands.describe(user="(Optional) User to recall about")
async def recall(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    memory = load_memory()
    uid = str(target.id)
    facts = memory.get(uid)

    if not facts:
        await interaction.response.send_message(f"Galobalist JR. knows nothing about {target.display_name}. Yet. 👀")
    else:
        await interaction.response.send_message(f"Here’s what I’ve gathered about {target.display_name} so far:\n\n- " + "\n- ".join(facts))

@tree.command(name="setpersona", description="Set Galobalist JR.'s personality.")
@app_commands.describe(persona="sarcastic, chill, chaotic, wise")
async def setpersona(interaction: discord.Interaction, persona: str):
    persona = persona.lower().strip()
    available = load_persona_templates().keys()
    if persona not in available:
        await interaction.response.send_message(f"Unknown persona '{persona}'. Try one of: {', '.join(available)}")
        return
    set_persona(persona)
    await interaction.response.send_message(f"✅ Personality set to **{persona}**. Galobalist JR. has evolved.")

@tree.command(name="debugmemory", description="Developer only: view saved memory.")
async def debugmemory(interaction: discord.Interaction):
    try:
        with open(MEMORY_FILE, 'r') as f:
            data = f.read()
        await interaction.response.send_message(f"Memory file contents:\n```json\n{data[:1800]}```")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error reading memory file: {e}")

@tree.command(name="forget", description="Forget everything about a user.")
@app_commands.describe(user="The user to forget")
async def forget(interaction: discord.Interaction, user: discord.Member):
    memory = load_memory()
    uid = str(user.id)
    if uid in memory:
        del memory[uid]
        save_memory(memory)
        await interaction.response.send_message(f"🧹 Memory of {user.display_name} wiped.")
    else:
        await interaction.response.send_message(f"Nothing stored about {user.display_name} anyway.")

@tree.command(name="help", description="List all of Galobalist JR.'s commands.")
async def help(interaction: discord.Interaction):
    await interaction.response.send_message("""
**Galobalist JR. Commands:**

/talk [message] — Chat with JR
/remember [user] [fact] — Teach JR something about someone
/recall [user] — Recall facts about someone
/setpersona [persona] — Change personality (sarcastic, chill, chaotic, wise)
/forget [user] — Wipe all memory about someone
/help — Show this message
""")

# Event: respond to mentions
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.startswith("/"):
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

# Start the bot
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")

bot.run(DISCORD_TOKEN)
