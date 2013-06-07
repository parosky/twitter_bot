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
import random
import sqlalchemy

class Bot1000Favs(psbot.BaseTwitterBot):
    def __init__(self):
        screen_name = "1000favs_"
        consumer_key = settings.user_apikey[screen_name]["consumer_key"]
        consumer_secret = settings.user_apikey[screen_name]["consumer_secret"]
        access_token = settings.user_apikey[screen_name]["access_token"]
        access_token_secret = settings.user_apikey[screen_name]["access_token_secret"]
        
        self.append_calllist(self.favorite_replies, 60*11)
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
        session = self.Session()                                                
        try:                                                                  
            post_recentid = session.query(psbot.KeyValue).filter(psbot.KeyValue.key==db_key).one()
        except sqlalchemy.orm.exc.NoResultFound:                                
            post_recentid = psbot.KeyValue(db_key, 0)                           
            session.add(post_recentid)                                          

        recent_id = int(post_recentid.value)  
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
        post_recentid.value = str(status_id)
        session.commit()
        session.close()

        self.api.update_status(text)

        print "posted"
    

if __name__ == "__main__":
    os.chdir(os.path.dirname(sys.argv[0]) or '.')
    bot = Bot1000Favs()
    bot.run()

