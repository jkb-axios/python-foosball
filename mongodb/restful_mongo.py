#!/bin/env python

# Create a RESTful wrapper around the mongodb that provides the necessary functions:
#   + add player (required: shortname, date_added; optional: longname, sensor_id, _id)
#   + update player by shortname (all fields optional)
#   + update player by player id (all fields optional)
#   + get player id from shortname
#   + get player id from sensor_id
#   + get player record from player id
#   + get player current stats by player id
#   + add game (and related stats)
#   - remove player (what about related games/stats?)
#   - remove game (and related stats)
#   - update game (and related stats?)
#   - update stats
#   - 
#!/bin/env python

import os, sys, time, logging, signal
import pymongo
from pymongo import MongoClient as MC
from datetime import datetime, timedelta
from pprint import pprint as pp

DEFAULT_IP='127.0.0.1'
DEFAULT_PORT=27017
DEFAULT_DB='foosball'

PLAYERS_COLLECTION = 'testPlayers'
GAMES_COLLECTION = 'testGames'
STATS_COLLECTION = 'testStats'

GOALS_TO_WIN = 10 # 5
GOALS_TO_WIN_BY = 1 # 2

class MongoHelper(object):
    def __init__(self, ip=DEFAULT_IP, port=DEFAULT_PORT, db=DEFAULT_DB):
        self.log = logging.getLogger('MongoHelper')
        self.log.setLevel(logging.DEBUG)
        #fh = logging.FileHandler('/var/log/mongohelper.log')
        fh = logging.FileHandler('./mongohelper.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        self.log.addHandler(fh)
        self.log.info('Creating DatabaseHelper w/ ip=%s port=%s db=%s'%(ip, port, db))
        self._client = MC('mongodb://%s:%s'%(ip, port))
        self._db = self._client[db]
        self._players = self._db[PLAYERS_COLLECTION]
        self._games = self._db[GAMES_COLLECTION]
        self._stats = self._db[STATS_COLLECTION]
        self.current_game = None
        self.current_stats = None

    def getPlayers(self):
        return self._players.find()

    def getPlayerById(self, _id):
        return self._players.find_one({'_id': _id})

    def getPlayerByShortname(self, shortname):
        return self._players.find_one({'shortname': shortname})

    def getGames(self):
        return self._games.find()

    def getStats(self):
        return self._stats.find()

    def addPlayer(self, shortname, fullname=None, sensor_id=None):
        self.log.debug('Adding player: %s, %s, %s'%(shortname, fullname, sensor_id))
        utcnow = datetime.utcnow()
        _id = self.getPlayers().count()
        player = {'_id': _id,                   # unique player id
                  'shortname': shortname,       # something easy to type in (jkb, kipp)
                  'fullname': fullname,         # players full name (optional?)
                  'sensor_id': sensor_id,       # used for rfid or other sensor id
                  'date_added': utcnow}         # date player added
        self.log.debug('Inserting player %s'%(player))
        res = self._players.insert_one(player)
        self.log.debug('Response from insert: %s'%(res.acknowledged))
        if not res.acknowledged:
            return False
        return True, res.inserted_id
        
    def updatePlayerByShortname(self, shortname, fullname=None, sensor_id=None):
        self.log.debug('Updating player: %s  with: %s, %s'%(shortname, fullname, sensor_id))
        if shortname==None or (fullname==None and sensor_id==None):
            return None #TODO: raise exception?
        value_updates = {}
        if fullname!=None:
            value_updates['fullname'] = fullname
        if sensor_id!=None:
            value_updates['sensor_id'] = sensor_id
        res = self._players.update_one({'shortname': shortname},{ '$set': value_updates } )
        if not res.acknowledged:
            self.log.debug('Finished updating player %s, but got back ack.'%(shortname))
            return False
        self.log.debug('Finished updating player %s, matched count: %s modified_count: %s'%(shortname, res.matched_count, res.modified_count))
        return res.matched_count==1
        # The following requires mongo 2.6 or later
        #return res.matched_count+res.modified_count == 2
        
    def updatePlayerById(self, player_id, shortname=None, fullname=None, sensor_id=None):
        self.log.debug('Updating player: %s  with: %s, %s, %s'%(player_id, shortname, fullname, sensor_id))
        if player_id==None or (shortname==None and fullname==None and sensor_id==None):
            return False
        value_updates = {}
        if shortname!=None:
            value_updates['shortname'] = shortname
        if fullname!=None:
            value_updates['fullname'] = fullname
        if sensor_id!=None:
            value_updates['sensor_id'] = sensor_id
        res = self._players.update_one({'_id': player_id},{ '$set': value_updates } )
        if not res.acknowledged:
            self.log.debug('Finished updating player %s, but got back ack.'%(player_id))
            return False
        self.log.debug('Finished updating player %s, matched count: %s modified_count: %s'%(player_id, res.matched_count, res.modified_count))
        return res.matched_count==1
        # The following requires mongo 2.6 or later
        #return res.matched_count+res.modified_count == 2

    def getPlayerIdFromShortname(self, shortname):
        res = self._players.find_one({'shortname': shortname},{})
        if res!=None:
            return res['_id']
        return res # TODO: make sure this returns None if shortname doesn't exist

    def getPlayerIdFromSensorId(self, sensor_id):
        if sensor_id == None:
            return None
        res = self._players.find_one({'sensor_id': sensor_id},{})
        if res!=None:
            return res['_id']
        return None

    def getPlayerCurrentStats(self, player_id):
        stats = self._stats.find({'player_id': player_id}).sort('timestamp',pymongo.DESCENDING)
        if stats.count() < 1:
            return None
        return stats[0]

    def initNewGamePlayerStats(self, shortname):
        if shortname==None:
            return None
        stats = None
        player_id = self.getPlayerIdFromShortname(shortname)
        if player_id!=None:
            stats = self.getPlayerCurrentStats(player_id)
        else:
            res = self.addPlayer(shortname)
            player_id = res.inserted_id

        if stats==None:
            stats = {'player_id': player_id,        # unique id of player
                     # accumulating all-time stats
                     'games_won': 0,                # total num games won
                     'games_lost': 0,               # total num games lost
                     'goals_for': 0,                # total goals for
                     'goals_against': 0,            # total goals against
                     # skill calculations: various methods for determining ranking
                     'skill_calc1': 0,              # skill calc based on 2-player matches
                     'skill_calc2': 0,              # skill calc based on 4-player matches
                     'skill_calc3': 0,              # skill calc based on all matches
                     'skill_calc4': 0,              # alternate skill calc
                     # game duration: how long from kickoff to winning goal
                     'average_game_duration': 0,    # 
                     'longest_game_duration': 0,    # 
                     'shortest_game_duration': 0,   # 
                     # goal duration: how long it took to score for/against
                     'average_goalfor': 0,          # seconds, average time takes
                     'slowest_goalfor': 0,          # seconds
                     'quickest_goalfor': 0,         # seconds
                     'average_goalagainst': 0,      # seconds
                     'slowest_goalagainst': 0,      # seconds 
                     'quickest_goalagainst': 0,     # seconds
                     # streaks: number of goals. Positive=goals for, Negative=goals against
                     'current_goals_streak': 0,     # num goals scored for/against
                     'best_goals_streak': 0,        # max(current_goals_streak)
                     'worst_goals_streak': 0}       # min(current_goals_streak)
        return stats
        

    def startGameBySensorId(self, offense1_sid, offense2_sid, defense1_sid=None, defense2_sid=None):
        o1sn = self.getPlayerIdFromSensorId(offense1_sid)
        o2sn = self.getPlayerIdFromSensorId(offense2_sid)
        d1sn = self.getPlayerIdFromSensorId(defense1_sid)
        d2sn = self.getPlayerIdFromSensorId(defense2_sid)
        return self.startGameByShortname(o1sn, o2sn, d1sn, d2sn)
        
    def startGameByShortname(self, offense1_sn, offense2_sn, defense1_sn=None, defense2_sn=None):
        if offense1_sn==None or offense2_sn==None:
            return None # TODO: raise exception

        # get current player stats, or add new player
        num_players = 2
        offense1 = self.initNewGamePlayerStats(offense1_sn)
        offense2 = self.initNewGamePlayerStats(offense2_sn)

        defense1=None
        if defense1_sn!=None:
            num_players += 1
            defense1 = self.initNewGamePlayerStats(defense1_sn)

        defense2=None
        if defense2_sn!=None:
            num_players += 1
            defense2 = self.initNewGamePlayerStats(defense2_sn)
        
        utcnow = datetime.utcnow()
        self.current_game={
                'timestamp': utcnow,                         # date/time of kickoff
                'players': num_players,                      # number of players, either 2, 3, or 4
                'offense1': offense1,                        # stats of team 1 offense (player 1)
                'offense2': offense2,                        # stats of team 2 offense (player 2)
                'defense1': defense1,                        # stats of team 1 defense (player 3)
                'defense2': defense2,                        # stats of team 2 defense (player 4)
                'goals' : []                                 # list of all goals scored during game

        }

    def gameOver(self):
        ''' First to GOALS_TO_WIN, win by GOALS_TO_WIN_BY
        '''
        team1 = len([x for x in self.current_game['goals'] if x['team_id']%2==1]) # Player 1 or 3
        team2 = len([x for x in self.current_game['goals'] if x['team_id']%2==0]) # Player 2 or 4
        if max(team1,team2) > GOALS_TO_WIN and abs(team1-team2) > GOALS_TO_WIN_BY:
            return True
        return False

    def sendVisitorGoal(self):
        if self.current_game!=None:
            utcnow = datetime.utcnow()
            self.current_game['goals'].append({'timestamp': utcnow,       # date/time goal was scored
                                               'team_id': 2})             # Team 2, Player 2 or 4
            if self.gameOver():
                self.endGame()
            return True
        return False

    def sendHomeGoal(self):
        if self.current_game!=None:
            utcnow = datetime.utcnow()
            self.current_game['goals'].append({'timestamp': utcnow,       # date/time goal was scored
                                               'team_id': 1})             # Team 1, Player 1 or 3
            if self.gameOver():
                self.endGame()
            return True
        return False

    def addWinToStats(self, stats, goals_for, goals_against):
        stats['games_won'] += 1
        stats['goals_for'] += goals_for
        stats['goals_against'] += goals_against

    def addLossToStats(self, stats, goals_for, goals_against):
        stats['games_lost'] += 1
        stats['goals_for'] += goals_for
        stats['goals_against'] += goals_against

    def calculateStats(self):
        #using only info in self.current_game
        team1 = len([x for x in self.current_game['goals'] if x['team_id']%2==1]) # Player 1 or 3
        team2 = len([x for x in self.current_game['goals'] if x['team_id']%2==0]) # Player 2 or 4
        if team1 > team2:
            self.addWinToStats(self.current_game['offense1'], team1, team2)
            self.addWinToStats(self.current_game['defense1'], team1, team2)
            self.addLossToStats(self.current_game['offense2'], team2, team1)
            self.addLossToStats(self.current_game['defense2'], team2, team1)
            # TODO
            #         'skill_calc1': 0,              # skill calc based on 2-player matches
            #         'skill_calc2': 0,              # skill calc based on 4-player matches
            #         'skill_calc3': 0,              # skill calc based on all matches
            #         'skill_calc4': 0,              # alternate skill calc
            #         'average_game_duration': 0,    # 
            #         'longest_game_duration': 0,    # 
            #         'shortest_game_duration': 0,   # 
            #         'average_goalfor': 0,          # seconds, average time takes
            #         'slowest_goalfor': 0,          # seconds
            #         'quickest_goalfor': 0,         # seconds
            #         'average_goalagainst': 0,      # seconds
            #         'slowest_goalagainst': 0,      # seconds 
            #         'quickest_goalagainst': 0,     # seconds
            #         'current_goals_streak': 0,     # num goals scored for/against
            #         'best_goals_streak': 0,        # max(current_goals_streak)
            #         'worst_goals_streak': 0}       # min(current_goals_streak)


    def endGame(self):
        self.calculateStats()
        res = self._games.insert_one(self.current_game)

    def cleanup(self):
        self.log.info('Signal caught... shutting down.')
        if self.game!=None:
            self.log.info('Ending current game, potentially unfinished.')
            self.endGame()


if __name__=='__main__':
    def handleSignal(signal, frame): pass
    signal.signal(signal.SIGINT, handleSignal)
    signal.signal(signal.SIGTERM, handleSignal)

    mongoHelper=MongoHelper(DB_IP, DB_PORT, DB_NAME)
    signal.pause() # wait for signal
    reader.cleanup()

