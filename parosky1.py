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

class Parosky1(psbot.BaseTwitterBot):
    def __init__(self):
        screen_name = "parosky1"
        consumer_key = settings.user_apikey[screen_name]["consumer_key"]
        consumer_secret = settings.user_apikey[screen_name]["consumer_secret"]
        access_token = settings.user_apikey[screen_name]["access_token"]
        access_token_secret = settings.user_apikey[screen_name]["access_token_secret"]
        
        self.append_calllist(self.favorite_replies, 60*11)
        self.append_calllist(self.favorite_retweets, 23)
        self.append_calllist(self.update_database, 60*13)
        self.append_calllist(self.follow_back, 60*7)
        self.append_calllist(self.follow, 2)
        self.append_calllist(self.post, 2)
        
        psbot.BaseTwitterBot.__init__(self, screen_name, consumer_key, consumer_secret, access_token, access_token_secret)
    
    # post to twitter
    # repost parosky0's post which is 3 or more favs/RTs
    def post(self):
        session = self.Session()
        try:
            post_recentid = session.query(psbot.KeyValue).filter(psbot.KeyValue.key=='post').one()
        except sqlalchemy.orm.exc.NoResultFound:
            post_recentid = psbot.KeyValue('post', 0)
            session.add(post_recentid)

        recent_id = int(post_recentid.value)
        print recent_id
        
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
            if "'fs-tweet-meta fs-sunken-panel'" in line:
                line = p.search(line).group(0)
                line = line.replace("data-model=", "")
                line = line.strip("'")
                tw = json.loads(line)
                for t in tw:
                    favs[-1]['count'] += int(t["total"])

        # post
        for fav in favs:
            if (fav['id'] > recent_id) and (fav['count'] >= 3):
                text = self.api.get_status(fav['id']).text
                if '@' in text:
                    continue
                try:
                    self.api.update_status(text)
                except tweepy.TweepError:
                    return
                post_recentid.value = str(max(recent_id, fav['id']))
                session.commit()
                session.close()
                return

if __name__ == "__main__":
    os.chdir(os.path.dirname(sys.argv[0]) or '.')
    parosky1 = Parosky1()
    if len(sys.argv) > 1:
        uid = sys.argv[1]
        parosky1.make_follow_list_from_followers(uid, ["parosky0"])
    else:
        parosky1.run()

