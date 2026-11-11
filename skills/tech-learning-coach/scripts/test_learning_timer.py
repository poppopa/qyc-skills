#!/usr/bin/env python3
"""Regression tests for the optional timer; creates no permanent files/services."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import learning_timer as module


class TimerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'timer-state.json'
        self.timer = module.Timer(self.path)

    def tearDown(self):
        self.directory.cleanup()

    def start(self, key='lesson:2', minutes=13):
        return self.timer.change({'action': 'start', 'title': '<b>教学标题</b>',
                                  'lesson_key': key, 'minutes': minutes})

    def test_initial_state_and_thirteen_minutes(self):
        self.assertEqual(self.timer.view()['status'], 'idle')
        state = self.start()
        self.assertEqual(state['duration_seconds'], 780)
        self.assertGreater(state['remaining_seconds'], 779)
        self.assertEqual(state['title'], '<b>教学标题</b>')

    def test_start_is_idempotent(self):
        self.start()
        before = self.timer.state['revision']
        self.start()
        self.assertEqual(self.timer.state['revision'], before)
        self.timer.change({'action': 'pause'})
        self.assertEqual(self.start()['status'], 'paused')

    def test_pause_resume_excludes_pause(self):
        self.start()
        self.timer.active_deadline -= 5
        paused = self.timer.change({'action': 'pause'})
        self.assertAlmostEqual(paused['remaining_seconds'], 775, delta=.1)
        time.sleep(.04)
        self.assertEqual(self.timer.view()['remaining_seconds'], paused['remaining_seconds'])
        resumed = self.timer.change({'action': 'resume'})
        self.assertAlmostEqual(resumed['remaining_seconds'], 775, delta=.1)

    def test_expiry_does_not_restart(self):
        self.start()
        self.timer.active_deadline = time.time() - 1
        self.assertEqual(self.timer.view()['status'], 'finished')
        self.assertEqual(self.start()['status'], 'finished')
        self.assertEqual(self.timer.change({'action': 'reset'})['status'], 'running')

    def test_new_lesson_replaces_and_stop(self):
        self.start()
        self.assertEqual(self.start(key='lesson:3', minutes=8)['duration_seconds'], 480)
        self.assertEqual(self.timer.change({'action': 'stop'})['status'], 'stopped')
        self.assertEqual(self.start(key='lesson:3', minutes=8)['status'], 'stopped')

    def test_validation(self):
        for minutes in [-1, 0, float('nan'), float('inf'), 241, True]:
            with self.assertRaises(ValueError):
                self.start(minutes=minutes)
        with self.assertRaises(ValueError):
            self.timer.change({'action': 'delete'})

    def test_running_restore_and_clock_change(self):
        self.start()
        restored = module.Timer(self.path)
        self.assertGreater(restored.view()['remaining_seconds'], 779)
        with patch.object(module.time, 'time', return_value=time.time() + 3600):
            self.assertEqual(self.timer.view()['status'], 'finished')

    def test_state_is_private(self):
        self.start()
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(self.path.read_text())['lesson_key'], 'lesson:2')

    def test_local_http_and_shutdown(self):
        directory = Path(self.directory.name)
        info = module.connect(directory, True)
        try:
            state = module.request(info, '/api/action', {'action': 'start',
                                   'title': '接口测试', 'lesson_key': 'http:1', 'minutes': 13})
            self.assertEqual(state['duration_seconds'], 780)
            self.assertEqual(module.request(info, '/api/state')['status'], 'running')
            invalid = dict(info, token='invalid-token')
            with self.assertRaises(HTTPError) as caught:
                module.request(invalid, '/api/action', {'action': 'stop'})
            self.assertEqual(caught.exception.code, 403)
            caught.exception.close()
            self.assertEqual(module.request(info, '/api/action', {'action': 'pause'})['status'], 'paused')
        finally:
            module.request(info, '/api/shutdown', {})
            for _ in range(30):
                if not (directory / 'timer-connection.json').exists():
                    break
                time.sleep(.05)
            self.assertFalse((directory / 'timer-connection.json').exists())
            for child in module.CHILDREN:
                child.wait(timeout=3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
