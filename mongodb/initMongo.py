#!/bin/env python

from pymongo import MongoClient as MC
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from time import sleep
from pprint import pprint as pp


#client = MC() # defaults to localhost:27017
client = MC('mongodb://localhost:27017') # or do it explicitly

db = client.foosball

players = db.testPlayers
games = db.testGames
stats = db.testStats

def addInitialPlayers():
    # collection - testPlayers
    utcnow = datetime.utcnow()
    player1 = {
            '_id': 0,                     # unique player id
            'shortname': 'jkb',           # something easy to type in (jkb, kipp)
            'fullname': 'Kipp Bowen',     # players full name (optional?)
            'sensor_id': None,            # used for rfid or other sensor id
            'date_added': utcnow          # date player added
    }

    res = players.insert_one(player1)
    pp(res)

    sleep(1)
    utcnow = datetime.utcnow()
    players234 = [{'_id': 1, 'fullname': 'Bruce Wayne', 'shortname': 'batman',
                   'sensor_id': None, 'date_added': utcnow},
                  {'_id': 2, 'fullname': 'Kevin Kelly', 'shortname': 'ceo',
                   'sensor_id': None, 'date_added': utcnow},
                  {'_id': 3, 'fullname': 'Barack Obama', 'shortname': 'potus',
                   'sensor_id': None, 'date_added': utcnow}]

    res = players.insert_many(players234)
    pp(res)
    sleep(5)

#addInitialPlayers()

utcnow = datetime.utcnow()
delta = timedelta(seconds=5)
p1 = players.find_one({'shortname':'jkb'},{})
p2 = players.find_one({'shortname':'batman'},{})
pp(p1)
pp(p2)

#collection - testGames # Should we have two collections, 2 player and 4 player?
game = {'_id': str(ObjectId()),                      # unique game id
        'timestamp': utcnow,                         # date/time of kickoff
        'players': 2,                                # number of players, either 2 or 4
        'offense1': p1['_id'],                       # stats of team 1 offense (player 1)
        'offense2': p2['_id'],                       # stats of team 2 offense (player 2)
        'defense1': None,                            # stats of team 1 defense (player 3)
        'defense2': None,                            # stats of team 2 defense (player 4)
        'goals': [{'timestamp': utcnow+delta,        # date/time goal was scored
                   'team_id': 1},                    # 1 (player 1), 2, 3 or 4
                  {'timestamp': utcnow+delta*4, 'team_id': 1},
                  {'timestamp': utcnow+delta*8, 'team_id': 1},
                  {'timestamp': utcnow+delta*14, 'team_id': 2},
                  {'timestamp': utcnow+delta*24, 'team_id': 2},
                  {'timestamp': utcnow+delta*34, 'team_id': 2},
                  {'timestamp': utcnow+delta*54, 'team_id': 1},
                  {'timestamp': utcnow+delta*64, 'team_id': 2},
                  {'timestamp': utcnow+delta*84, 'team_id': 1},
                  {'timestamp': utcnow+delta*94, 'team_id': 2},
                  {'timestamp': utcnow+delta*104, 'team_id': 2},
                  {'timestamp': utcnow+delta*114, 'team_id': 2},
                  {'timestamp': utcnow+delta*124, 'team_id': 1},
                  {'timestamp': utcnow+delta*140, 'team_id': 1},
                  {'timestamp': utcnow+delta*144, 'team_id': 2},
                  {'timestamp': utcnow+delta*149, 'team_id': 1},
                  {'timestamp': utcnow+delta*164, 'team_id': 2},
                  {'timestamp': utcnow+delta*174, 'team_id': 1},
                  {'timestamp': utcnow+delta*194, 'team_id': 1},
                  {'timestamp': utcnow+delta*240, 'team_id': 2}]
}

#Collection - testStats
# stats of team 1 offense (player 1)
p1_stats = {'_id': str(ObjectId()),        # unique stats id
            'player_id': p1['_id'],        # unique id of player
            'game_id': game['_id'],        # unique id of game
            'timestamp': utcnow,           # timestamp of game (kickoff)
            # accumulating all-time stats
            'games_won': 0,                # total num games won
            'games_lost': 1,               # total num games lost
            'goals_for': 9,                # total goals for
            'goals_against': 10,           # total goals against
            'goals_scored': 9,             # total goals scored
            # skill calculations: various methods for determining ranking
            'skill_calc1': 0,              # skill calc based on 2-player matches
            'skill_calc2': 0,              # skill calc based on 4-player matches
            'skill_calc3': 0,              # skill calc based on all matches
            'skill_calc4': 0,              # alternate skill calc
            # game duration: how long from kickoff to winning goal
            'average_game_duration': delta.total_seconds()*240,    # 
            'longest_game_duration': delta.total_seconds()*240,    # 
            'shortest_game_duration': delta.total_seconds()*240,   # 
            # goal duration: how long it took to score for/against
            'average_goalfor': 0,          # seconds, average time takes
            'slowest_goalfor': 0,          # seconds
            'quickest_goalfor': 0,         # seconds
            'average_goalagainst': 0,      # seconds
            'slowest_goalagainst': 0,      # seconds 
            'quickest_goalagainst': 0,     # seconds
            # streaks: number of goals. Positive=goals for, Negative=goals against
            'current_goals_streak': -1,     # num goals scored for/against
            'best_goals_streak': 2,        # max(current_goals_streak)
            'worst_goals_streak': -3}       # min(current_goals_streak)

# stats of team 2 offense (player 2)
p2_stats = {'_id': str(ObjectId()),
            'player_id': p2['_id'],
            'game_id': game['_id'],
            'timestamp': utcnow,
            'games_won': 1,
            'games_lost': 0,
            'goals_for': 10,
            'goals_against': 9,
            'goals_scored': 10,
            'skill_calc1': 0,
            'skill_calc2': 0,
            'skill_calc3': 0,
            'skill_calc4': 0,
            'average_game_duration': delta.total_seconds()*240,
            'longest_game_duration': delta.total_seconds()*240,
            'shortest_game_duration': delta.total_seconds()*240,
            'average_goalfor': 0,
            'slowest_goalfor': 0,
            'quickest_goalfor': 0,
            'average_goalagainst': 0,
            'slowest_goalagainst': 0,
            'quickest_goalagainst': 0,
            'current_goals_streak': 1,
            'best_goals_streak': 3,
            'worst_goals_streak': -2}


res = games.insert_one(game)
pp(res)

res = stats.insert_many([p1_stats, p2_stats])
pp(res)

