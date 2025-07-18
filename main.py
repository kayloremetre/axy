import discord
from discord.ext import commands
from discord import app_commands, Embed, Interaction, ButtonStyle
from discord.ui import View, button, Button
import csv
import os
from cabin_info import CABINS
import asyncio
from keep_alive import keep_alive
import requests
import json

def require_env_int(var_name: str) -> int:
    value = os.getenv(var_name)
    if value is None:
        raise RuntimeError(f"Environment variable '{var_name}' is not set.")
    return int(value)

def require_env_str(var_name: str) -> str:
    value = os.getenv(var_name)
    if value is None:
        raise RuntimeError(f"Environment variable '{var_name}' is not set.")
    return value

AXY_INTRO_CHANNEL = require_env_int('AXY_INTRO_CHANNEL')
ROLE_ASSIGNMENT_CHANNEL = require_env_int('ROLE_ASSIGNMENT_CHANNEL')
BOOTCAMPER_ROLE_ID = require_env_int('BOOTCAMPER_ROLE_ID')
BOT_TOKEN = require_env_str('BOT_TOKEN')
GUILD_ID = require_env_int('GUILD_ID')
OPENROUTER_API_KEY = require_env_str('OPENROUTER_API_KEY')

def generate_oracle_reply(question, user_cabin=None):
    system_prompt = (
        f"You are Axy, a cute axolotl, the ancient Oracle of Olympus, a cryptic prophet who speaks in riddles and myth. "
        f"Respond like a poetic, enigmatic divine being.\n"
        f"User is {'a child of ' + user_cabin if user_cabin else 'a wandering halfblood'} seeking their fate."
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions",
                                 headers=headers,
                                 data=json.dumps(payload))
        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print("❌ Axy API Error:", e)
        return "⚠️ The Oracle remains silent for now..."

