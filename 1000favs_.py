#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import parosky_bot
import urllib
import re
import random
import pickle
import ConfigParser

class Bot1000favs_(parosky_bot.ParoskyBot):
    def __init__(self):
        screen_name = "1000favs_"
        config = ConfigParser.RawConfigParser()
        config.read('bot.conf')
        consumer_key = config.get(screen_name, "consumer_key")
        consumer_secret = config.get(screen_name, "consumer_secret")
        access_token = config.get(screen_name, "access_token")
        access_token_secret = config.get(screen_name, "access_token_secret")
        self.filename_post = screen_name + "_post_{t}.p"
        parosky_bot.ParoskyBot.__init__(self, screen_name, consumer_key, consumer_secret, access_token, access_token_secret)

    # post to twitter
    # repost parosky0's post which is 2 or more favs/RTs
    def post(self, target):
        target_user = self.api.GetUser(target)
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

        # check update
        try:
            recent_id = pickle.load(open(self.filename_post.replace("{t}",target)))
        except:
            recent_id = 0
        status_id = target_user.status.id
        if recent_id == status_id:
            print "already posted"
            return

        print status_id,recent_id

        # record id
        pickle.dump(status_id, open(self.filename_post.replace("{t}",target), "w"))

        self.api.PostUpdate(text)

        print "posted"


    def Afipost(self):
        tweets = open("twlist.txt").readlines()
        text = random.choice(tweets).strip().decode("utf-8")
        self.api.PostUpdate(text)

if __name__ == "__main__":
    os.chdir(os.path.dirname(sys.argv[0]) or '.')
    func = sys.argv[1]
    bot = Bot1000favs_()

    print func
    if func == "favoritereplies":
        bot.favoriteReplies()
    elif func == "favoriteretweets":
        bot.favoriteRetweets()
    elif func == "makeids":
        bot.makeIds(sys.argv[2])
    elif func == "refollow":
        bot.refollow()
    elif func == "unfollow":
        bot.unfollow()
    elif func == "follow":
        bot.follow()
    elif func == "post":
        bot.post(sys.argv[2])
    elif func == "afipost":
        bot.Afipost()
    elif func == "updatedb":
        bot.updateDB()
