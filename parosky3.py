#!/usr/bin/env python
# -*- coding: utf-8 -*-

import settings
import psbot
import urllib
import re
import os
import sys
import pickle
import json
import xml.sax.saxutils
import sqlalchemy
import tweepy
import random
import datetime

class Parosky3(psbot.BaseTwitterBot):
    def __init__(self):
        screen_name = "parosky3"
        consumer_key = settings.user_apikey[screen_name]["consumer_key"]
        consumer_secret = settings.user_apikey[screen_name]["consumer_secret"]
        access_token = settings.user_apikey[screen_name]["access_token"]
        access_token_secret = settings.user_apikey[screen_name]["access_token_secret"]
        
        self.append_calllist(self.favorite_replies, 60*11)
        self.append_calllist(self.update_database, 60*13)
        self.append_calllist(self.follow_back, 60*7)
        #self.append_calllist(self.follow, 2)
        self.append_calllist(self.post, 6)
        
        psbot.BaseTwitterBot.__init__(self, screen_name, consumer_key, consumer_secret, access_token, access_token_secret)
    
    # post to twitter
    def post(self):
        tweets_per_hour = pickle.load(open('parosky3_tweets_per_hour.p'))
        rand = random.random()
        hour = datetime.datetime.now().hour
        if rand >= tweets_per_hour[hour] / 10:
            return
        
        tweets = pickle.load(open('parosky3_tweets.p'))
        rand = random.random()
        for t in tweets:
            if rand <= t[2]:
                tweet = t[1]
                break
        self.api.update_status(tweet)
        print tweet

if __name__ == "__main__":
    os.chdir(os.path.dirname(sys.argv[0]) or '.')
    parosky3 = Parosky3()
    parosky3.run()