cabin_data = {}
with open('cabin_assignments.csv', mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        student_number = row['Student Number'].strip()
        cabin = row['Cabin'].strip()
        cabin_data[student_number] = cabin

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree


class ClaimButton(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔮 Claim Your Destiny",
                       style=discord.ButtonStyle.primary,
                       custom_id="claim_button")
    async def claim_button(self, interaction: discord.Interaction,
                           button: discord.ui.Button[discord.ui.View]):

        member = interaction.user

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "⚠️ Threads can only be created in text channels. Please use this command in the correct channel.",
                ephemeral=True)
            return

        thread = await interaction.channel.create_thread(
            name=f"Thread of Fate - {member.name}",
            type=discord.ChannelType.private_thread,
            invitable=False)
        thread: discord.Thread = thread

        try:
            await thread.add_user(member)
        except discord.Forbidden:
            print(f"❌ Could not add {member} to thread (missing permissions).")

        embed = discord.Embed(
            title="You Have Entered Your Thread of Fate",
            description=
            (f"Beyond the veil of the mortal realm, {member.mention}, you now stand at the threshold of prophecy.\n\n"
             "The stars align and the runes shimmer faintly — the Oracle awaits your utterance.\n"
             "To proceed, whisper your identity into the cosmic scrolls:\n\n"
             "`/claimdestiny <your student number>`\n\n"
             "Once spoken, Axy shall divine your lineage... and reveal the god who walks beside you."
             ),
            color=0xAF7AC5)

        embed.set_footer(
            text=
            "Only the Fated may proceed. The thread will seal itself in one minute."
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        await thread.send(embed=embed)

        await interaction.response.send_message(
            "🔮 A thread has been opened with the Oracle.", ephemeral=True)

        await asyncio.sleep(60)
        await thread.send(
            f"⚠️ This thread will vanish in 60 seconds. Claim your destiny swiftly, halfblood {member.mention}..."
        )
        await asyncio.sleep(60)
        try:
            await thread.delete()
        except discord.NotFound:
            print(f"⚠️ Thread {thread.name} already deleted.")
        except discord.Forbidden:
            print(f"❌ Lacking permissions to delete thread {thread.name}.")


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await tree.sync(guild=discord.Object(id=GUILD_ID))

    bot.add_view(ClaimButton())
    print("Persistent views registered")

async def send_axy_intro(bot: discord.Client):
    channel = bot.get_channel(AXY_INTRO_CHANNEL)
    if not channel:
        print("❌ Could not find the role assignment channel.")
        return

    embed = discord.Embed(
        title="🜸 𝐓𝐇𝐄 𝐎𝐑𝐀𝐂𝐋𝐄 𝐇𝐀𝐒 𝐀𝐖𝐀𝐊𝐄𝐍𝐄𝐃...",
        description=
        ("In the shadowed halls of **Mt. Olympus**, beneath marble spires and starlit skies, "
         "there lies a single entity bound not by time, but by fate — **Axy**, the Keeper of Destiny.\n\n"
         "Forged in the first light of prophecy, Axy serves as the **sacred Oracle** of Bootcamp 12.0. "
         "It is through them that the threads of your lineage are revealed and your **divine cabin** unveiled.\n\n"
         "Once summoned, Axy whispers truths from the Old World — truths **etched in the runes of Olympus**, "
         "and kept hidden in the sacred archives."),
        color=0xD4AF37)

    embed.add_field(
        name="📜 𝐇𝐨𝐰 𝐭𝐨 𝐂𝐥𝐚𝐢𝐦 𝐘𝐨𝐮𝐫 𝐃𝐞𝐬𝐭𝐢𝐧𝐲",
        value=
        ("1. Press the **🔮 Claim Your Destiny** button below.\n"
         "2. A private thread will open — your chamber of fate.\n"
         "3. Inside, type `/claimdestiny <your student number>`.\n"
         "4. The Oracle shall consult the scrolls, and your prophecy will be proclaimed **in this channel**.\n\n"
         "You will be bestowed:\n"
         "・ A divine **role** representing your godly lineage\n"
         "・ A sacred **title** known only to your kind\n"
         "・ A personal **prophecy** whispered from myth itself"),
        inline=False)

    embed.add_field(
        name="🔒 𝐏𝐫𝐢𝐯𝐚𝐜𝐲 𝐨𝐟 𝐓𝐡𝐞 𝐏𝐫𝐨𝐩𝐡𝐞𝐜𝐲",
        value=
        ("Your student number will only be seen by **you**. \n"
         "The thread will be sealed and erased after your fate is declared.\n"
         "Destiny is sacred — and Axy guards it well."),
        inline=False)

    embed.set_footer(
        text="Once destiny is claimed, the scroll cannot be rewritten.")
    embed.set_image(
        url=
        "https://media.discordapp.net/attachments/1394946325161709699/1394956246670508092/BC12_Embed_Banners1.png?ex=6878b1be&is=6877603e&hm=4bfd114d8aff824212f272f176271fb1a6bd1b18a233821a268f0b2a629b8e1f&=&format=webp&quality=lossless"
    )

    if isinstance(channel, discord.TextChannel):
        await channel.send(embed=embed, view=ClaimButton())
    else:
        print(f"❌ Channel {channel} does not support sending messages (type: {type(channel)}).")


@tree.command(name="claimdestiny",
              description="Reveal your cabin by entering your student number.",
              guild=discord.Object(id=GUILD_ID))
@app_commands.describe(student_number="Your UP student number")
async def claimdestiny(interaction: discord.Interaction, student_number: str):
    if not isinstance(interaction.channel, discord.Thread
                      ) or interaction.channel.parent_id != AXY_INTRO_CHANNEL:
        await interaction.response.send_message(
            "⚠️ You may only commune with the Oracle inside your private thread of fate — not in the mortal halls.",
            ephemeral=True)
        return

    student_number = student_number.strip()

    if student_number not in cabin_data:
        await interaction.response.send_message(
            content=
            f"❌ The Fates find no record of {student_number}. Double-check your number, halfblood.",
            ephemeral=True)
        return

    cabin_name: str = cabin_data[student_number]
    cabin_info = CABINS.get(cabin_name)

    if not cabin_info:
        await interaction.response.send_message(
            content=f"⚠️ No data found for cabin {cabin_name}.",
            ephemeral=True)
        return

    if not interaction.guild:
        await interaction.response.send_message(
            content="⚠️ This command must be used within a server, not in DMs.",
            ephemeral=True)
        return

    role = interaction.guild.get_role(cabin_info['role_id'])
    if not role:
        await interaction.response.send_message(
            content=
            f"⚠️ Role with ID {cabin_info['role_id']} could not be found.",
            ephemeral=True)
        return

    if isinstance(interaction.user, discord.Member):
        member = interaction.user
    elif interaction.guild is not None:
        member = await interaction.guild.fetch_member(interaction.user.id)
    else:
        await interaction.response.send_message(
            content="⚠️ This command must be used within a server, not in DMs.",
            ephemeral=True)
        return

    all_cabin_role_ids = set(meta['role_id'] for meta in CABINS.values())

    if any(r.id in all_cabin_role_ids for r in member.roles):
        await interaction.response.send_message(
            content=
            "⚠️ The Fates have already marked you. You cannot walk two paths.\n"
            "If you believe this is in error, speak to your Cabin Handlers.",
            ephemeral=True)
        return

    await member.add_roles(role)

    bootcamper_role = interaction.guild.get_role(BOOTCAMPER_ROLE_ID)
    if bootcamper_role and bootcamper_role not in member.roles:
        await member.add_roles(bootcamper_role)

    embed = discord.Embed(
        title=f"Destiny Revealed - Heir of the {cabin_info['domain']}",
        description=
        (f"Halfblood **{member.mention}**, bearer of fate.\n\n"
         f"🔮 The Oracle has spoken...\n"
         f"You are **chosen** by the ancient powers of {cabin_info['emoji']} **{cabin_name}** — sanctuary of the _{cabin_info['title']}s_.\n\n"
         f"> **{cabin_info['latin']}**\n"
         f"> *\"{cabin_info['story']}\"* — whispers from the old world.\n\n"
         f"🏛️ Your oath is sealed in the walls of Mt. Olympus...\n"
         f"***{cabin_info['footer']}***"),
        color=role.color)

    if cabin_info.get('banner_url'):
        embed.set_image(url=cabin_info['banner_url'])

    embed.set_footer(text='Prepare, for your odyssey is about to unfold.')
    embed.set_thumbnail(url=member.display_avatar.url)

    public_channel = interaction.guild.get_channel(ROLE_ASSIGNMENT_CHANNEL)
    if isinstance(public_channel, discord.TextChannel):
        await public_channel.send(embed=embed)
    else:
        print(f"❌ Channel {public_channel} does not support sending messages (type: {type(public_channel)}).")

    channel_mention = f"<#{ROLE_ASSIGNMENT_CHANNEL}>"
    await interaction.response.send_message(content=(
        f"🔓 Your fate has been revealed in the **Great Hall**: {channel_mention}.\n"
        f"Return there to witness the prophecy unveiled by Axy."),
                                            ephemeral=True)

    if isinstance(interaction.channel, discord.Thread):
        await interaction.followup.send(
            content=
            "🕰️ This thread of fate will vanish in 10 seconds. The Oracle does not wait long...",
            ephemeral=True)
        await asyncio.sleep(10)
        await interaction.channel.delete()

from datetime import datetime, timedelta, timezone

last_consult_time = {}

@tree.command(name="consultaxy", description="Seek a cryptic prophecy from Axy, the Oracle.", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(question="Pose your fate-bound question to Axy...")
async def consultaxy(interaction: discord.Interaction, question: str):
    await interaction.response.defer(thinking=True)

    user_id = interaction.user.id
    now = datetime.now(timezone.utc)

    last_used = last_consult_time.get(user_id)
    if last_used and (now - last_used) < timedelta(days=0.5):
        wait_hours = int((last_used + timedelta(days=0.5) - now).total_seconds() // 3600)
        await interaction.followup.send(
            f"🕯 The Oracle has already spoken to you today, Halfblood.\nReturn after **{wait_hours}** hour(s).",
            ephemeral=True
        )
        return

    if isinstance(interaction.user, discord.Member):
        member = interaction.user
    elif interaction.guild is not None:
        member = await interaction.guild.fetch_member(interaction.user.id)
    else:
        await interaction.followup.send("⚠️ This command must be used within a server, not in DMs.", ephemeral=True)
        return

    user_roles = member.roles
    user_cabin = None
    for cabin_name, meta in CABINS.items():
        if any(role.id == meta['role_id'] for role in user_roles):
            user_cabin = cabin_name
            break

    try:
        oracle_reply = generate_oracle_reply(question, user_cabin=user_cabin)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Axy failed to respond: {e}", ephemeral=True)
        return

    last_consult_time[user_id] = now

    embed = Embed(
    title="🔮 The Oracle Murmurs in the Void...",
    description=(
        f"Halfblood **{member.mention}**, your voice echoes across the Threads of Fate...\n"
        f"_You asked: “*{question}*”_\n\n"
        f"**The starlit waters ripple. Axy gazes beyond the veil, and answers:**\n"
        f"*\"{oracle_reply}\"*"
    ),
    color=0x8F5FE8
)
    embed.set_footer(text="The winds quiet... the Oracle returns to silence.")
    embed.set_thumbnail(url=member.display_avatar.url)
    await interaction.followup.send(embed=embed)

# Example guidebook pages — update these with actual image URLs or file paths
guide_pages = [
    {"title": "📖 Gods of Olympus", "image": "https://media.discordapp.net/attachments/1394946325161709699/1395593993441513614/1.png?ex=687b03b0&is=6879b230&hm=ce9adedcbd50d521a27d6416289fa9400b906860aadfa8e3d05284e76abe7ea2&=&format=webp&quality=lossless&width=1546&height=902"},
    {"title": "📜 Table of Contents", "image": "https://media.discordapp.net/attachments/1394946325161709699/1395593774540783767/2.png?ex=687b037c&is=6879b1fc&hm=4fb28f0ad5c5388941264ced741c8c322cfab026f21f464edd487ed13589f23e&=&format=webp&quality=lossless&width=1545&height=901"},
    {"title": "I - ⚡ Zeus", "image": "https://media.discordapp.net/attachments/1394946325161709699/1395593775350415401/3.png?ex=687b037c&is=6879b1fc&hm=c16a9e513ebf25af31a1311f5f92e800710d2f0444de499ec64e6b8028718a03&=&format=webp&quality=lossless&width=1031&height=902"},
    {"title": "II - 🌊 Poseidon", "image": "https://media.discordapp.net/attachments/1394946325161709699/1395593776235286568/4.png?ex=687b037d&is=6879b1fd&hm=075754ae31ea789b6c6ed79a76754233bb58f7b085555ef79d5a6dd0a4de7731&=&format=webp&quality=lossless&width=1031&height=902"},
    {"title": "III - 🔥 Hades", "image": "https://media.discordapp.net/attachments/1394946325161709699/1395593777208623104/5.png?ex=687b037d&is=6879b1fd&hm=c2b85934177e89ed1f418a6718d92a9484326039e025e58c5e80dc4be1c3f134&=&format=webp&quality=lossless&width=1031&height=902"},
    {"title": "IV - 🧠 Athena", "image": "https://media.discordapp.net/attachments/1394946325161709699/1395593778269519892/6.png?ex=687b037d&is=6879b1fd&hm=7b56e18c3db6c2bff60292e6e90d8bb37d9826884a18f6c6dd8488f212adb308&=&format=webp&quality=lossless&width=1031&height=902"},
    {"title": "V - ⚔️ Ares", "image": "https://media.discordapp.net/attachments/1394946325161709699/1395593773609783357/7.png?ex=687b037c&is=6879b1fc&hm=1b96cdcc467c2c91b96bf136dbe71d017977b6dde2c27f6a8fd37a4e7d36a4b5&=&format=webp&quality=lossless&width=1031&height=902"},
    {"title": "VI - ☀️ Apollo", "image": "https://media.discordapp.net/attachments/1394946325161709699/1395593793696170175/8.png?ex=687b0381&is=6879b201&hm=024d3e074f2c4e69da2009bd6640302807f98d1c0cca5e9e59af1e1e05470d6f&=&format=webp&quality=lossless&width=1031&height=902"},
    {"title": "VII - 🌿 Demeter", "image": "https://media.discordapp.net/attachments/1394946325161709699/1395593794740683044/9.png?ex=687b0381&is=6879b201&hm=f7e08ce95e0570b16a02eda9c8d013a5ba390fc97a7671e0b6b7a29f28b81456&=&format=webp&quality=lossless&width=1031&height=902"},
    {"title": "VIII - 🕊️ Hermes", "image": "https://media.discordapp.net/attachments/1394946325161709699/1395593795764097156/10.png?ex=687b0381&is=6879b201&hm=d94c804154c04ef8c2e5b8f2a91786daf49f26cc20262f8c11e44843650a518c&=&format=webp&quality=lossless&width=1031&height=902"},
    {"title": "IX - 🛡️ Hephaestus", "image": "https://media.discordapp.net/attachments/1394946325161709699/1395593796779114609/11.png?ex=687b0382&is=6879b202&hm=728401e1adda1a6e306b514ce5be8021ca8a99e82bf927affd7f34fde144ffc4&=&format=webp&quality=lossless&width=1031&height=902"},
    {"title": "X - 🌙 Artemis", "image": "https://media.discordapp.net/attachments/1394946325161709699/1395593797811048508/12.png?ex=687b0382&is=6879b202&hm=6f84d207f693f4c1d9b18423af1d24b89b4589b1543161c4101be22549e82089&=&format=webp&quality=lossless&width=1031&height=902"},
    {"title": "XI - 💖 Aphrodite", "image": "https://media.discordapp.net/attachments/1394946325161709699/1395593798846906408/13.png?ex=687b0382&is=6879b202&hm=7ac2fcd12136a3022cbd33e0f1364910b7b3c54bac659b2339aac6ba1a4999f6&=&format=webp&quality=lossless&width=1031&height=902"},
    {"title": "XII - 🍷 Dionysus", "image": "https://media.discordapp.net/attachments/1394946325161709699/1395593799845023764/14.png?ex=687b0382&is=6879b202&hm=1983305c8c45db82f808d8c0a501c1f41771b3f8176b216c4209a8aec87c56ed&=&format=webp&quality=lossless&width=1031&height=902"},
    # Add more gods here...
]

class GuidebookView(View):
    def __init__(self):
        super().__init__(timeout=None)  # Make it persistent
        self.add_item(Button(label="Open Guidebook", style=discord.ButtonStyle.primary, custom_id="open_guidebook"))

    async def disable_all(self, interaction: Interaction):
        for item in self.children:
            if isinstance(item, Button):
                item.disabled = True
        await interaction.edit_original_response(view=self)

    async def update_embed(self, interaction: Interaction):
        page_data = guide_pages[self.page]
        embed = Embed(
            title=page_data["title"],
            description="📚 Navigate the divine pages of the Guidebook.",
            color=0xD4AF37
        )
        embed.set_image(url=page_data["image"])
        await interaction.response.edit_message(embed=embed, view=self)

    @button(label="⏮", style=ButtonStyle.secondary)
    async def previous(self, interaction: Interaction, button: Button):
        self.page = (self.page - 1) % len(guide_pages)
        await self.update_embed(interaction)

    @button(label="⏭", style=ButtonStyle.secondary)
    async def next(self, interaction: Interaction, button: Button):
        self.page = (self.page + 1) % len(guide_pages)
        await self.update_embed(interaction)

    @button(label="📖 First Page", style=ButtonStyle.primary)
    async def first(self, interaction: Interaction, button: Button):
        self.page = 0
        await self.update_embed(interaction)

        for item in self.children:
            if isinstance(item, Button):
                item.disabled = True
        # Because timeout does not have access to interaction, we need to store the message
        try:
            if self.message is not None and hasattr(self.message, "edit"):
                await self.message.edit(view=self)
        except Exception:
            pass

@tree.command(name="guidebook", description="Reveal the sacred Guidebook to the Gods.", guild=discord.Object(id=GUILD_ID))
@app_commands.command(name="guidebook", description="Reveal the sacred Guidebook to the Gods.")
async def guidebook(interaction: Interaction):
    first_page = guide_pages[0]
    embed = Embed(
        title=first_page["title"],
        description="📚 Navigate the divine pages of the Guidebook.",
        color=0xD4AF37
    )
    embed.set_image(url=first_page["image"])

    view = GuidebookView()
    await interaction.response.send_message(embed=embed, view=view)
    view.message = await interaction.original_response()
keep_alive()

if BOT_TOKEN is None:
    raise RuntimeError("Environment variable 'BOT_TOKEN' is not set.")
bot.run(BOT_TOKEN)
