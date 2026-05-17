import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
from dotenv import load_dotenv
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pymongo import MongoClient

import random
import os
import sys
import threading

# ================= LOAD ENV =================

load_dotenv()

# ================= MONGODB =================

mongo = MongoClient(os.getenv("MONGOURI"))

try:
    mongo.admin.command("ping")
    print("✅ MongoDB connecté")

except Exception as e:
    print("❌ Erreur MongoDB :", e)

db = mongo["botPSHM"]

config_collection = db["config"]

# ================= CONFIG =================

TOKEN = os.getenv("TOKEN")

CHANNEL_ID = 1501624162907590867
ROLE_ID = 1501628455018692690

LOG_CHANNEL_ID = 1501653212229402634

DAYOFF_CHANNEL_ID = 1505269832361447485

BASE_ROLE_ID = 1502632030104453200

HEURE_ENVOI = 14

PORT = int(os.environ.get("PORT", 10000))

# ================= JOURS =================

JOURS = {
    0: "Lundi",
    1: "Mardi",
    2: "Mercredi",
    3: "Jeudi",
    4: "Vendredi",
    5: "Samedi",
    6: "Dimanche"
}

# ================= DAYOFF DATABASE =================

def load_dayoff():

    data = config_collection.find_one(
        {"type": "dayoff"}
    )

    if data:
        return data.get("days", [])

    return []


def save_dayoff(days):

    config_collection.update_one(
        {"type": "dayoff"},
        {
            "$set": {
                "days": days
            }
        },
        upsert=True
    )

# ================= RP MESSAGES =================

MESSAGES_RP = [

    "🌒 Rendez-vous dans 2 lunes au niveau de la maison à gauche de Deadboot Creek en Ambarinho.",

    "🔥 Rendez-vous dans 1 lune au niveau de Annesburg.",

    "🐎 Les Falcons répondent à l’appel du feu sacré.",

    "💰 Les RedFalcons sont demandés à se réunir.",

    "🪶 L'Organisation demande de confirmer votre présence."
]

# ================= INTENTS =================

intents = discord.Intents.default()

intents.message_content = True
intents.guilds = True
intents.members = True

# ================= BOT =================

bot = commands.Bot(
    command_prefix="//",
    intents=intents
)

# ================= SEND PRESENCE =================

async def envoyer_message_presence(channel, role):

    texte_rp = random.choice(MESSAGES_RP)

    embed = discord.Embed(
        title="📜 Registre des Présences",
        description=(
            f"{texte_rp}\n\n"
            f"✅ Présent\n"
            f"❌ Absent\n"
            f"⏰ Retard"
        ),
        color=0x8B0000
    )

    embed.set_footer(
        text="Le silence est remarqué."
    )

    message = await channel.send(
        content=role.mention,
        embed=embed,
        allowed_mentions=discord.AllowedMentions(
            roles=True
        )
    )

    await message.add_reaction("✅")
    await message.add_reaction("❌")
    await message.add_reaction("⏰")

# ================= DAYOFF VIEW =================

