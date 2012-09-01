#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import twitter
import urllib
import re
import random
import datetime
import sqlite3
import time

class ParoskyBot():
    # init
    def __init__(self, screen_name, consumer_key, consumer_secret, access_token, access_token_secret):
        self.screen_name = screen_name
        self.api = twitter.Api(consumer_key, consumer_secret, access_token, access_token_secret, cache=None)
        self.filename_db = screen_name + ".db"
    
    # get all follower's IDs
    def getFollowerIDs(self, id=None):
        if not id:
            me = self.api.GetUser(self.screen_name)
            id = me.id
        ret = self.api.GetFollowerIDs(userid = id, cursor = -1)

        followers = ret["ids"]
        while (ret["next_cursor"]!=0):
            ret = self.api.GetFollowerIDs(userid = id, cursor = ret["next_cursor"])
            followers += ret["ids"]
        return followers

    # get all friend's IDs
    def getFriendIDs(self, id=None):
        if not id:
            me = self.api.GetUser(self.screen_name)
            id = me.id
        ret = self.api.GetFriendIDs(id)
        friends = ret["ids"]
        while (ret["next_cursor"]!=0):
            ret = self.api.GetFriendIDs(user = id, cursor = ret["next_cursor"])
            friends += ret["ids"]
        return friends

    # follow an account listed in a pickle file
    def follow(self):
        # get me
        me = self.api.GetUser(self.screen_name)

        # unfollow
        follow_limit = int(me.GetFollowersCount()*1.1) - me.GetFriendsCount()
        num_remove = 100 - follow_limit
        if (me.GetFriendsCount()>2000)and(num_remove > 0):
            self.unfollow(num_remove)
 
        # calc date
        date = (int)(time.time())

        # follow
        con = sqlite3.connect(self.filename_db)
        update_data = []
        for row in con.execute("SELECT user_id FROM user WHERE follow_to=3 order by date"):
            target_id = row[0]
            try:
                self.api.CreateFriendship(target_id)
                update_data.append((1, date, target_id))
                print "follow:", target_id
                break
            except:
                update_data.append((4, date, target_id))
                print "follow error:", target_id
        con.executemany("UPDATE user SET follow_to=?,date=? WHERE user_id=?", update_data)
        con.commit()
        con.close()

    # refollow
    # follow back
    def refollow(self):
        # calc date
        date = (int)(time.time())

        # refollow
        con = sqlite3.connect(self.filename_db)
        update_data = []
        for row in con.execute("SELECT user_id FROM user WHERE follow_from=1 and follow_to=0"):
            target_id = row[0]
            try:
                self.api.CreateFriendship(target_id)
                update_data.append((1, date, target_id))
                print "follow:", target_id
            except Exception as e:
                update_data.append((4, date, target_id))
                print "follow error:", target_id
        con.executemany("UPDATE user SET follow_to=?,date=? WHERE user_id=?", update_data)
        con.commit()
        con.close()

    def unfollow(self, limit=-1):
        # calc date
        date = (int)(time.time())

        # remove
        con = sqlite3.connect(self.filename_db)
        count = 0
        for row in con.execute("SELECT user_id FROM user WHERE follow_from=0 and follow_to=1 order by date"):
            target_id = row[0]
            try:
                self.api.DestroyFriendship(target_id)
                con.execute("UPDATE user SET follow_to=2,date=%d WHERE user_id=%d" % (date,target_id))
                count += 1
                print "removed:", target_id
            except Exception as e:
                print "remove error:", target_id
            con.commit()
            if (limit != -1) and (count>=limit):
                break
        con.close()

    # make a list to follow
    def makeIds(self, target):
        # calc date
        date = (int)(time.time())
     
        parosky0 = self.api.GetUser("parosky0")
        parosky0_followers = set(self.getFollowerIDs(parosky0.id))
        parosky0_followings = set(self.getFriendIDs(parosky0.id))

        target = self.api.GetUser(target)
        target_followers = set(self.getFollowerIDs(target.id))

        # target candidate
        target_ids = target_followers - (parosky0_followers | parosky0_followings)
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

        
    # favorite all replies
    def favoriteReplies(self):
        rs = self.api.GetReplies()
        for r in rs:
            self.api.CreateFavorite(r)
            print "fav:", str(r.id)

    # favorite follower's retweets
    def favoriteRetweets(self):
        rs = self.api.GetRetweetsToMe()
        for r in rs:
            if r.user.lang != 'ja':
                continue
            self.api.CreateFavorite(r)
            print "fav:", str(r.id)
            break

    def updateDB(self):
        # [follow_to] 0: non following, 1: following, 2: removed
        # [follow_from] 0: non follower, 1: follower


        # open db
        con = sqlite3.connect(self.filename_db)

        # create table if not exists
        cur = con.execute("SELECT * FROM sqlite_master WHERE type='table' and name='user'")
        if cur.fetchone() == None:
            con.execute("CREATE TABLE user(user_id INTEGER UNIQUE, follow_to INTEGER, follow_from INTEGER, date INTEGER);")
            con.execute("CREATE UNIQUE INDEX user_index ON user(user_id);")
            con.commit()

        # calc date
        date = (int)(time.time())
        
        # get all followers and followings 
        parosky0 = self.api.GetUser("parosky0")

        my_followers = set(self.getFollowerIDs())
        my_followings = set(self.getFriendIDs())
        my_followers2 = set(self.getFollowerIDs(parosky0.id))
        my_followings2 = set(self.getFollowerIDs(parosky0.id))

        # all followings and followers
        my_connections = my_followers | my_followings
        my_connections -= (my_followings2 | my_followers2)

        # register to db
        insert_data = []
        update_data = []
        for user_id in my_connections:
            if user_id in my_followings:
                follow_to = 1
            else:
                follow_to = 0

            if user_id in my_followers:
                follow_from = 1
            else:
                follow_from = 0

            cur = con.execute("SELECT user_id FROM user WHERE user_id=%d;" % user_id)
            if cur.fetchone() == None:
                insert_data.append((user_id, follow_to, follow_from, date))
            else:
                update_data.append((follow_to, follow_from, user_id))

        con.executemany("INSERT INTO user VALUES(?,?,?,?);", insert_data)
        con.executemany("UPDATE user SET follow_to=?, follow_from=? WHERE user_id=?;", update_data)
        con.commit()
        con.close()
