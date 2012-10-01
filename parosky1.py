#!/usr/bin/env python
# -*- coding: utf-8 -*-

import parosky_bot
import urllib
import re
import os
import sys
import pickle
import ConfigParser
import json

class Parosky1(parosky_bot.ParoskyBot):
    def __init__(self):
        screen_name = "parosky1"
        config = ConfigParser.RawConfigParser()
        config.read('bot.conf')
        consumer_key = config.get(screen_name, "consumer_key")
        consumer_secret = config.get(screen_name, "consumer_secret")
        access_token = config.get(screen_name, "access_token")
        access_token_secret = config.get(screen_name, "access_token_secret")
        self.filename_post = screen_name + "_post.p"
        parosky_bot.ParoskyBot.__init__(self, screen_name, consumer_key, consumer_secret, access_token, access_token_secret)

    # post to twitter
    # repost parosky0's post which is 3 or more favs/RTs
    def post(self):
        # get favstar html
        url = 'http://favstar.fm/users/parosky0/recent'
        favstring = urllib.urlopen(url).read()

        # extract posts and favs/RTs
        favs = []
        p = re.compile(r"data-model='.*?'")
        for line in favstring.splitlines():
            if "'fs-tweet'" in line:
                line = p.search(line).group(0)
                line = line.replace("data-model=", "")
                line = line.strip("'")
                tw = json.loads(line)
                favs.append({})
                favs[-1]['id'] = int(tw["tweet_id"])
                favs[-1]['count'] = 0
            if "'fs-tweet-text'" in line:
                line = line.strip()
                line = re.sub("<.*?>", "", line)
                favs[-1]['text'] = line
            if "'fs-tweet-meta fs-sunken-panel'" in line:
                line = p.search(line).group(0)
                line = line.replace("data-model=", "")
                line = line.strip("'")
                tw = json.loads(line)
                for t in tw:
                    favs[-1]['count'] += int(t["total"])
        # check update
        try:
            recent_id = pickle.load(open(self.filename_post))
        except:
            recent_id = 0

        # post
        for fav in favs:
            if '@' in fav['text']: continue
            if (fav['id'] > recent_id) and (fav['count'] >= 3):
                try:
                    self.api.PostUpdate(fav['text'])
                    # print fav['text']
                    recent_id = max(recent_id, fav['id'])
                    pickle.dump(recent_id, open(self.filename_post, "w"))
                    return
                except:
                    pass

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
