#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tweepy
import time
import os
import datetime
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative

Base = sqlalchemy.ext.declarative.declarative_base()

class KeyValue(Base):
    __tablename__ = 'keyvalue'
    key = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    value = sqlalchemy.Column(sqlalchemy.String)

    def __init__(self, key, value):
        self.key = key
        self.value = value

class CronTime(Base):
    __tablename__ = 'crontime'
    function = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    called = sqlalchemy.Column(sqlalchemy.DateTime)

    def __init__(self, function, called):
        self.function = function
        self.called = called

class User(Base):
    # [follow_to] 0: not following, 1: following, 2: removed, 4: cannot follow back
    # [follow_from] 0: not follower, 1: follower
    __tablename__ = 'user'
    user_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    follow_to = sqlalchemy.Column(sqlalchemy.Integer)
    follow_from = sqlalchemy.Column(sqlalchemy.Integer)
    date = sqlalchemy.Column(sqlalchemy.DateTime)

    def __init__(self, user_id, follow_to, follow_from, date):
        self.user_id = user_id
        self.follow_to = follow_to
        self.follow_from = follow_from
        self.date = date

class BaseTwitterBot():
    api = None
    screen_name = None
    filename_db = None
    call_list = []
    FOLLOW_MARGIN = 100

    def __init__(self, screen_name, consumer_key, consumer_secret, access_token, access_token_secret):
        self.screen_name = screen_name
        self.filename_db = screen_name + ".db"

        self.engine = sqlalchemy.create_engine('sqlite:///%s' % self.filename_db)
        self.Session = sqlalchemy.orm.sessionmaker(bind=self.engine) 
        
        User.metadata.create_all(self.engine)
        CronTime.metadata.create_all(self.engine)
        KeyValue.metadata.create_all(self.engine)
        
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

    def follow(self):
        """ follow an account listed in database """
        me = self.api.get_user(id=self.screen_name)

        # unfollow
        follow_limit = int(me.followers_count*1.1) - me.friends_count
        num_remove = self.FOLLOW_MARGIN - follow_limit
        if (me.friends_count > 2000) and (num_remove > 0):
            self.unfollow(num_remove)
 
        # follow
        date = datetime.datetime.now()
        session = self.Session()
        for user in session.query(User).filter(User.follow_to==3).order_by(User.date):
            target_id = user.user_id
            try:
                self.api.create_friendship(id=target_id)
                user.follow_to = 1
                user.date = date
                print "follow:", target_id
                break
            except:
                user.follow_to = 4
                user.date = date
                print "follow error:", target_id
        session.commit()
        session.close()

    def follow_back(self):
        """ follow back """
        date = datetime.datetime.now()
        session = self.Session()
        for user in session.query(User).filter(sqlalchemy.and_(User.follow_from==1, User.follow_to==0)):
            target_id = user.user_id
            try:
                self.api.create_friendship(id=target_id)
                user.follow_to = 1
                user.date = date
                print "follow:", target_id
            except Exception as e:
                user.follow_to = 4
                user.date = date
                print "follow error:", target_id
        session.commit()
        session.close()

    def unfollow(self, limit=-1):
        """ unfollow friends who don't follow back """

        date = datetime.datetime.now()
        session = self.Session()
        for user in session.query(User).filter(sqlalchemy.and_(User.follow_from==0, User.follow_to==1)).order_by(User.date):
            target_id = user.user_id
            try:
                self.api.destroy_friendship(target_id)
                user.follow_to = 2
                user.date = date
                limit = limit - 1
                print "unfollowed:", target_id
            except Exception as e:
                print "unfollow error:", target_id
            if limit <= 0:
                break
        session.commit()
        session.close()

    def make_follow_list_from_followers(self, target, excluding_users = []):
        """ make user list to follow from someone's followers """
       
        date = datetime.datetime.now()
     
        excluding_list = set()
        for user in excluding_users:
            u = self.api.get_user(id=user)
            excluding_list = excluding_list | set(self.get_follower_ids(user_id=user))
            excluding_list = excluding_list | set(self.get_friend_ids(user_id=user))

        target = self.api.get_user(target)
        target_followers = set(self.get_follower_ids(target.id))

        target_ids = target_followers - excluding_list
        session = self.Session()
        count = 0
        for target_id in target_ids:
            user = session.query(User).filter(User.user_id==target_id)
            if user.count() == 0:
                user = User(target_id, 3, 0, date)
                session.add(user)
                count += 1
        session.commit()
        session.close()
        print "%d users added" % count
        
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

        # get all followers and followings 
        my_followers = set(self.get_follower_ids())
        my_followings = set(self.get_friend_ids())

        # register to database
        session = self.Session()
        date = datetime.datetime.now()
        for user_id in set(my_followers) | set(my_followings):
            follow_to = 1 if user_id in my_followings else 0
            follow_from = 1 if user_id in my_followers else 0
            try:
                user = session.query(User).filter(User.user_id==user_id).one()
                user.follow_to = follow_to
                user.follow_from = follow_from
            except sqlalchemy.orm.exc.NoResultFound:
                user = User(user_id, follow_to, follow_from, date)
                session.add(user)
        session.commit()
        session.close()

    def append_calllist(self, function, interval_min):
        """ append function for run() """
        self.call_list.append((function, interval_min))

    def run(self):
        """ cron job """

        session = self.Session()
        for function, interval in self.call_list:
            date = datetime.datetime.now()
            function_name = function.__name__
           
            try:
                crontime = session.query(CronTime).filter(CronTime.function==function_name).one()
            except sqlalchemy.orm.exc.NoResultFound:
                crontime = CronTime(function_name, datetime.datetime.fromtimestamp(0))
                session.add(crontime)

            secondsdelta = calendar.timegm(date.timetuple()) - calendar.timegm(crontime.called.timetuple())
            # secondsdelta =  (date - crontime.called).total_seconds()
            print secondsdelta, function_name
            if secondsdelta < interval*60:
                continue
            
            crontime.called = date
            session.commit()
            function()
        session.close()
