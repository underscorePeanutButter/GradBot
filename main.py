import discord
import sqlite3
import datetime
import secret

class Server:
    def __init__(self, id, admin, games, events):
        self.id = id
        self.admin = admin
        self.games = games
        self.events = events

class Game:
    def __init__(self, name, roles):
        self.name = name
        self.roles = roles

class Event:
    def __init__(self, game, date):
        self.game = game
        self.date = date

client = discord.Client()

def parse_date(date):
    date = date.split(" ")
    
    time = date[1].split(":")
    date = date[0].split("/")
    
    month = int(date[0])
    day = int(date[1])
    year = int(date[2])

    if len(year) == 2:
        year += 2000
    
    hour = int(time[0])
    minute = int(time[1])

    return datetime.datetime(year, month, day, hour, minute)

async def send(message, channel=None, user=None):
    if channel:
        await channel.send(message)
    if user:
        await user.send(message)

@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")

@client.event
async def on_message(message):
    if message.guild:
        if message.author == client.user:
            return

        if message.content.startswith("!"):
            db = sqlite3.connect("gradbot.db")

            server = db.execute("SELECT * FROM Servers WHERE id=?", (message.guild.id,)).fetchone()
            if not server:
                await send("This server has not been initialized. You can do so with `!init`.", channel=message.channel)
                return

            message.content = message.content.replace("\"", "").strip("!").split(" ")
            if message.content[0] == "game":
                if message.content[1] == "create":
                    game = " ".join(message.content[2:])
                    db.execute("INSERT INTO Servers VALUES ()")

        return

client.run(secret.TOKEN)
