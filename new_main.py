import discord
import sqlite3
import datetime
import asyncio
from threading import Thread
import secret

class Server:
    def __init__(self, id, admin, games, events, announcement_channel):
        self.id = id
        self.admin = admin
        self.games = games
        self.events = events
        self.announcement_channel = announcement_channel

class Game:
    def __init__(self, name, roles):
        self.name = name
        self.roles = roles

class Event:
    def __init__(self, game, date, reminders):
        self.game = game
        self.date = date
        self.reminders = reminders

client = discord.Client()
client.intents.guilds = True

def init():
    loop = asyncio.get_event_loop()
    loop.create_task(client.start(secret.TOKEN))
    loop.create_task(handle_reminders())
    Thread(target=loop.run_forever())

def parse_date(date):
    try:
        date = date.split(" ")
        time = date[1].split(":")
        date = date[0].split("/")
        month = int(date[0])
        day = int(date[1])
        year = int(date[2])
        if len(str(year)) == 2:
            year += 2000
        hour = int(time[0])
        if "am" in time[1]:
            time[1] = time[1].replace("am", "")
            if hour == 12:
                hour = 0
        elif "pm" in time[1]:
            time[1] = time[1].replace("pm", "")
            if hour != 12:
                hour += 12
        minute = int(time[1])
        return datetime.datetime(year, month, day, hour, minute)
    except:
        return

def format_date(date):
    return f"{date.month}/{date.day}/{date.year} {date.hour}:{date.minute}"

async def send(message, channel=None, user=None):
    if channel:
        await channel.send(message)
    if user:
        await user.send(message)

async def handle_reminders():
    db = sqlite3.connect("gradbot.db")
    await asyncio.sleep(10)

    while True:
        servers = db.execute("SELECT * FROM Servers").fetchall()
        for server in servers:
            current_server = Server(server[0], eval(server[1]), eval(server[2]), eval(server[3]), server[4])
            current_server_guild = discord.utils.find(lambda g: g.id == current_server.id, client.guilds)
            current_server.announcement_channel = discord.utils.find(lambda c: c.name == current_server.announcement_channel, current_server_guild.channels)
            games = {}
            if type(current_server.announcement_channel) is not str:
                for game in current_server.games:
                    roles = [discord.utils.find(lambda r: r.id == role, current_server_guild.roles) for role in game["roles"]]
                    games[game["name"]] = Game(game["name"], roles)
                updated_events = []
                for event in current_server.events:
                    now = datetime.datetime.now()
                    if now.hour < 8:
                        now = datetime.datetime(now.year, now.month, now.day - 1, now.hour + 16, now.minute)
                    else:
                        now = datetime.datetime(now.year, now.month, now.day, now.hour - 8, now.minute)
                    date = parse_date(event["date"])
                    now_date_difference = date - now
                    print(now_date_difference.seconds)
                    ref_event = Event(games[event["game"]], date, event["reminders"])
                    message = ""
                    hour_12 = date.hour
                    str_minute_12 = str(date.minute)
                    if hour_12 > 12:
                        hour_12 -= 12
                        str_minute_12 += "pm"
                    else:
                        str_minute_12 += "am"
                    str_hour_12 = str(hour_12)
                    if len(str_minute_12) == 1:
                        str_minute_12 = "0" + str_minute_12
                    str_hour = str(date.hour)
                    if len(str_hour) == 1:
                        str_hour = "0" + str_hour
                    str_minute = str(date.minute)
                    if len(str_minute) == 1:
                        str_minute = "0" + str_minute
                    if not ref_event.reminders["first"]:
                        ref_event.reminders["first"] = 1
                        if not len(ref_event.game.roles):
                            message += "@everyone"
                        message += f"{' '.join([role.mention for role in ref_event.game.roles])}\nThere will be {ref_event.game.name} on {date.month}/{date.day}/{date.year} at {str_hour}:{str_minute} ({str_hour_12}:{str_minute_12})."
                        await send(message, channel=current_server.announcement_channel)
                        updated_events.append(ref_event)
                    elif now.year >= date.year and now.month >= date.month and now.day >= date.day and not ref_event.reminders["long"] and not (now.hour >= date.hour and now.minute >= date.minute):
                        ref_event.reminders["long"] = 1
                        if not len(ref_event.game.roles):
                            message += "@everyone"
                        message += f"{' '.join([role.mention for role in ref_event.game.roles])}\n{ref_event.game.name} today at {str_hour}:{str_minute} ({str_hour_12}:{str_minute_12})."
                        await send(message, channel=current_server.announcement_channel)
                        updated_events.append(ref_event)
                    # elif now.year >= date.year and now.month >= date.month and now.day >= date.day and now.hour >= date.hour and not ref_event.reminders["short"] and not now.minute >= date.minute:
                    elif now_date_difference.days == 0 and now_date_difference.seconds <= 1800 and not ref_event.reminders["short"]:
                        ref_event.reminders["short"] = 1
                        if not len(ref_event.game.roles):
                            message += "@everyone"
                        message += f"{' '.join([role.mention for role in ref_event.game.roles])}\n{ref_event.game.name} starts in {round(now_date_difference.seconds / 60)} minutes!"
                        await send(message, channel=current_server.announcement_channel)
                        updated_events.append(ref_event)
                    elif now_date_difference.days == 0 and now_date_difference.seconds <= 0:
                        if not len(ref_event.game.roles):
                            message += "@everyone"
                        message += f"{' '.join([role.mention for role in ref_event.game.roles])}\n{ref_event.game.name} starts now!"
                        await send(message, channel=current_server.announcement_channel)
                db.execute("UPDATE Servers SET events=? WHERE id=?", (str([{"game": event.game.name, "date": format_date(event.date), "reminders": {"first": event.reminders["first"], "long": event.reminders["long"], "short": event.reminders["short"]}} for event in updated_events]), current_server.id))
                db.commit()
        await asyncio.sleep(5)

