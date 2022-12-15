import dataclasses
import sqlite3
import uuid
import databases
import toml
import json
import itertools
import requests
import httpx
import os
import socket
from quart import Quart, abort, g, request
from quart_schema import QuartSchema, validate_request

app = Quart(__name__)
QuartSchema(app)

app.config.from_file(f"./etc/{__name__}.toml", toml.load)


@dataclasses.dataclass
class Game:
    username: str

# @dataclasses.dataclass
# class Url:
#     url: str

@dataclasses.dataclass
class Guess:
    gameid: str
    word: str

@dataclasses.dataclass
class Information:
    user: str
    attempts: int

database_list = ['DATABASE_PRIMARY','DATABASE_SECONDARY1','DATABASE_SECONDARY2']
database_index = itertools.cycle(database_list)

async def _connect_db():
    database = databases.Database(app.config[next(database_index)]["URL"])
    await database.connect()
    return database

async def _connect_db_primary():
    database = databases.Database(app.config["DATABASE_PRIMARY"]["URL"])
    await database.connect()
    return database
#make _get_db_primary function
def _get_db():
    if not hasattr(g, "sqlite_db"):
        g.sqlite_db = _connect_db()
    return g.sqlite_db

def _get_db_primary():
    if not hasattr(g, "sqlite_db_primary"):
        g.sqlite_db_primary = _connect_db_primary()
    return g.sqlite_db_primary


@app.teardown_appcontext
async def close_connection(exception):
    db = getattr(g, "_sqlite_db", None)
    if db is not None:
        await db.disconnect()


@app.route("/newgame", methods=["POST"])
async def create_game():
    # auth method referenced from https://www.youtube.com/watch?v=VW8qJxy4XcQ
    auth = request.authorization
    if auth and auth.username and auth.password:
        db = await _get_db()
        db_primary = await _get_db_primary()

        # Retrive random ID from the answers table
        word = await db.fetch_one(
            "SELECT answerid FROM answer ORDER BY RANDOM() LIMIT 1"
        )

        # Check if the retrived word is a repeat for the user, and if so grab a new word
        while await db.fetch_one(
            "SELECT answerid FROM games WHERE username = :username AND answerid = :answerid",
            values={"username": auth.username, "answerid": word[0]},
        ):
            word = await db.fetch_one(
                "SELECT answerid FROM answer ORDER BY RANDOM() LIMIT 1"
            )

        # Create new game with 0 guesses
        gameid = str(uuid.uuid1())
        values = {"gameid": gameid, "guesses": 0, "gstate": "In-progress"}
        await db_primary.execute(
            "INSERT INTO game(gameid, guesses, gstate) VALUES(:gameid, :guesses, :gstate)",
            values,
        )

        # Create new row into Games table which connect with the recently connected game
        values = {"username": auth.username, "answerid": word[0], "gameid": gameid}
        await db_primary.execute(
            "INSERT INTO games(username, answerid, gameid) VALUES(:username, :answerid, :gameid)",
            values,
        )

        return values, 201
    else:
        return (
            {"error": "User not verified"},
            401,
            {"WWW-Authenticate": 'Basic realm = "Login required"'},
        )


