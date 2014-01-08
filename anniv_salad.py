#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import datetime

import settings
import basebot
import MeCab


def num2kanji(num):
    KNUM = [u"", u"一", u"二", u"三", u"四", u"五", 
            u"六", u"七", u"八", u"九"]
    DIGIT1 = (u"", u"十", u"百", u"千")
    DIGIT2 = (u"", u"万", u"億", u"兆", u"京")
    
    try:
        num = int(num)
    except ValueError:
        raise ValueError("not an integer")
    max = 10000 ** len(DIGIT2) - 1
    if not(0 <= num < max):
        raise ValueError("not in (0-%d)" % max)

    if num == 0: return u"零"

    str_num = str(num)
    knum = []
    for i in xrange(((len(str_num) + 3) / 4)):
        sn = str_num[-1-i*4:-5-i*4:-1]
        if sn != "0000": 
            knum.append(DIGIT2[i] + " ")
            for j, n in enumerate(map(int, sn)):
                if n != 0:
                    knum.append(DIGIT1[j])
                    if not(n == 1 and j):
                        knum.append(KNUM[n])
    knum.reverse()
    return "".join(knum).rstrip()

class AnnivSalad(basebot.BaseBot):
    def __init__(self):
        screen_name = "anniv_salad"
        consumer_key = settings.user_apikey[screen_name]["consumer_key"]
        consumer_secret = settings.user_apikey[screen_name]["consumer_secret"]
        access_token = settings.user_apikey[screen_name]["access_token"]
        access_token_secret = settings.user_apikey[screen_name]["access_token_secret"]
        
        self.append_calllist(self.favorite_replies, 60*11)
        self.append_calllist(self.update_database, 60*13)
        self.append_calllist(self.follow_back, 60*7)
        self.append_calllist(self.follow, 2)
        self.append_calllist(self.post, 60*11)
        
        basebot.BaseBot.__init__(self, screen_name, consumer_key, consumer_secret, access_token, access_token_secret)
    
    # post to twitter
    # repost parosky0's post which is 2 or more favs/RTs
    def post(self):
        statuses = self.api.friends_timeline(count=100)
        for status in statuses:
            text = status.text.replace("\n", " ")
            user = status.author.screen_name.encode('utf-8')
            if len(text)>50:
                continue
            if len(text)<5:
                continue
            if u"ttp" in text:
                continue
            if u"@" in text:
                continue
            if u"(" in text:
                continue
            if u"（" in text:
                continue
            if u")" in text:
                continue
            if u"）" in text:
                continue
            if u"「" in text:
                continue
            if u"｢" in text:
                continue
            noun = self.getLongestNoun(text.encode('utf-8')).decode('utf-8')
            if noun == None:
                continue
            d = datetime.datetime.now()
            post = u"「%s」と @%s が言ったから%s月%s日は%s記念日" % (text, user, num2kanji(d.month), num2kanji(d.day), noun)
            #print post
            self.api.update_status(post)
            break
        print "posted"

    def getLongestNoun(self, text):
        m = MeCab.Tagger("-Ochasen")
        nodes = m.parseToNode(text)
        node = nodes
        nouns = []
        notnoun = True
        while node:
            if "名詞" in node.feature:
                if notnoun:
                    nouns.append("")
                    notnoun = False
                nouns[-1] += node.surface.decode("utf-8")
            else:
                notnoun = True
            node = node.next
        if len(nouns)==0:
            return None
        maxindex = -1
        maxlength = -1
        for i in range(len(nouns)):
            if nouns[i]>maxlength:
                maxindex = i
                maxlength = len(nouns[i])
        if len(nouns[maxindex])<2:
            return None
        # print nouns[maxindex]
        return nouns[maxindex].encode("utf-8")


if __name__ == "__main__":
    os.chdir(os.path.dirname(sys.argv[0]) or '.')
    parosky1 = AnnivSalad()
    parosky1.run()

