#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tweepy
import calendar
import datetime
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative
import os

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
    # [follow_to]
    #   0: not following
    #   1: following
    #   2: removed
    #   4: cannot follow back
    # [follow_from]
    #   0: not follower
    #   1: follower
    __tablename__ = 'user'
    user_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, index=True)
    follow_to = sqlalchemy.Column(sqlalchemy.Integer, index=True)
    follow_from = sqlalchemy.Column(sqlalchemy.Integer, index=True)
    date = sqlalchemy.Column(sqlalchemy.DateTime)

    def __init__(self, user_id, follow_to, follow_from):
        self.user_id = user_id
        self.follow_to = follow_to
        self.follow_from = follow_from
        self.date = datetime.datetime.now()


class BaseBot():
    FOLLOW_MARGIN = 100

    def __init__(self, screen_name, consumer_key, consumer_secret,
                 access_token, access_token_secret):
        self.screen_name = screen_name

        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.filename_lock = '%s/lock/%s.lock' % (self.directory, screen_name)
        self.filename_db = '%s/database/%s.db' % (self.directory, self.screen_name)

        self.engine = sqlalchemy.create_engine('sqlite:///%s' % self.filename_db)
        self.Session = sqlalchemy.orm.sessionmaker(bind=self.engine)

        User.metadata.create_all(self.engine)
        CronTime.metadata.create_all(self.engine)
        KeyValue.metadata.create_all(self.engine)

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(auth)

        self.call_list = []

    def follow(self):
        """ follow an account from public_timeline """
        me = self.api.get_user(id=self.screen_name)

        # unfollow
        follow_limit = int(me.followers_count*1.1) - me.friends_count
        num_remove = self.FOLLOW_MARGIN - follow_limit
        if (me.friends_count > 2000) and (num_remove > 0):
            self.unfollow(num_remove)

        # follow
        target_id = -1
        while target_id == -1:
            tweets = self.api.search(lang='ja', q='-http -@ -#', count=100)
            for tweet in tweets:
                if ('@' or 'http' or '#') not in tweet.text:
                        target_id = tweet.author.id
                        break

        session = self.Session()
        user = User(target_id, 0, 0)
        try:
            self.api.create_friendship(id=target_id)
            user.follow_to = 1
            print "follow:", target_id
        except:
            user.follow_to = 4
            print "follow error:", target_id
        session.add(user)
        session.commit()
        session.close()

    def follow_back(self, limit=1000):
        """ follow back """
        date = datetime.datetime.now()
        session = self.Session()
        for user in session.query(User).filter(
                sqlalchemy.and_(User.follow_from == 1, User.follow_to == 0))[:limit]:
            target_id = user.user_id
            try:
                self.api.create_friendship(id=target_id)
                user.follow_to = 1
                user.date = date
                print "follow:", target_id
            except Exception:
                user.follow_to = 4
                user.date = date
                print "follow error:", target_id
        session.commit()
        session.close()

    def unfollow(self, limit=-1):
        """ unfollow friends who don't follow back """

        date = datetime.datetime.now()
        session = self.Session()
        for user in session.query(User).filter(
                sqlalchemy.and_(User.follow_from == 0, User.follow_to == 1)
                ).order_by(User.date):
            target_id = user.user_id
            try:
                self.api.destroy_friendship(target_id)
                user.follow_to = 2
                user.date = date
                limit -= 1
                print "unfollowed:", target_id
            except Exception:
                print "unfollow error:", target_id
            if limit <= 0:
                break
        session.commit()
        session.close()

    def favorite_replies(self):
        """ favorite all replies """
        statuses = self.api.mentions_timeline()
        for status in statuses:
            if status.favorited:
                continue
            else:
                self.api.create_favorite(id=status.id)
                print "fav:", str(status.id)

    def get_value(self, key, default=None):
        session = self.Session()
        q = session.query(KeyValue).filter(KeyValue.key == key)
        if q.count() == 0:
            return default
        else:
            return q.one().value

    def set_value(self, key, value):
        session = self.Session()
        q = session.query(KeyValue).filter(KeyValue.key == key)
        if q.count() == 0:
            kv = KeyValue(key, value)
            session.add(kv)
        else:
            kv = q.one()
            kv.value = value
        session.commit()
        session.close()

    def get_ids(self, ftype, cursor=-1):
        if ftype == 'friends':
            funcname1 = 'friends'
            funcname2 = '/friends/ids'
            func = self.api.friends_ids
        else:
            funcname1 = 'followers'
            funcname2 = '/followers/ids'
            func = self.api.followers_ids
        ids = []
        while self.api.rate_limit_status()['resources'][funcname1][funcname2]['remaining'] != 0:
            ret = func(cursor=cursor)
            cursor = ret[1][1]
            ids += ret[0]
            if cursor == 0:
                break
        return ids, cursor

    def update_database(self):
        """ update database of following relations """

        session = self.Session()

        # [follow_to] 0: not following, 1: following, 2: removed, 4: cannot follow back
        cursor = long(self.get_value('friends_ids_cursor', -1))
        if cursor == 0:
            cursor = -1
        ids, cursor = self.get_ids('friends', cursor)
        self.set_value('friends_ids_cursor', str(cursor))
        for user_id in ids:
            q = session.query(User).filter(User.user_id == user_id)
            if q.count() == 0:
                user = User(user_id, 1, 0)
                session.add(user)
            else:
                user = q.one()
                user.follow_to = 1
        session.commit()

        # [follow_from] 0: not follower, 1: follower
        cursor = long(self.get_value('followers_ids_cursor', -1))
        if cursor == 0:
            cursor = -1
        ids, cursor = self.get_ids('followers', cursor)
        self.set_value('followers_ids_cursor', str(cursor))
        for user_id in ids:
            q = session.query(User).filter(User.user_id == user_id)
            if q.count() == 0:
                user = User(user_id, 0, 1)
                session.add(user)
            else:
                user = q.one()
                user.follow_from = 1
        session.commit()

        session.close()

    def append_calllist(self, function, interval_min):
        """ append function for run() """
        self.call_list.append((function, interval_min))

        function_name = function.__name__
        session = self.Session()
        try:
            crontime = session.query(CronTime).filter(CronTime.function == function_name).one()
        except sqlalchemy.orm.exc.NoResultFound:
            crontime = CronTime(function_name, datetime.datetime.fromtimestamp(0))
            session.add(crontime)
            session.commit()
        session.close()

    def run(self):
        """ cron job """

        # check lockfile
        if os.path.exists(self.filename_lock):
            return
        else:
            open(self.filename_lock, 'w')

        try:
            for function, interval in self.call_list:
                date = datetime.datetime.now()
                function_name = function.__name__

                session = self.Session()
                crontime = session.query(CronTime).filter(CronTime.function == function_name).one()
                secondsdelta = (calendar.timegm(date.timetuple()) -
                                calendar.timegm(crontime.called.timetuple()))

                print secondsdelta, function_name
                if secondsdelta > interval*60:
                    crontime.called = date
                    session.commit()
                    function()

                session.close()

            # unlock
            os.remove(self.filename_lock)
        except Exception as e:
            open(self.filename_lock, 'w').write(e.message)