@client.event
async def on_ready():
    await client.change_presence(status=discord.Status.online)
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
                command = message.content[0].strip().split(" ")
                string_args = message.content[1:]
                extras = message.content[-1].strip()
                mentions = message.mentions
                role_mentions = message.role_mentions

            if not server:
                db.execute("INSERT INTO Servers VALUES (?, ?, '[]', '[]', '')", (message.guild.id, str([message.author.id])))
                db.commit()
                server = db.execute("SELECT * FROM Servers WHERE id=?", (message.guild.id,)).fetchone()

            games = {}
            for game in eval(server[2]):
                roles = [discord.utils.find(lambda r: r.id == role, message.channel.guild.roles) for role in game["roles"]]
                games[game["name"]] = Game(game["name"], roles)

            events = [Event(games[event["game"]], parse_date(event["date"]), event["reminders"]) for event in eval(server[3])]
            announcement_channel = discord.utils.find(lambda c: c.name == server[4], message.guild.channels)
            server = Server(server[0], eval(server[1]), games, events, announcement_channel)

            if command[0] == "help":
                await send("Available commands:\n`!list games` list this server's games\n`!list schedule` list all upcoming events\n`!game create \"<game name>\" <role mentions>` create a new game with the specified name (reminders will include the specified role mentions)\n`!game delete \"<game name>\"` delete the game with the specified name\n`!game schedule \"<game name>\" <date (mm/dd/yyyy)> <time (hh:mm in 24h)>` schedule a new event\n`!game unschedule \"<game name>\"` cancel all events related to the specified game\n`!set channel <channel mention>` change the channel in which the bot should send event reminders", channel=message.channel)
                return

            elif command[0] == "game":
                if command[1] == "create":
                    if len(string_args) > 0:
                        game_name = string_args[0]
                        # if len(role_mentions) == 0:
                        #     role_mentions = [discord.utils.find(lambda r: r.name == "@everyone", message.channel.guild.roles)]

                        if game_name in server.games:
                            await send("That game already exists.", channel=message.channel)
                            return

                        server.games[game_name] = Game(game_name, role_mentions)

                        db.execute("UPDATE Servers SET games=? WHERE id=?", (str([{"name": game.name, "roles": [role.id for role in game.roles]} for key, game in server.games.items()]), str(server.id)))
                        db.commit()
                        db.close()

                        await send("Game created.", channel=message.channel)
                    else:
                        await send("Please ensure the game name is in quotations.", channel=message.channel)

                    return

                if command[1] == "delete":
                    if len(string_args) > 0:
                        game_name = string_args[0]

                        if game_name not in server.games:
                            await send("That game does not exist. Please check your spelling and try again.", channel=message.channel)
                            return

                        for event in server.events:
                            if event.game.name == game_name:
                                server.events.remove(event)

                        del server.games[game_name]

                        db.execute("UPDATE Servers SET games=?, events=? WHERE id=?", (str([{"name": game.name, "roles": [role.id for role in game.roles]} for key, game in server.games.items()]), str([{"game": event.game.name, "date": format_date(event.date), "reminders": {"first": event.reminders["first"], "long": event.reminders["long"], "short": event.reminders["short"]}} for event in server.events]), str(server.id)))
                        db.commit()
                        db.close()

                        await send("Game deleted.", channel=message.channel)
                    else:
                        await send("Please ensure the game name is in quotations.", channel=message.channel)

                    return

                if command[1] == "schedule":
                    if len(string_args) > 0:
                        game_name = string_args[0]
                        date = parse_date(extras)

                        if not date:
                            await send("Invalid date. Please check your formatting and try again.", channel=message.channel)
                            return

                        if game_name not in server.games:
                            await send("That game does not exist. Please check your spelling and try again.", channel=message.channel)
                            return

                        server.events.append(Event(server.games[game_name], date, {"long": 0, "short": 0}))

                        db.execute("UPDATE Servers SET events=? WHERE id=?", (str([{"game": event.game.name, "date": format_date(event.date), "reminders": {"first": 0, "long": 0, "short": 0}} for event in server.events]), str(server.id)))
                        db.commit()
                        db.close()

                        await send("Event scheduled.", channel=message.channel)
                    else:
                        await send("Please ensure the game name is in quotations.", channel=message.channel)

                    return

                if command[1] == "unschedule":
                    if len(string_args) > 0:
                        game_name = string_args[0]

                        if game_name not in server.games:
                            await send("That game does not exist. Please check your spelling and try again.", channel=message.channel)
                            return

                        events_to_remove = []
                        for event in server.events:
                            if event.game.name == game_name:
                                events_to_remove.append(event)

                        for event in events_to_remove:
                            server.events.remove(event)

                        db.execute("UPDATE Servers SET events=? WHERE id=?", (str([{"game": event.game.name, "date": format_date(event.date), "reminders": {"first": event.reminders["first"], "long": event.reminders["long"], "short": event.reminders["short"]}} for event in server.events]), str(server.id)))
                        db.commit()
                        db.close()

                        await send("Events unscheduled.", channel=message.channel)
                    else:
                        await send("Please ensure the game name is in quotations.", channel=message.channel)

                    return

            if command[0] == "set":
                if command[1] == "channel":
                    channel_id = command[2].replace("<","").replace(">","").replace("#","")
                    channel = discord.utils.find(lambda c: c.id == int(channel_id), message.guild.channels)
                    server.announcement_channel = channel

                    db.execute("UPDATE Servers SET announcement_channel=? WHERE id=?", (server.announcement_channel.name, server.id))
                    db.commit()
                    db.close()

                    await send("Announcement channel set.", channel=message.channel)

                    return

            if command[0] == "list":
                if command[1] == "games":
                    if len(server.games) > 0:
                        await send(", ".join([game.name for key, game in server.games.items()]), channel=message.channel)
                    else:
                        await send("This server has no games.", channel=message.channel)

                    return

                if command[1] == "schedule":
                    if len(server.events) > 0:
                        messages = []
                        for event in server.events:
                            date = event.date
                            hour_12 = date.hour
                            str_minute_12 = str(date.minute)
                            if hour_12 > 12:
                                hour_12 -= 12
                                str_minute_12 += "pm"
                            else:
                                str_minute_12 += "am"
                            str_hour_12 = str(hour_12)
                            if len(str_minute_12) == 1:
                                str_minute_12 = "0" + str_minute_12
                            str_hour = str(date.hour)
                            if len(str_hour) == 1:
                                str_hour = "0" + str_hour
                            str_minute = str(date.minute)
                            if len(str_minute) == 1:
                                str_minute = "0" + str_minute

                            messages.append(f"{event.game.name} at {str_hour}:{str_minute} on {date.month}/{date.day}/{date.year} ({str_hour_12}:{str_minute_12})")
                        
                        await send(", ".join(messages), channel=message.channel)
                    else:
                        await send("There are no scheduled games.", channel=message.channel)

                    return

                if command[1] == "channel":
                    if not server.announcement_channel:
                        await send("This server doesn't have an announcement channel set.", message.channel)
                    else:
                        await send(server.announcement_channel.mention, message.channel)

                    return

            db.close()
            await send("Invalid command syntax. Use `!help` if you need it.", channel=message.channel)
            return

init()
