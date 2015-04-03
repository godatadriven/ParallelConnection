from itertools import chain
from threading import Thread


class ParallelConnection(object):
    """
        This class manages multiple database connections, handles the parallel access to it, and
        hides the complexity this entails. The execution of queries is distributed by running it
        for each connection in parallel. The result (as retrieved by fetchall() and fetchone())
        is the union of the parallelized query results from each connection.
    """

    def __init__(self, connections):
        self.connections = connections
        self.cursors = None

    def cursor(self, *args, **kwargs):
        self.cursors = [connection.cursor(*args, **kwargs)
                        for connection in self.connections]
        return self

    def execute(self, query, tuple_args=None, fetchnone=False):
        self._do_parallel(lambda i, c: c.execute(query, tuple_args))

    def fetchone(self):
        results = [None] * len(self.cursors)
        def do_work(index, cursor):
            results[index] = cursor.fetchone()
        self._do_parallel(do_work)

        results_values = filter(is_not_none, results)
        if results_values:
            return list(chain(results_values))[0]

    def fetchall(self):
        results = [None] * len(self.cursors)
        def do_work(index, cursor):
            results[index] = cursor.fetchall()
        self._do_parallel(do_work)

        return list(chain(*results))

    def mogrify(self, q, *args, **kwargs):
        return self.cursors[0].mogrify(q, *args, **kwargs)

    def commit(self):
        for connection in self.connections:
            connection.commit()

    def close(self):
        for cursor in self.cursors:
            cursor.close()
        self.cursors = None

    def putconn(self, pools):
        for p, c in zip(pools, self.connections):
            t = Thread(target=lambda p=p, c=c: p.putconn(c))
            t.start()

    def _do_parallel(self, target):
        threads = []
        for i, c in enumerate(self.cursors):
            t = Thread(target=lambda i=i, c=c: target(i, c))
            t.setDaemon(True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()


def is_not_none(dict_or_tuple):
    if dict_or_tuple:
        if isinstance(dict_or_tuple, dict):
            if all(r is None for r in dict_or_tuple.itervalues()):
                return False
        else:
            if all(r is None for r in dict_or_tuple):
                return False
        return True
    return False