class DayOffView(View):

    def __init__(self):
        super().__init__(timeout=None)

    async def toggle_day(self, interaction, day_id):

        days = load_dayoff()

        if day_id in days:
            days.remove(day_id)

        else:
            days.append(day_id)

        save_dayoff(days)

        jours_text = "\n".join(
            [f"• {JOURS[d]}" for d in sorted(days)]
        )

        if not jours_text:
            jours_text = "Aucun"

        embed = discord.Embed(
            title="📅 Planning Day Off",
            description=jours_text,
            color=0x8B0000
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    @discord.ui.button(
        label="Lundi",
        style=discord.ButtonStyle.grey,
        custom_id="lundi"
    )
    async def lundi(self, interaction, button):
        await self.toggle_day(interaction, 0)

    @discord.ui.button(
        label="Mardi",
        style=discord.ButtonStyle.grey,
        custom_id="mardi"
    )
    async def mardi(self, interaction, button):
        await self.toggle_day(interaction, 1)

    @discord.ui.button(
        label="Mercredi",
        style=discord.ButtonStyle.grey,
        custom_id="mercredi"
    )
    async def mercredi(self, interaction, button):
        await self.toggle_day(interaction, 2)

    @discord.ui.button(
        label="Jeudi",
        style=discord.ButtonStyle.grey,
        custom_id="jeudi"
    )
    async def jeudi(self, interaction, button):
        await self.toggle_day(interaction, 3)

    @discord.ui.button(
        label="Vendredi",
        style=discord.ButtonStyle.grey,
        custom_id="vendredi"
    )
    async def vendredi(self, interaction, button):
        await self.toggle_day(interaction, 4)

    @discord.ui.button(
        label="Samedi",
        style=discord.ButtonStyle.red,
        custom_id="samedi"
    )
    async def samedi(self, interaction, button):
        await self.toggle_day(interaction, 5)

    @discord.ui.button(
        label="Dimanche",
        style=discord.ButtonStyle.red,
        custom_id="dimanche"
    )
    async def dimanche(self, interaction, button):
        await self.toggle_day(interaction, 6)

# ================= TICKET VIEW =================

class TicketView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🥃 Ouvrir un ticket",
        style=discord.ButtonStyle.red,
        custom_id="open_ticket"
    )
    async def open_ticket(self, interaction, button):

        guild = interaction.guild
        author = interaction.user

        category = discord.utils.get(
            guild.categories,
            name="Ticket RP"
        )

        if category is None:

            await interaction.response.send_message(
                "❌ Catégorie Ticket RP introuvable.",
                ephemeral=True
            )

            return

        overwrites = {

            guild.default_role:
            discord.PermissionOverwrite(
                read_messages=False
            ),

            author:
            discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True
            ),

            guild.me:
            discord.PermissionOverwrite(
                read_messages=True
            )
        }

        ticket_channel = await guild.create_text_channel(

            name=f"ticket-{author.name}",

            category=category,

            overwrites=overwrites
        )

        embed = discord.Embed(
            title="📜 Ticket Ouvert",
            description="Expose ta demande.",
            color=0x8B0000
        )

        await ticket_channel.send(
            author.mention,
            embed=embed
        )

        await interaction.response.send_message(
            f"🎫 Ticket créé : {ticket_channel.mention}",
            ephemeral=True
        )

# ================= READY =================

@bot.event
async def on_ready():

    print(f"✅ Connecté : {bot.user}")

    bot.add_view(TicketView())
    bot.add_view(DayOffView())

    if not presence_auto.is_running():
        presence_auto.start()

# ================= AUTO PRESENCE =================

@tasks.loop(minutes=1)
async def presence_auto():

    now = datetime.now()

    if now.hour == HEURE_ENVOI and now.minute == 0:

        days = load_dayoff()

        # ✅ Vérifie si aujourd'hui est un day off
        if now.weekday() in days:

            channel = bot.get_channel(DAYOFF_CHANNEL_ID)

            if channel:

                embed = discord.Embed(
                    title="🌙 Jour de Repos",
                    description=(
                        "Les Falcons restent dans l'ombre aujourd'hui.\n\n"
                        "Aucun rassemblement ne sera organisé ce soir."
                    ),
                    color=0x222222
                )

                await channel.send(embed=embed)

            return

        # ✅ Sinon envoie le registre normal
        channel = bot.get_channel(CHANNEL_ID)

        if channel:

            role = channel.guild.get_role(ROLE_ID)

            if role:
                await envoyer_message_presence(channel, role)
# ================= HELP =================

@bot.command()
async def hp(ctx):

    embed = discord.Embed(
        title="📖 Commandes",
        color=0x8B0000
    )

    commandes = {

        "//registre": "Envoie un registre",

        "//rapport ID": "Rapport présence",

        "//panel": "Créer panel ticket",

        "//dayoff": "Panel jours OFF",

        "//clear 10": "Supprimer messages",

        "//restart": "Redémarrer bot",

        "//stop": "Arrêter bot"
    }

    for nom, desc in commandes.items():

        embed.add_field(
            name=nom,
            value=desc,
            inline=False
        )

    await ctx.send(embed=embed)

# ================= REGISTRE =================

