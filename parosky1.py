#!/usr/bin/env python
# -*- coding: utf-8 -*-

import parosky_bot
import urllib
import re
import os
import sys
import pickle
import ConfigParser

class Parosky1(parosky_bot.ParoskyBot):
    def __init__(self):
        screen_name = "parosky1"
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
    def post(self):
        # get favstar html
        url = 'http://favstar.fm/users/parosky0/recent'
        favstring = urllib.urlopen(url).read()

        # extract posts and favs/RTs
        favs = []
        p = re.compile(r'<.*?>')
        p2 = re.compile(r">[0-9]+<")
        p3 = re.compile(r"[0-9]+")
        for line in favstring.splitlines():
            if 'class=\"theTweet\"' in line:
                line = p.sub('', line)
                line = line.replace("\t","")
                favs.append(dict())
                favs[-1]['text'] = line.decode("utf8")
                favs[-1]['count'] = 0
                favs[-1]['id'] = 0
            if 'class=\"count\"' in line:
                line = p.sub('', line)
                if "Others" in line: continue
                favs[-1]['count'] += int(line)
            if 'class=\"bird\"' in line:
                m = re.search("status/[0-9]+",line)
                if m:
                    favs[-1]['id'] = int(m.group(0).replace("status/",""))

        # check update
        try:
            recent_id = pickle.load(open(self.filename_post))
        except:
            recent_id = 0

        # post
        for fav in favs:
            if '@' in fav['text']: continue
            if (fav['id'] > recent_id) and (fav['count'] >= 2):
                self.api.PostUpdate(fav['text'])
                # print fav['text']
                recent_id = max(recent_id, fav['id'])
        pickle.dump(recent_id, open(self.filename_post, "w"))

if __name__ == "__main__":
    func = sys.argv[1]
    os.chdir(os.path.dirname(sys.argv[0]) or '.')
    parosky1 = Parosky1()

    print func
    if func == "favoritereplies":
        parosky1.favoriteReplies()
    elif func == "favoriteretweets":
        parosky1.favoriteRetweets()
    elif func == "makeids":
        parosky1.makeIds(sys.argv[2])
    elif func == "refollow":
        parosky1.refollow()
    elif func == "follow":
        parosky1.follow()
    elif func == "post":
        parosky1.post()
    elif func == "unfollow":
        parosky1.unfollow()
    elif func == "updatedb":
        parosky1.updateDB()
