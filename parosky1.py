#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlalchemy
import tweepy

import settings
import basebot


class Parosky1(basebot.BaseBot):
    def __init__(self):
        screen_name = "parosky1"
        consumer_key = settings.user_apikey[screen_name]["consumer_key"]
        consumer_secret = settings.user_apikey[screen_name]["consumer_secret"]
        access_token = settings.user_apikey[screen_name]["access_token"]
        access_token_secret = settings.user_apikey[screen_name]["access_token_secret"]

        basebot.BaseBot.__init__(self, screen_name,
                                 consumer_key,
                                 consumer_secret,
                                 access_token,
                                 access_token_secret)

        self.append_calllist(self.post, 2)
        self.append_calllist(self.follow, 5)
        self.append_calllist(self.follow_back, 60*7)
        self.append_calllist(self.favorite_replies, 60*11)
        self.append_calllist(self.update_database, 60*13)

    # post to twitter
    # repost parosky0's post which is 3 or more favs/RTs
    def post(self):
        session = self.Session()
        try:
            post_recentid = session.query(basebot.KeyValue).filter(
                basebot.KeyValue.key == 'post').one()
        except sqlalchemy.orm.exc.NoResultFound:
            post_recentid = basebot.KeyValue('post', 0)
            session.add(post_recentid)

        recent_id = int(post_recentid.value)
        print recent_id

        tweets = self.api.user_timeline('parosky0')

        # post
        for tweet in tweets:
            if (tweet.id > recent_id) and (tweet.favorite_count+tweet.retweet_count >= 3):
                text = tweet.text
                if '@' in text:
                    continue
                try:
                    self.api.update_status(text)
                except tweepy.TweepError:
                    return
                post_recentid.value = str(max(recent_id, tweet.id))
                session.commit()
                session.close()
                return

if __name__ == "__main__":
    parosky1 = Parosky1()
    parosky1.run()