# Should validate to check if guess is in valid_word table
# if it is then insert into guess table
# update game table by decrementing guess variable
# if word is not valid throw 404 exception
@app.route("/addguess", methods=["PUT"])
@validate_request(Guess)
async def add_guess(data):
    # auth method referenced from https://www.youtube.com/watch?v=VW8qJxy4XcQ
    auth = request.authorization
    if auth and auth.username and auth.password:
        db = await _get_db()
        db_primary = await _get_db_primary()
        currGame = dataclasses.asdict(data)

        # checks whether guessed word is the answer for that game
        isAnswer = await db.fetch_one(
            "SELECT * FROM answer as a where (select count(*) from games where gameid = :gameid and answerid = a.answerid)>=1 and a.answord = :word;",
            currGame,
        )

        # is guessed word the answer
        if isAnswer is not None and len(isAnswer) >= 1:
            # update game status
            try:
                await db_primary.execute(
                    """
                    UPDATE game set gstate = :status where gameid = :gameid
                    """,
                    values={"status": "Finished", "gameid": currGame["gameid"]},
                )
            except sqlite3.IntegrityError as e:
                abort(404, e)

            numguesses = await db.fetch_one(
                "SELECT guesses FROM game WHERE gameid = :gameid",
                values={"gameid":currGame["gameid"]}
            )
            data = {'user' : auth.username, 'attempts' : numguesses[0]}
            print(data)
            r = httpx.post("http://127.0.0.1:5500/payload",data=json.dumps(data), headers={'Content-Type': 'application/json'})

            return {
                "guessedWord": currGame["word"],
                "Accuracy": "\u2713" * 5,
            }, 201  # should return correct answer?

        # if 1 then word is valid otherwise it isn't valid and also check if they exceed guess limit
        isValidGuess = await db.fetch_one(
            "SELECT * from valid_word where valword = :word;",
            values={"word": currGame["word"]},
        )
        if isValidGuess is None:
            isValidGuess = await db.fetch_one(
                "SELECT * from answer where answord = :word;",
                values={"word": currGame["word"]},
            )

        guessNum = await db.fetch_one(
            "SELECT guesses from game where gameid = :gameid",
            values={"gameid": currGame["gameid"]},
        )
        accuracy = ""

        if isValidGuess is not None and len(isValidGuess) >= 1 and guessNum[0] < 6:
            try:
                # make a dict mapping each character and its position from the answer
                answord = await db.fetch_one(
                    "SELECT answord FROM answer as a, games as g  where g.gameid = :gameid and g.answerid = a.answerid",
                    values={"gameid": currGame["gameid"]},
                )

                ansDict = {}
                for i in range(len(answord[0])):
                    ansDict[answord[0][i]] = i

                # compare location of guessed word with answer
                guess_word = currGame["word"]
                for i in range(len(guess_word)):
                    if guess_word[i] in ansDict:
                        # print(ansDict.get(guess_word[i]))
                        if ansDict.get(guess_word[i]) == i:
                            accuracy += "\u2713"
                        else:
                            accuracy += "O"
                    else:
                        accuracy += "X"

                # insert guess word into guess table with accruracy
                await db_primary.execute(
                    "INSERT INTO guess(gameid,guessedword, accuracy) VALUES(:gameid, :guessedword, :accuracy)",
                    values={
                        "guessedword": currGame["word"],
                        "gameid": currGame["gameid"],
                        "accuracy": accuracy,
                    },
                )
                # update game table's guess variable by decrementing it
                await db_primary.execute(
                    """
                    UPDATE game set guesses = :guessNum where gameid = :gameid
                    """,
                    values={
                        "guessNum": (guessNum[0] + 1),
                        "gameid": currGame["gameid"],
                    },
                )

                # if after updating game number of guesses reaches max guesses then mark game as finished
                if guessNum[0] + 1 >= 6:
                    # update game status as finished
                    await db_primary.execute(
                        """
                        UPDATE game set gstate = :status where gameid = :gameid
                        """,
                        values={"status": "Finished", "gameid": currGame["gameid"]},
                    )

                    return "Max attempts.", 202
            except sqlite3.IntegrityError as e:
                abort(404, e)
        else:
            # should return msg saying invalid word?
            return {"Error": "Invalid Word"}
        print(guessNum[0])
        if guessNum[0]+1 == 5:
            numguesses = await db.fetch_one(
                "SELECT guesses FROM game WHERE gameid = :gameid",
                values={"gameid":currGame["gameid"]}
            )
            data = {'user' : auth.username, 'attempts' : numguesses[0]}
            r = httpx.post("http://127.0.0.1:5500/payload",data=json.dumps(data), headers={'Content-Type': 'application/json'})
            print(data)

        return {"guessedWord": currGame["word"], "Accuracy": accuracy}, 201
    else:
        return (
            {"error": "User not verified"},
            401,
            {"WWW-Authenticate": 'Basic realm = "Login required"'},
        )


@app.route("/allgames", methods=["GET"])
async def all_games():
    # auth method referenced from https://www.youtube.com/watch?v=VW8qJxy4XcQ
    auth = request.authorization
    if auth and auth.username and auth.password:
        db = await _get_db()

        games_val = await db.fetch_all(
            "SELECT * FROM game as a where gameid IN (select gameid from games where username = :username) and a.gstate = :gstate;",
            values={"username": auth.username, "gstate": "In-progress"},
        )

        if games_val is None or len(games_val) == 0:
            return {"Message": "No Active Games"}, 406

        return list(map(dict, games_val))
    else:
        return (
            {"error": "User not verified"},
            401,
            {"WWW-Authenticate": 'Basic realm = "Login required"'},
        )


@app.route("/onegame", methods=["GET"])
async def my_game():
    # auth method referenced from https://www.youtube.com/watch?v=VW8qJxy4XcQ
    auth = request.authorization
    if auth and auth.username and auth.password:
        db = await _get_db()
        gameid = request.args.get("id")

        results = await db.fetch_all(
            "select * from game where gameid = :gameid",
            values={"gameid": gameid},
        )

        guess = await db.fetch_all(
            "select guessedword, accuracy from guess where gameid = :gameid",
            values={"gameid": gameid},
        )

        if results[0][2] == "Finished":
            return {"Message": "Not An Active Game"}, 406
        return list(map(dict, (results + guess)))
    else:
        return (
            {"error": "User not verified"},
            401,
            {"WWW-Authenticate": 'Basic realm = "Login required"'},
        )

@app.route("/subscribe", methods=["POST"])
async def register():
    db = await _get_db_primary()
    push = await request.get_json()
    app.logger.debug(json.dumps(push, indent=1))
    await db.execute("DELETE FROM callbackurls where url = :url", values={"url":str(push['url'])})
    await db.execute("INSERT INTO callbackurls(url) VALUES(:url)", values={"url":str(push['url'])})
    checkdb = await db.fetch_one(
        "SELECT url FROM callbackurls where url = :url",
        values={"url":str(push['url'])},
    )
    print("URL: "+checkdb[0])
    return "",200

@app.route("/payload", methods=["POST"])
async def inspect_push():
    print("PINGAS")
    db = await _get_db()
    push = await request.get_json()
    app.logger.info(json.dumps(push, indent=2))
    data = push
    allurls = await db.fetch_all("SELECT url from callbackurls")
    print(allurls)
    for urls in allurls:
        try:
            r = httpx.post(str(urls[0]), data=json.dumps(data), headers={'Content-Type': 'application/json'})
            print(r)
        except:
            print("skipped!")
            continue
    return "", 204

@app.errorhandler(409)
def conflict(e):
    return {"error": str(e)}, 409
