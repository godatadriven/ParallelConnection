from unittest import TestCase
from parallel_connection import ParallelConnection

class Mock(object):
    def __init__(self):
        self.calls = []

    def register_call(self, name, args, kwargs):
        self.calls.append((name, args, kwargs))

    def assert_called_once_with(self, name, *args, **kwargs):
        nr = 0
        for this_name, this_args, this_kwargs in self.calls:
            if name == this_name and args == this_args and kwargs == this_kwargs:
                nr += 1

        assert nr == 1, nr

class FakeCursor(Mock):

    def execute(self, *args, **kwargs):
        self.register_call('execute', args, kwargs)

    def fetchone(self, *args, **kwargs):
        self.register_call('fetchone', args, kwargs)
        return {1:'a', 2 :'b'}

    def fetchall(self, *args, **kwargs):
        self.register_call('fetchall', args, kwargs)
        return [{1:'a', 2:'b'}]

    def close(self, *args, **kwargs):
        self.register_call('close', args, kwargs)

    def mogrify(self, *args, **kwargs):
        self.register_call('mogrify', args, kwargs)

class FakeConnection(Mock):
    def cursor(self, *args, **kwargs):
        self.register_call('cursor', args, kwargs)
        return FakeCursor()

    def commit(self, *args, **kwargs):
        self.register_call('commit', args, kwargs)

class PCTestCase(TestCase):

    def setUp(self):
        self.con1 = FakeConnection()
        self.con2 = FakeConnection()
        self.pc = ParallelConnection([self.con1, self.con2])

    def test_cursor(self):
        self.pc.cursor('a', b='c')

        self.con1.assert_called_once_with('cursor', 'a', b='c')
        self.con2.assert_called_once_with('cursor', 'a', b='c')

    def test_execute(self):
        self.pc.cursor()
        self.pc.execute("hello world", 42)

        for cursor in self.pc.cursors:
            cursor.assert_called_once_with("execute", "hello world", 42)

    def test_fetchone(self):
        self.pc.cursor()
        self.pc.execute("hello world", 42)
        results = self.pc.fetchone()

        self.assertEqual(results, {1:'a', 2 :'b'})

        for cursor in self.pc.cursors:
            cursor.assert_called_once_with("execute", "hello world", 42)
            cursor.assert_called_once_with("fetchone")

    def test_fetchall(self):
        self.pc.cursor()
        self.pc.execute("hello world", 42)
        results = self.pc.fetchall()

        self.assertEqual(results, [{1:'a', 2:'b'}, {1:'a', 2:'b'}])

        for cursor in self.pc.cursors:
            cursor.assert_called_once_with("execute", "hello world", 42)
            cursor.assert_called_once_with("fetchall")

    def test_commit(self):
        self.pc.commit()
        self.con1.assert_called_once_with('commit')
        self.con2.assert_called_once_with('commit')

    def test_close(self):
        self.pc.cursor()
        cursors = self.pc.cursors[:]
        self.pc.close()

        for cursor in cursors:
            cursor.assert_called_once_with('close')

        self.assertIsNone(self.pc.cursors)

    def test_mogrify(self):
        self.pc.cursor()
        self.pc.mogrify("hello world")
        self.pc.cursors[0].assert_called_once_with('mogrify', "hello world")
