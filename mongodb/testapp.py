#!/usr/bin/env python

from flask import Flask, jsonify
from pymongo import MongoClient as MC

DB_IP = '127.0.0.1'
DB_PORT = 27017
DB_NAME = 'foosball'
PLAYERS_COLLECTION = 'testPlayers'
GAMES_COLLECTION = 'testGames'

testapp = Flask(__name__)

client = MC('mongodb://%s:%s'%(DB_IP,DB_PORT))
db = client[DB_NAME]

def to_native(x):
  try:
    jsonify(x)
  except:
    if type(x)==dict:
      for k,v in x:
        x[k]=to_native(v)
        print k,v,x[i]
    elif type(x)==list:
      for i,v in enumerate(x):
        x[i]=to_native(v)
        print i,v,x[i]
    else:
      x = str(x)
      print x
  finally:
    return x

@testapp.route('/')
def index():
  return "Hello World!"

@testapp.route('/foosball/api/v1.0/players', methods=['GET'])
def get_players():
    try:
      return jsonify(to_native(list(db[PLAYERS_COLLECTION].find())))
    except:
      return jsonify({"ERROR"})

@testapp.route('/foosball/api/v1.0/games', methods=['GET'])
def get_games():
    try:
      return jsonify(to_native(list(db[GAMES_COLLECTION].find())))
    except:
      return jsonify({"ERROR"})

if __name__=='__main__':
  testapp.run(debug=True)

