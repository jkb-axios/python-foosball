#!/usr/bin/env python

from flask import Flask, jsonify, abort, request, make_response
from restful_mongo import MongoHelper


#DB_IP = '127.0.0.1'
#DB_PORT = 27017
#DB_NAME = 'foosball'
BASE_PATH='/foosball/api/v1.0'
HELP_TEXT='''\
<HTML>
<H1>Welcome to Python Foosball!</H1>
<br>
curl -i http://localhost:5000/foosball/api/v1.0/players (or /games or /stats)
<br>
<br>
curl -i -H "Content-Type: application/json" -X POST -d '{"shortname":"joker","fullname":"The Joker"}' http://localhost:5000/foosball/api/v1.0/players

</HTML>
'''

testapp = Flask(__name__)

#helper = MongoHelper(DB_IP, DB_PORT, DB_NAME)
helper = MongoHelper()

@testapp.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}))

@testapp.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}))

#curl -i http://localhost:5000/
@testapp.route('/')
def index():
  return '<HTML><a href="%s">Python Foosball</a></HTML>'%(BASE_PATH)

#curl -i http://localhost:5000/foosball/api/v1.0/
@testapp.route(BASE_PATH+'/')
def foosball_index():
  return HELP_TEXT

#curl -i http://localhost:5000/foosball/api/v1.0/players
@testapp.route(BASE_PATH+'/players', methods=['GET'])
def get_players():
    players = helper.getPlayers()
    if players == None:
        #abort(404)
        return 'ERROR - no players'
    return jsonify(list(players))

@testapp.route(BASE_PATH+'/players/<int:player_id>', methods=['GET'])
def get_player_id(player_id):
    player = helper.getPlayerById(player_id)
    if player == None:
        return "ERROR - no player"
    return jsonify(player)

@testapp.route(BASE_PATH+'/players/<string:player_sn>', methods=['GET'])
def get_player_sn(player_sn):
    player = helper.getPlayerByShortname(player_sn)
    if player == None:
        return "ERROR - no player"
    return jsonify(player)

#curl -i -H "Content-Type: application/json" -X POST -d '{"shortname":"joker","fullname":"The Joker"}' http://localhost:5000/foosball/api/v1.0/players
@testapp.route(BASE_PATH+'/players', methods=['POST'])
def add_player():
    if not request.json or not 'shortname' in request.json:
        abort(400)
    shortname = request.json['shortname']
    fullname = request.json.get('fullname', None)
    sensor_id = request.json.get('sensor_id', None)
    ack, _id = helper.addPlayer(shortname, fullname, sensor_id)
    if not ack:
        abort(400)
    return jsonify({'_id': _id}), 201

#curl -i -H "Content-Type: application/json" -X PUT -d '{"shortname":"joker","fullname":"The Joker", "sensor_id":"0123456789"}' http://localhost:5000/foosball/api/v1.0/players/4
@testapp.route(BASE_PATH+'/players/<int:player_id>', methods=['PUT'])
def update_player(player_id):
    if not request.json:
        abort(400)
    player = helper.getPlayerById(player_id)
    if player == None:
        abort(404)
    shortname = request.json.get('shortname', player['shortname'])
    fullname = request.json.get('fullname', player['fullname'])
    sensor_id = request.json.get('sensor_id', player['sensor_id'])
    ack = helper.updatePlayerById(player_id, shortname, fullname, sensor_id)
    if not ack:
        abort(400)
    return jsonify(helper.getPlayerById(player_id)) or abort(400)
    #return jsonify({'_id': player_id, 'shortname': shortname, 'fullname': fullname, 'sensor_id': sensor_id, 'timestamp': player['timestamp']})

@testapp.route(BASE_PATH+'/games', methods=['GET'])
def get_games():
    games = helper.getGames()
    if games == None:
        return 'ERROR - no games'
    return jsonify(list(games))

@testapp.route(BASE_PATH+'/stats', methods=['GET'])
def get_all_stats():
    stats = helper.getStats()
    if stats == None:
        return 'ERROR - no stats'
    return jsonify(list(stats))

@testapp.route(BASE_PATH+'/stats/<int:player_id>', methods=['GET'])
def get_player_stats(player_id):
    stats = helper.getPlayerCurrentStats(player_id)
    if stats == None:
        return "ERROR - no stats"
    return jsonify(stats)

if __name__=='__main__':
  testapp.run(debug=True)

