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
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from pprint import pprint as pp

DEFAULT_IP='127.0.0.1'
DEFAULT_PORT=27017
DEFAULT_DB='foosball'

PLAYERS_COLLECTION = 'testPlayers'
GAMES_COLLECTION = 'testGames'
STATS_COLLECTION = 'testStats'

#TODO - add multiple game modes (perhaps a collection in the database?)
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
        #self.current_stats = None

    def getPlayers(self):
        return self._players.find()

    def getPlayerById(self, _id):
        return self._players.find_one({'_id': _id})

    def doesPlayerExist(self, _id):
        return True if self.getPlayerById(_id) else False

    def getPlayerByShortname(self, shortname):
        return self._players.find_one({'shortname': shortname})

    def getPlayerBySensorId(self, sensor_id):
        return self._players.find_one({'sensor_id': sensor_id})

    def getGames(self):
        return self._games.find()

    def getGameById(self, _id):
        return self._games.find_one({'_id': _id})

    def getGameByPlayerId(self, player_id):
        return list(self._games.find({'player_id': player_id}).sort({'timestamp':pymongo.DESCENDING})) # TODO - does this return [None] if no games associated with player? would prefer [] or None, but not [None]

    def getStats(self):
        return self._stats.find()

    def getStatsById(self, _id):
        return self._stats.find_one({'_id': _id})

    def getStatsByPlayerId(self, player_id):
        return list(self._stats.find({'player_id': player_id}).sort({'timestamp':pymongo.DESCENDING})) # TODO - does this return [None] if no stats associated with player? would prefer [] or None, but not [None]

    def addPlayer(self, shortname, fullname=None, sensor_id=None, timestamp=None):
        self.log.debug('Adding player: %s, %s, %s'%(shortname, fullname, sensor_id))
        if shortname==None:
            return None
        if timestamp==None:
            timestamp = datetime.utcnow()
        _id = self.getPlayers().count()
        player = {'_id': _id,                   # unique player id
                  'shortname': shortname,       # something easy to type in (jkb, kipp)
                  'fullname': fullname,         # players full name (optional?)
                  'sensor_id': sensor_id,       # used for rfid or other sensor id
                  'date_added': timestamp}      # date player added
        self.log.debug('Inserting player %s'%(player))
        res1 = self._players.insert_one(player)
        self.log.debug('Response from insert: %s'%(res1.acknowledged))
        res2 = self.initNewPlayerStats(_id, timestamp)
        self.log.debug('Response from init stats: %s'%(res2)
        if not res1.acknowledged:
            return None
        return res1.inserted_id
        
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
            self.log.debug('Finished updating player %s, but got back False ack.'%(shortname))
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
            self.log.debug('Finished updating player %s, but got back False ack.'%(player_id))
            return False
        self.log.debug('Finished updating player %s, matched count: %s modified_count: %s'%(player_id, res.matched_count, res.modified_count))
        return res.matched_count==1
        # The following requires mongo 2.6 or later
        #return res.matched_count+res.modified_count == 2

    def getPlayerIdFromShortname(self, shortname):
        if shortname==None:
            return None
        res = self._players.find_one({'shortname': shortname},{})
        if res==None:
            return None
        return res['_id']
        # TODO: make sure this returns None if shortname doesn't exist

    def getPlayerIdFromSensorId(self, sensor_id):
        if sensor_id == None:
            return None
        res = self._players.find_one({'sensor_id': sensor_id},{})
        if res==None:
            return None
        return res['_id']
        # TODO: make sure this returns None if shortname doesn't exist

    def getPlayerCurrentStats(self, player_id):
        stats = self._stats.find({'player_id': player_id}).sort('timestamp',pymongo.DESCENDING)
        if stats.count() < 1:
            return None
        return stats[0]

    def initNewPlayerStats(self, player_id, timestamp):
        if player_id==None or timestamp==None:
            return None
        stats = self.getPlayerCurrentStats(player_id):
        if stats:
            return stats['_id'] # TODO: raise exception?

        stats = {'_id': str(ObjectId()),        # unique stats id
                 'player_id': player_id,        # unique id of player
                 'game_id': None,               # unique id of game (None for initial stats)
                 'timestamp': timestamp,        # timestamp of game (kickoff), or initial player creation
                 # accumulating all-time stats
                 'games_won': 0,                # total num games won
                 'games_lost': 0,               # total num games lost
                 'goals_for': 0,                # total goals for
                 'goals_against': 0,            # total goals against
                 'goals_scored': 0,             # total goals scored
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
        ack, _id = self._stats.insert_one(stats)
        return _id if ack else None
        
    def startGameBySensorId(self, offense1_sid, offense2_sid, defense1_sid=None, defense2_sid=None):
        if offense1_sid==None or offense2_sid==None:
            return None #TODO - raise exception
        timestamp = datetime.utcnow()
        o1id = self.getPlayerIdFromSensorId(offense1_sid)
        if not o1id:
            o1id = self.addPlayer(shortname=offense1_sid, fullname='Automatically added by sensor_id (offense1)',
                                  sensor_id=offense1_sid, timestamp=timestamp)
        o2id = self.getPlayerIdFromSensorId(offense2_sid)
        if not o2id:
            o2id = self.addPlayer(shortname=offense2_sid, fullname='Automatically added by sensor_id (offense2)',
                                  sensor_id=offense2_sid, timestamp=timestamp)

        d1id = self.getPlayerIdFromSensorId(defense1_sid)
        if defense1_sid and not d1id:
            d1id = self.addPlayer(shortname=defense1_sid, fullname='Automatically added by sensor_id (defense1)',
                                  sensor_id=defense1_sid, timestamp=timestamp)

        d2id = self.getPlayerIdFromSensorId(defense2_sid)
        if defense2_sid and not d2id:
            d2id = self.addPlayer(shortname=defense2_sid, fullname='Automatically added by sensor_id (defense2)',
                                  sensor_id=defense2_sid, timestamp=timestamp)

        return self.startGame(o1id, o2id, d1id, d2id, timestamp)
        
    def startGameByShortname(self, offense1_sn, offense2_sn, defense1_sn=None, defense2_sn=None):
        if offense1_sn==None or offense2_sn==None:
            return None #TODO - raise exception
        timestamp = datetime.utcnow()
        o1id = self.getPlayerIdFromShortname(offense1_sn)
        if not o1id:
            o1id = self.addPlayer(shortname=offense1_sn, fullname='Automatically added by shortname (offense1)',
                                  sensor_id=None, timestamp=timestamp)
        o2id = self.getPlayerIdFromShortname(offense2_sn)
        if not o2id:
            o2id = self.addPlayer(shortname=offense2_sn, fullname='Automatically added by shortname (offense2)',
                                  sensor_id=None, timestamp=timestamp)

        d1id = self.getPlayerIdFromShortname(defense1_sn)
        if defense1_sn and not d1id:
            d1id = self.addPlayer(shortname=defense1_sn, fullname='Automatically added by shortname (defense1)',
                                  sensor_id=None, timestamp=timestamp)

        d2id = self.getPlayerIdFromShortname(defense2_sn)
        if defense2_sn and not d2id:
            d2id = self.addPlayer(shortname=defense2_sn, fullname='Automatically added by shortname (defense2)',
                                  sensor_id=None, timestamp=timestamp)

        return self.startGame(o1id, o2id, d1id, d2id, timestamp)
        
    def startGame(self, offense1, offense2, defense1=None, defense2=None, timestamp=None):
        if offense1==None or offense2==None:
            return None # TODO: raise exception
        if timestamp==None:
            timestamp = datetime.utcnow()

        # check that players exist
        if not self.doesPlayerExist(offense1) or not self.doesPlayerExist(offense2):
            return None #TODO raise exception
        num_players = 2

        if defense1!=None:
            if not self.doesPlayerExist(defense1):
                return None #TODO raise exception
            num_players += 1
        if defense2!=None:
            if not self.doesPlayerExist(defense2):
                return None #TODO raise exception
            num_players += 1
        
        self.current_game={
                'timestamp': timestamp,                      # date/time of kickoff
                'players': num_players,                      # number of players, either 2, 3, or 4
                'offense1': offense1,                        # player id of team 1 offense (player 1)
                'offense2': offense2,                        # player id of team 2 offense (player 2)
                'defense1': defense1,                        # player id of team 1 defense (player 3)
                'defense2': defense2,                        # player id of team 2 defense (player 4)
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
                #TODO - add a wait in case last goal is toggled or canceled
                self.endGame()
            return True
        return False

    def sendHomeGoal(self):
        if self.current_game!=None:
            utcnow = datetime.utcnow()
            self.current_game['goals'].append({'timestamp': utcnow,       # date/time goal was scored
                                               'team_id': 1})             # Team 1, Player 1 or 3
            if self.gameOver():
                #TODO - add a wait in case last goal is toggled or canceled
                self.endGame()
            return True
        return False

    # Toggle between offensive and defensive score
    def toggleLastGoalScorer(self):
        if self.current_game!=None and len(self.current_game['goals'])>0:
            self.current_game['goals'][-1]['team_id'] = (self.current_game['goals'][-1]['team_id']+1)%4+1

    def cancelLastGoal(self):
        if self.current_game!=None and len(self.current_game['goals'])>0:
            del self.current_game['goals'][-1]

    def addWinToStats(self, stats, game_id, timestamp, goals_scored, goals_for, goals_against):
        if stats:
            stats['_id'] = str(ObjectId())
            stats['game_id'] = game_id
            stats['timestamp'] = timestamp
            stats['games_won'] += 1
            stats['goals_for'] += goals_for
            stats['goals_against'] += goals_against
            stats['goals_scored'] += goals_scored

    def addLossToStats(self, stats, game_id, timestamp, goals_scored, goals_for, goals_against):
        if stats:
            stats['_id'] = str(ObjectId())
            stats['game_id'] = game_id
            stats['timestamp'] = timestamp
            stats['games_lost'] += 1
            stats['goals_for'] += goals_for
            stats['goals_against'] += goals_against
            stats['goals_scored'] += goals_scored

    def updatePlayerStats(self):
        o1_stats = self.getPlayerCurrentStats(self.current_game['offense1'])
        o2_stats = self.getPlayerCurrentStats(self.current_game['offense2'])
        d1_stats = self.getPlayerCurrentStats(self.current_game['defense1']) if self.current_game['defense1'] else None
        d2_stats = self.getPlayerCurrentStats(self.current_game['defense2']) if self.current_game['defense2'] else None

        #using only info in self.current_game
        #team1 = len([x for x in self.current_game['goals'] if x['team_id']%2==1]) # Player 1 or 3
        #team2 = len([x for x in self.current_game['goals'] if x['team_id']%2==0]) # Player 2 or 4
        player1 = len([x for x in self.current_game['goals'] if x['team_id']==1]) # Player 1
        player2 = len([x for x in self.current_game['goals'] if x['team_id']==2]) # Player 2
        player3 = len([x for x in self.current_game['goals'] if x['team_id']==3]) # Player 3
        player4 = len([x for x in self.current_game['goals'] if x['team_id']==4]) # Player 4
        team1 = player1+player3
        team2 = player2+player4
        if team1 > team2:
            self.addWinToStats(o1_stats, current_game['_id'], player1, team1, team2)
            self.addWinToStats(d1_stats, current_game['_id'], player3, team1, team2)
            self.addLossToStats(o2_stats, current_game['_id'], player2, team2, team1)
            self.addLossToStats(d2_stats, current_game['_id'], player4, team2, team1)
        else:
            self.addLossToStats(o1_stats, current_game['_id'], player1, team1, team2)
            self.addLossToStats(d1_stats, current_game['_id'], player3, team1, team2)
            self.addWinToStats(o2_stats, current_game['_id'], player2, team2, team1)
            self.addWinToStats(d2_stats, current_game['_id'], player4, team2, team1)
        #TODO:
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

        updated_stats = [o1_stats, o2_stats]
        if d1_stats:
            updated_stats.append(d1_stats)
        if d2_stats:
            updated_stats.append(d2_stats)
        res = self.stats.insert_many(updated_stats)

    def endGame(self):
        self.updatePlayerStats()
        res = self._games.insert_one(self.current_game)
        self.current_game = None

    def cleanup(self):
        self.log.info('Signal caught... shutting down.')
        if self.current_game!=None:
            self.log.info('Ending current game, potentially unfinished.')
            self.endGame()


if __name__=='__main__':
    def handleSignal(signal, frame): pass
    signal.signal(signal.SIGINT, handleSignal)
    signal.signal(signal.SIGTERM, handleSignal)

    mongoHelper=MongoHelper(DB_IP, DB_PORT, DB_NAME)
    signal.pause() # wait for signal
    reader.cleanup()

