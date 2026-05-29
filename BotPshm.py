import discord
from discord.ext import commands, tasks
from datetime import datetime
import random
import os
import sys
from discord.ui import View, Button
from dotenv import load_dotenv
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from pymongo import MongoClient
from datetime import datetime

load_dotenv()
# ================= CONFIGURATION =================
TOKEN = os.getenv("TOKEN")
MONGOURI=os.getenv("MONGOURI")
CHANNEL_ID = 1501624162907590867  # Salon RP présence
DAYOFF_CHANNEL_ID = 1505269832361447485
ROLE_ID = 1501628455018692690  # Rôle organisation
HEURE_ENVOI = 16 # Heure RP (20h par défaut)

# Messages immersifs RP (rotation automatique)
MESSAGES_RP = [
    "🌒 Rendez-vous dans 2 lunes au niveau de la maison à gauche de Deadboot Creek en Ambarinho, les rituels se feront à cette endroit .",
    "🔥 Rendez-vous dans 1 lune au niveau de Annesburg. Nous allons peut être rencontrait notre contact",
    "🐎 Les Falcons répondent à l’appel du feu sacré.",
    "💰 Les RedFalcons sont demandé à se réunir.",
    "🪶 L'Organisation demande de confirmer votre présence.",
    ".",
    
    
]

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="//", intents=intents)


# ================= CREATION MESSAGE IMMERSIF =================

async def envoyer_message_presence(channel, role):
    texte_rp = random.choice(MESSAGES_RP)

    embed = discord.Embed(
        title="📜 Registre des Présences — Organisation",
        description=(
            f"{texte_rp}\n\n"
            f"Répondez au registre avant le début des opération:\n\n"
            f"✅ Présent sur le terrain\n"
            f"❌ Indisponible ce soir\n"
            f"⏰ Arrivée tardive prévue"
        ),
        color=0x8B0000
    )

    embed.set_footer(text="Le silence est remarqué. L'absence aussi.")
    message = await channel.send(
        content=role.mention,
        embed=embed,
        allowed_mentions=discord.AllowedMentions(roles=True))
 
    await message.add_reaction("✅")
    await message.add_reaction("❌")
    await message.add_reaction("⏰")

# ================= READY =================
@bot.command()
async def hp (ctx):

    embed = discord.Embed(
        title="📖 Commandes Falcons",
        color=0x8B0000
    )

    embed.add_field(
        name="//registre",
        value="Envoie un registre RP",
        inline=False
    )

    embed.add_field(
        name="//rapport ID",
        value="Rapport des présences",
        inline=False
    )

    embed.add_field(
        name="//panel",
        value="Créer le panel ticket",
        inline=False
    )

    embed.add_field(
        name="//clear 10",
        value="Supprimer des messages",
        inline=False
    )

    embed.add_field(
        name="//restart",
        value="Redémarre le bot",
        inline=False
    )

    await ctx.send(embed=embed)
# ================= ENVOI AUTO CHAQUE SOIR =================

@tasks.loop(minutes=1)
async def presence_auto():
    now = datetime.now()

    if now.hour == HEURE_ENVOI and now.minute == 0:
        channel = bot.get_channel(CHANNEL_ID)

        if channel:
            role = channel.guild.get_role(ROLE_ID)
            await envoyer_message_presence(channel, role)


# ================= COMMANDE MANUELLE STAFF =================

@bot.command()
@commands.has_permissions(administrator=True)
async def registre(ctx):
    """Déclenche le registre de présence RP manuellement"""

    role = ctx.guild.get_role(ROLE_ID)

    await envoyer_message_presence(ctx.channel, role)


# ================= RAPPORT AUTOMATIQUE =================

@bot.command()
@commands.has_permissions(administrator=True)
async def rapport(ctx, message_id: int):
    """Affiche un rapport des présences basé sur les réactions"""

    message = await ctx.channel.fetch_message(message_id)

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
        title="📊 Rapport des Effectifs",
        description="Lecture du registre terminée.",
        color=0x222222
    )

    embed.add_field(
        name="Présents",
        value="\n".join([u.mention for u in presents]) or "Personne",
        inline=False
    )

    embed.add_field(
        name="Absents",
        value="\n".join([u.mention for u in absents]) or "Personne",
        inline=False
    )

    embed.add_field(
        name="Retard",
        value="\n".join([u.mention for u in retard]) or "Personne",
        inline=False
    )

    await ctx.send(embed=embed)
@bot.command()
@commands.has_permissions(administrator=True)
async def stop(ctx):
    """Arrête le bot (Admin uniquement)"""

    await ctx.send("🛑 Le registre est fermé pour ce soir... extinction du relais.")
    await bot.close()
    os._exit(0)
    print("Le bot c'est bien coupé")

