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
            message.content = message.content.strip("!").split("\"")
            
            if type(message.content) == str:
                command = message.content
            else:
                command = message.content[0].split(" ")
                string_args = message.content[1:]
                mentions = message.mentions
                role_mentions = message.role_mentions
            
            if not server:
                db.execute("INSERT INTO Servers VALUES (?, ?, '[]', '[]')", (message.guild.id, str([message.author.id])))
                db.commit()
                server = db.execute("SELECT * FROM Servers WHERE id=?", (message.guild.id,)).fetchone()
                db.close()

            games = {}
            for game in eval(server[2]):
                roles = [discord.utils.find(lambda r: r.id == role, message.channel.guild.roles) for role in game["roles"]]
                games[game["name"]] = Game(game["name"], roles)

            events = [Event(games[event["game"]], parse_date(event["date"])) for event in eval(server[3])]
            server = Server(server[0], eval(server[1]), games, events)

            if command[0] == "game":
                if command[1] == "create":
                    if len(string_args) > 0:
                        game_name = string_args[0]
                        if len(role_mentions) == 0:
                            role_mentions = [discord.utils.find(lambda r: r.name == "@everyone", message.channel.guild.roles)]

                        server.games[game_name] = Game(game_name, role_mentions)

                        db.execute("UPDATE Servers SET games=? WHERE id=?", (str([{"name": game.name, "roles": [role.id for role in game.roles]} for key, game in server.games.items()]), str(server.id)))
                        db.commit()
                        db.close()

                        await send("Game created.", channel=message.channel)
                    else:
                        await send("Please ensure the game name is in quotations.", channel=message.channel)

                    return

            if command[0] == "list":
                if command[1] == "games":
                    if len(games) > 0:
                        await send(", ".join([game.name for key, game in server.games.items()]), channel=message.channel)
                    else:
                        await send("This server has no games.", channel=message.channel)
                    
                    return

            db.close()
            await send("Invalid command syntax. Use `!help` if you need it.", channel=message.channel)
            return

client.run(secret.TOKEN)
