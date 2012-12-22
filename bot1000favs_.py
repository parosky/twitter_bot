#!/usr/bin/env python
# -*- coding: utf-8 -*-

import settings
import psbot
import urllib
import re
import os
import sys
import pickle
import ConfigParser
import json
import xml.sax.saxutils
import sqlite3
import random

class Bot1000Favs(psbot.BaseTwitterBot):
    def __init__(self):
        screen_name = "1000favs_"
        consumer_key = settings.user_apikey[screen_name]["consumer_key"]
        consumer_secret = settings.user_apikey[screen_name]["consumer_secret"]
        access_token = settings.user_apikey[screen_name]["access_token"]
        access_token_secret = settings.user_apikey[screen_name]["access_token_secret"]
        
        self.append_calllist(self.favorite_replies, 60*11)
        self.append_calllist(self.favorite_retweets, 23)
        self.append_calllist(self.update_database, 60*13)
        self.append_calllist(self.follow_back, 60*7)
        self.append_calllist(self.follow, 2)
        self.append_calllist(self.post_250favs, 23)
        self.append_calllist(self.post_500favs, 29)
        self.append_calllist(self.post_1000favs, 31)
        psbot.BaseTwitterBot.__init__(self, screen_name, consumer_key, consumer_secret, access_token, access_token_secret)
    
    def post_250favs(self):
        self.post('250favs')
    def post_500favs(self):
        self.post('500favs')
    def post_1000favs(self):
        self.post('1000favs')
    # post to twitter
    def post(self, target):
        print target
        db_key = "recent_id_%s" % target 
        con = sqlite3.connect(self.filename_db)
        cur = con.execute("SELECT * FROM sqlite_master WHERE type='table' and name='key_value'")
        if cur.fetchone() == None:
            con.execute("CREATE TABLE key_value(key UNIQUE, value);")
            con.commit()
        cur = con.execute("SELECT value FROM key_value WHERE key='%s'" % db_key)
        row = cur.fetchone()
        if row:
            recent_id = row[0]
        else:
            recent_id = 0
            con.execute("INSERT INTO key_value VALUES(?, ?)", (db_key, recent_id))
            con.commit()
        con.close()
 
        target_user = self.api.get_user(target)
        text = target_user.status.text
        text = text + " " + target
        
        if len(text)>140:
            return
        if "http" in text:
            return
        if "twpss" in text:
            return
        if "[PR]" in text:
            return

        status_id = target_user.status.id
        print status_id,recent_id
        if recent_id == status_id:
            print "already posted"
            return


        # record id
        con = sqlite3.connect(self.filename_db)
        con.execute("UPDATE key_value SET value=? WHERE key=?;", (status_id, db_key))
        con.commit()
        con.close()

        self.api.update_status(text)

        print "posted"
    
    def afipost(self):
        tweets = open("1000favs__twlist.txt").readlines()
        text = random.choice(tweets).strip().decode("utf-8")
        self.api.update_status(text)


if __name__ == "__main__":
    os.chdir(os.path.dirname(sys.argv[0]) or '.')
    bot = Bot1000Favs()
    if len(sys.argv) > 1:
        uid = sys.argv[1]
        if uid == "afipost":
            bot.afipost()
        else:
            bot.make_follow_list_from_followers(uid, ["parosky0"])
    else:
        bot.run()