#Redémarrage du bot
@bot.command()
@commands.has_permissions(administrator=True)
async def restart(ctx):
    """Redémarre le bot (Admin uniquement)"""

    await ctx.send("♻️ Reprise du relais en cours...")
    os.execv(sys.executable, ['python'] + sys.argv)
#===========================Panel DayOFF================

mongo = MongoClient(MONGOURI)

db = mongo["botPSHM1"]
config_collection = db["config"]

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

# ================= LOAD / SAVE =================

def load_dayoff():

    data = config_collection.find_one({
        "type": "dayoff"
    })

    if data:
        return data.get("days", [])

    return []


def save_dayoff(days):

    config_collection.update_one(
        {
            "type": "dayoff"
        },
        {
            "$set": {
                "days": days
            }
        },
        upsert=True
    )

# ================= MESSAGE PRESENCE =================

async def envoyer_presence():

    channel = bot.get_channel(CHANNEL_ID)

    if not channel:
        return

    role = channel.guild.get_role(ROLE_ID)

    embed = discord.Embed(
        title="📜 Registre des Présences",
        description=(
            "Merci de confirmer votre présence.\n\n"
            "✅ Présent\n"
            "❌ Absent\n"
            "⏰ Retard"
        ),
        color=0x8B0000
    )

    msg = await channel.send(
        content=role.mention,
        embed=embed,
        allowed_mentions=discord.AllowedMentions(
            roles=True
        )
    )

    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await msg.add_reaction("⏰")

# ================= AUTO PRESENCE =================

@tasks.loop(minutes=1)
async def presence_auto():

    now = datetime.now()

    if now.hour == HEURE_ENVOI and now.minute == 0:

        days = load_dayoff()

        # ================= JOUR OFF =================

        if now.weekday() in days:

            channel = bot.get_channel(
                DAYOFF_CHANNEL_ID
            )

            if channel:

                embed = discord.Embed(
                    title="🌙 Jour OFF",
                    description=(
                        "Aucune présence aujourd'hui.\n\n"
                        "Les Falcons restent dans l'ombre."
                    ),
                    color=0x222222
                )

                await channel.send(embed=embed)

            return

        # ================= PRESENCE =================

        await envoyer_presence()

# ================= VIEW =================

