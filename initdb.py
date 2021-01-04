import sqlite3

db = sqlite3.connect("gradbot.db")

command = """
CREATE TABLE Servers (
id BIGINT,
admin VARCHAR,
games VARCHAR,
events VARCHAR,
announcement_channel VARCHAR)"""
db.execute(command)

db.commit()
db.close()
