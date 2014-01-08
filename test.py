#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import parosky1

class TestParosky1(unittest.TestCase):
    def test_post(self):
        self.bot = parosky1.Parosky1()
        testmessage = 'test'
        status = self.bot.api.update_status(testmessage)
        status.destroy()
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