class DayOffView(View):

    def __init__(self):
        super().__init__(timeout=None)

    async def toggle_day(
        self,
        interaction,
        day_id
    ):

        days = load_dayoff()

        if day_id in days:
            days.remove(day_id)
            status = "❌ Jour retiré"
        else:
            days.append(day_id)
            status = "✅ Jour ajouté"

        save_dayoff(days)

        jours_text = "\n".join([
            f"• {JOURS[d]}"
            for d in sorted(days)
        ])

        if not jours_text:
            jours_text = "Aucun"

        embed = discord.Embed(
            title="📅 Planning DayOff",
            description=(
                f"{status}\n\n"
                f"{jours_text}"
            ),
            color=0x8B0000
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    # ================= BOUTONS =================

    @discord.ui.button(
        label="Lundi",
        style=discord.ButtonStyle.grey
    )
    async def lundi(self, interaction, button):
        await self.toggle_day(interaction, 0)

    @discord.ui.button(
        label="Mardi",
        style=discord.ButtonStyle.grey
    )
    async def mardi(self, interaction, button):
        await self.toggle_day(interaction, 1)

    @discord.ui.button(
        label="Mercredi",
        style=discord.ButtonStyle.grey
    )
    async def mercredi(self, interaction, button):
        await self.toggle_day(interaction, 2)

    @discord.ui.button(
        label="Jeudi",
        style=discord.ButtonStyle.grey
    )
    async def jeudi(self, interaction, button):
        await self.toggle_day(interaction, 3)

    @discord.ui.button(
        label="Vendredi",
        style=discord.ButtonStyle.grey
    )
    async def vendredi(self, interaction, button):
        await self.toggle_day(interaction, 4)

    @discord.ui.button(
        label="Samedi",
        style=discord.ButtonStyle.red
    )
    async def samedi(self, interaction, button):
        await self.toggle_day(interaction, 5)

    @discord.ui.button(
        label="Dimanche",
        style=discord.ButtonStyle.red
    )
    async def dimanche(self, interaction, button):
        await self.toggle_day(interaction, 6)

# ================= COMMANDE PANEL =================

@bot.command()
@commands.has_permissions(administrator=True)
async def dayoff(ctx):

    days = load_dayoff()

    jours_text = "\n".join([
        f"• {JOURS[d]}"
        for d in sorted(days)
    ])

    if not jours_text:
        jours_text = "Aucun"

    embed = discord.Embed(
        title="📅 Gestion des DayOff",
        description=(
            "Choisissez les jours OFF.\n\n"
            f"{jours_text}"
        ),
        color=0x8B0000
    )

    embed.set_footer(
        text="Les jours OFF désactivent automatiquement les présences."
    )

    await ctx.send(
        embed=embed,
        view=DayOffView()
    )

# ================= READY =================

@bot.event
async def on_ready():

    print(f"✅ Connecté : {bot.user}")

    bot.add_view(DayOffView())

    if not presence_auto.is_running():
        presence_auto.start()
#=====================auto-rôle =======================
BASE_ROLE_ID = 1502632030104453200

@bot.event
async def on_member_join(member):

    role = member.guild.get_role(BASE_ROLE_ID)

    if role is None:
        print("❌ Rôle introuvable")
        return

    try:
        await member.add_roles(role)

        print(f"✅ Rôle donné à {member.name}")

    except Exception as e:
        print(f"Erreur attribution rôle : {e}")


# ================  Close Ticket================
@bot.command()
async def close(ctx):
    """Fermer un ticket avec logs en thread"""

    if "ticket-" not in ctx.channel.name:
        return

    await ctx.send("🛑 Fermeture du dossier en cours...")

    # 🔥 Récupération des messages
    messages = []
    async for msg in ctx.channel.history(limit=None, oldest_first=True):
        contenu = msg.content if msg.content else "[Embed / Fichier]"
        messages.append(f"[{msg.created_at.strftime('%d/%m %H:%M')}] {msg.author}: {contenu}")

    logs = "\n".join(messages)

    log_channel = bot.get_channel(LOG_CHANNEL_ID)

    if log_channel:

        # 🧵 Création du thread avec nom du ticket
        thread = await log_channel.create_thread(
            name=ctx.channel.name,
            type=discord.ChannelType.public_thread
        )

        # 📜 Envoi des logs (découpé si trop long)
        chunk_size = 1900
        for i in range(0, len(logs), chunk_size):
            await thread.send(f"```{logs[i:i+chunk_size]}```")

        # 🧠 Infos du ticket
        embed = discord.Embed(
            title="📁 Ticket archivé",
            description=f"Salon : `{ctx.channel.name}`",
            color=0x8B0000
        )
        embed.add_field(name="Fermé par", value=ctx.author.mention)

        await thread.send(embed=embed)

    # 🗑 suppression du salon
    await ctx.channel.delete()
#gui

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🥃Prend un Béésh Tichii ! et rentre...",
        style=discord.ButtonStyle.red,
        custom_id="open_ticket"
    )
    async def open_ticket(self, interaction: discord.Interaction, button: Button):

        guild = interaction.guild
        author = interaction.user

        category = discord.utils.get(guild.categories, name="Ticket RP")

        if category is None:
            category = await guild.create_category("Ticket RP")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            author: discord.PermissionOverwrite(read_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{author.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="📜 Salle secrétes ouverte",
            description=(
                "« Hao, assieds-toi. Que recherches-tu en entrant ici ? »\n\n"
            ),
            color=0x8B0000
        )

        await ticket_channel.send(author.mention, embed=embed)

        await interaction.response.send_message(
            f"🎫 Ticket créé : {ticket_channel.mention}",
            ephemeral=True
        )
@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):

    embed = discord.Embed(
        title="📩 Saloon Clandestin",
        description="Prend un Béésh Tichii et ouvre la porte nous t'attendions"
    )

    await ctx.send(embed=embed, view=TicketView())

@bot.event
async def on_command(ctx):
    try:
        await ctx.message.delete()
    except:
        pass
#=================================== Panel Persistant===========================================================
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")

    presence_auto.start()

    # ✅ boutons persistants
    bot.add_view(TicketView())

#=================================== Command Clear ==============================================================
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    """Supprime un nombre de messages"""

    if amount <= 0:
        await ctx.send("❌ Nombre invalide.")
        return

    await ctx.channel.purge(limit=amount + 1)  # +1 pour la commande

    msg = await ctx.send(f"🧹 {amount} messages supprimés.")
    await msg.delete(delay=3)

#==================================Logs Ticket==================================================================
LOG_CHANNEL_ID = 1501653212229402634 # salon où seront envoyés les logs
async def save_ticket(channel):
    messages = []

    async for msg in channel.history(limit=None, oldest_first=True):
        messages.append(f"[{msg.created_at.strftime('%d/%m %H:%M')}] {msg.author}: {msg.content}")

    return "\n".join(messages)


#==================================server http bot on=============================================================
PORT = int(os.environ.get("PORT", 10000))

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


bot.run(TOKEN)
