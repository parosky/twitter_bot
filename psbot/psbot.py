#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tweepy
import sqlite3
import time
import os

class BaseTwitterBot():
    api = None
    screen_name = None
    filename_db = None
    call_list = []
    FOLLOW_MARGIN = 100

    def __init__(self, screen_name, consumer_key, consumer_secret, access_token, access_token_secret):
        self.screen_name = screen_name
        self.filename_db = screen_name + ".db"

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(auth)
    
    def get_follower_ids(self, user_id=None):
        """ get all followers' IDs """
        followers = []
        cursor = -1
        while True: 
            ret = self.api.followers_ids(id = user_id, cursor = cursor)
            followers += ret[0]
            cursor = ret[1][1]
            if cursor == 0:
                break
        return followers
 
    def get_friend_ids(self, user_id=None):
        """ get all friends' IDs """
        friends = []
        cursor = -1
        while True: 
            ret = self.api.friends_ids(id = user_id, cursor = cursor)
            friends += ret[0]
            cursor = ret[1][1]
            if cursor == 0:
                break
        return friends

    def get_unixtime(self):
        """ get unix epoch time """
        return int(time.time())

    def follow(self):
        """ follow an account listed in database """
        me = self.api.get_user(id=self.screen_name)

        # unfollow
        follow_limit = int(me.followers_count*1.1) - me.friends_count
        num_remove = self.FOLLOW_MARGIN - follow_limit
        if (me.friends_count > 2000) and (num_remove > 0):
            self.unfollow(num_remove)
 
        # follow
        date = self.get_unixtime()
        con = sqlite3.connect(self.filename_db)
        update_data = []
        for row in con.execute("SELECT user_id FROM user WHERE follow_to=3 order by date"):
            target_id = row[0]
            try:
                self.api.create_friendship(id=target_id)
                update_data.append((1, date, target_id))
                print "follow:", target_id
                break
            except:
                update_data.append((4, date, target_id))
                print "follow error:", target_id
        con.executemany("UPDATE user SET follow_to=?,date=? WHERE user_id=?", update_data)
        con.commit()
        con.close()

    def follow_back(self):
        """ follow back """
        date = self.get_unixtime()
        con = sqlite3.connect(self.filename_db)
        update_data = []
        for row in con.execute("SELECT user_id FROM user WHERE follow_from=1 and follow_to=0"):
            target_id = row[0]
            try:
                self.api.create_friendship(target_id)
                update_data.append((1, date, target_id))
                print "follow:", target_id
            except Exception as e:
                update_data.append((4, date, target_id))
                print "follow error:", target_id
        con.executemany("UPDATE user SET follow_to=?,date=? WHERE user_id=?", update_data)
        con.commit()
        con.close()

    def unfollow(self, limit=-1):
        """ unfollow friends who don't follow back """

        date = self.get_unixtime()
        con = sqlite3.connect(self.filename_db)
        count = 0
        for row in con.execute("SELECT user_id FROM user WHERE follow_from=0 and follow_to=1 order by date"):
            target_id = row[0]
            try:
                self.api.destroy_friendship(target_id)
                con.execute("UPDATE user SET follow_to=2,date=%d WHERE user_id=%d" % (date,target_id))
                count += 1
                print "unfollowed:", target_id
            except Exception as e:
                print "unfollow error:", target_id
            con.commit()
            if (limit != -1) and (count>=limit):
                break
        con.close()

    def make_follow_list_from_followers(self, target, excluding_users = []):
        """ make user list to follow from someone's followers """
       
        date = self.get_unixtime()
     
        excluding_list = set()
        for user in excluding_users:
            u = self.api.get_user(id=user)
            excluding_list = excluding_list | set(self.get_follower_ids(user_id=user))
            excluding_list = excluding_list | set(self.get_friend_ids(user_id=user))

        target = self.api.get_user(target)
        target_followers = set(self.get_follower_ids(target.id))

        # target candidate
        target_ids = target_followers - excluding_list
        insert_data = []
        for target_id in target_ids:
            con = sqlite3.connect(self.filename_db)
            cur = con.execute("SELECT user_id FROM user WHERE user_id=%d;" % target_id)
            if cur.fetchone() == None:
                insert_data.append((target_id, 3, 0, date))
        con.executemany("INSERT INTO user VALUES(?,?,?,?);", insert_data)
        con.commit()
        con.close()
        print "%d users added" % len(insert_data)               
        
    def favorite_replies(self):
        """ favorite all replies """
        statuses = self.api.mentions()
        for status in statuses:
            try:
                self.api.create_favorite(id=status.id)
            except:
                return
            print "fav:", str(status.id)

    def favorite_retweets(self):
        """ favorite follower's retweets """
        statuses = self.api.retweeted_to_me()
        for status in statuses:
            if status.user.lang != 'ja':
                continue
            try:
                self.api.create_favorite(id=status.id)
            except:
                return
            print "fav:", str(status.id)
            break

    def update_database(self):
        """ update database of following relations """
        # [follow_to] 0: not following, 1: following, 2: removed, 4: cannot follow back
        # [follow_from] 0: not follower, 1: follower

        # open db
        con = sqlite3.connect(self.filename_db)

        # create table if not exists
        cur = con.execute("SELECT * FROM sqlite_master WHERE type='table' and name='user'")
        if cur.fetchone() == None:
            con.execute("CREATE TABLE user(user_id INTEGER UNIQUE, follow_to INTEGER, follow_from INTEGER, date INTEGER);")
            con.execute("CREATE UNIQUE INDEX user_index ON user(user_id);")
            con.commit()
        
        # get all followers and followings 
        my_followers = set(self.get_follower_ids())
        my_followings = set(self.get_friend_ids())

        # register to database
        date = self.get_unixtime()
        insert_data = []
        update_data = []
        for user_id in set(my_followers) | set(my_followings):
            follow_to = 1 if user_id in my_followings else 0
            follow_from = 1 if user_id in my_followers else 0

            cur = con.execute("SELECT user_id FROM user WHERE user_id=%d;" % user_id)
            if cur.fetchone() == None:
                insert_data.append((user_id, follow_to, follow_from, date))
            else:
                update_data.append((follow_to, follow_from, user_id))

        con.executemany("INSERT INTO user VALUES(?,?,?,?);", insert_data)
        con.executemany("UPDATE user SET follow_to=?, follow_from=? WHERE user_id=?;", update_data)
        con.commit()
        con.close()

    def append_calllist(self, function, interval_min):
        """ append function for run() """
        self.call_list.append((function, interval_min))

    def run(self):
        """ cron job """
        if not os.path.exists(self.filename_db):
            self.update_database()

        # create table if not exists
        con = sqlite3.connect(self.filename_db)
        cur = con.execute("SELECT * FROM sqlite_master WHERE type='table' and name='cron'")
        if cur.fetchone() == None:
            con.execute("CREATE TABLE cron(function UNIQUE, called INTEGER)")
            con.commit()
        con.close()

        for function, interval in self.call_list:
            date = self.get_unixtime()
            print date, function.__name__
            
            con = sqlite3.connect(self.filename_db)
            cur = con.execute("SELECT called FROM cron WHERE function='%s';" % function.__name__)
            row = cur.fetchone()
            if row == None:
                con.execute("INSERT INTO cron VALUES(?,?)", (function.__name__, date))
            else:
                called = row[0]
                if date - called < interval*60:
                    continue
                con.execute("UPDATE cron SET called=? WHERE function=?", (date, function.__name__))
            con.commit()
            con.close()
            print "call:", function.__name__
            function()