@bot.command()
@commands.has_permissions(administrator=True)
async def registre(ctx):

    role = ctx.guild.get_role(ROLE_ID)

    if role is None:

        await ctx.send(
            "❌ Rôle introuvable."
        )

        return

    await envoyer_message_presence(
        ctx.channel,
        role
    )

# ================= RAPPORT =================

@bot.command()
async def rapport(ctx, message_id: int):

    message = await ctx.channel.fetch_message(
        message_id
    )

    presents = []
    absents = []
    retard = []

    for reaction in message.reactions:

        async for user in reaction.users():

            if user.bot:
                continue

            if str(reaction.emoji) == "✅":
                presents.append(user)

            elif str(reaction.emoji) == "❌":
                absents.append(user)

            elif str(reaction.emoji) == "⏰":
                retard.append(user)

    embed = discord.Embed(
        title="📊 Rapport",
        color=0x222222
    )

    embed.add_field(
        name="Présents",
        value="\n".join(
            [u.mention for u in presents]
        ) or "Personne",
        inline=False
    )

    embed.add_field(
        name="Absents",
        value="\n".join(
            [u.mention for u in absents]
        ) or "Personne",
        inline=False
    )

    embed.add_field(
        name="Retard",
        value="\n".join(
            [u.mention for u in retard]
        ) or "Personne",
        inline=False
    )

    await ctx.send(embed=embed)

# ================= PANEL =================

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):

    embed = discord.Embed(
        title="📩 Ticket RP",
        description="Ouvre un ticket.",
        color=0x8B0000
    )

    await ctx.send(
        embed=embed,
        view=TicketView()
    )

# ================= DAYOFF PANEL =================

@bot.command()
@commands.has_permissions(administrator=True)
async def dayoff(ctx):

    days = load_dayoff()

    jours_text = "\n".join(
        [f"• {JOURS[d]}" for d in sorted(days)]
    )

    if not jours_text:
        jours_text = "Aucun"

    embed = discord.Embed(
        title="📅 Planning Day Off",
        description=jours_text,
        color=0x8B0000
    )

    await ctx.send(
        embed=embed,
        view=DayOffView()
    )

# ================= CLEAR =================

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):

    await ctx.channel.purge(
        limit=amount + 1
    )

# ================= CLOSE TICKET =================

@bot.command()
async def close(ctx):

    if "ticket-" not in ctx.channel.name:
        return

    await ctx.send(
        "🛑 Fermeture du ticket..."
    )

    messages = []

    async for msg in ctx.channel.history(
        limit=None,
        oldest_first=True
    ):

        contenu = msg.content or "[Embed/Fichier]"

        messages.append(
            f"[{msg.created_at.strftime('%d/%m %H:%M')}] {msg.author}: {contenu}"
        )

    logs = "\n".join(messages)

    log_channel = bot.get_channel(
        LOG_CHANNEL_ID
    )

    if log_channel:

        thread = await log_channel.create_thread(
            name=ctx.channel.name,
            type=discord.ChannelType.public_thread
        )

        chunk_size = 1900

        for i in range(
            0,
            len(logs),
            chunk_size
        ):

            await thread.send(
                f"```{logs[i:i+chunk_size]}```"
            )

    await ctx.channel.delete()

# ================= AUTO ROLE =================

@bot.event
async def on_member_join(member):

    role = member.guild.get_role(
        BASE_ROLE_ID
    )

    if role:

        try:
            await member.add_roles(role)

        except Exception as e:
            print(e)

# ================= DELETE COMMAND =================

@bot.event
async def on_command(ctx):

    try:
        await ctx.message.delete()

    except:
        pass

# ================= HTTP SERVER =================

def run_server():

    class Handler(BaseHTTPRequestHandler):

        def do_GET(self):

            self.send_response(200)
            self.end_headers()

            self.wfile.write(
                "Bot Falcons opérationnel".encode("utf-8")
            )

    server = HTTPServer(
        ("0.0.0.0", PORT),
        Handler
    )

    server.serve_forever()

threading.Thread(
    target=run_server,
    daemon=True
).start()

# ================= RUN =================

bot.run(TOKEN)