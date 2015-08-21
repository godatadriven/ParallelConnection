ParallelConnection
==================

This class manages multiple database connections, handles the parallel
access to it, and hides the complexity this entails. The execution of
queries is distributed by running it for each connection in parallel.
The result (as retrieved by fetchall() and fetchone()) is the union of
the parallelized query results from each connection.

The use case we had in mind when we created this class was having
sharded tables (distributed across n database instances) that we needed
to query concurrently and merging the results.

See below for an architecture overview for possible inspiration.

Usage
-----

The package is in principle database independent, as long as you expect
a connection object to respond to (part of) these methods:

.. code:: python

    cursor
    cursor.execute
    cursor.fetchone
    cursor.fetchall
    cursor.mogrify
    cursor.commit
    cursor.close
    putconn

To use in its simplest form, do (example using psycopg2 and assuming
that dsns is a list containing your databases' connection strings)

.. code:: python

    n = 20  # maximum connections per pool
    pools = [psycopg2.ThreadedConnectionPool(1, n, dsn=d) for d in dsns]
    connections = [p.getconn() for p in pools]
    pdb = ParallelConnection(connections)

The ``pdb`` object works for the rest like a normal, single, database
connection object, but it merges results return by each database. You
can therefore use it like so:

.. code:: python

    c = pdb.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("SELECT * FROM my_shrd_tbl WHERE shrd_column = 1543", parameters)
    results = c.fetchall()
    c.close

Results will fetch everything from all database. In case your query has
a where in the sharded column (``shrd_column``) the results from all but
one databases will be empty. This is fine, as the package handles it for
you. When it gets more interesting is a query like

.. code:: python

    c = pdb.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("SELECT * FROM my_shrd_tbl WHERE not_shrd_column = 543", parameters)
    results = c.fetchall()
    c.close

In this case the query does *not* have a ``WHERE`` on a sharded column,
so the package will fetch results from each database and merge them. Why
that may be of interest for you, will be shown below.

If you are executing a query on a non-sharded table you should use a
normal connection object.

Architectural motivation
------------------------

We found ourselves having long running queries that where aggregating
records on a particular column (let's call it ``shrd_column``). To
reduce the run-time we decided to split only the table(s) containing
``shrd_column`` between multiple databases, and have each database have
a copy of all non-sharded tables.

Then each query grouping on ``shrd_column`` can be basically be executed
independently in each databases. The results still need to be merged
though, so that's why we build this package (we call it package even if
Niels insists on calling it "just a class").

FAQ
---

**Q.** Why don't you use things as
`pg\_shard <https://github.com/citusdata/pg_shard>`__?

**A.** Because pg\_shard doesn't handle ``JOIN`` on the distributed
query, which we want to do. Our package has the additional advantage
that all the databases are completely unaware of each other. It all
happens on the application layer and on the ingestion layer.

--------------

**Q.** What about if a machine goes down, etc.?

**A.** Just use two machines with a load balancer in front of them.

--------------

**Q.** What about ``INSERT``?

**A.** Yeah, we don't do that sort of things (it's read-only application
for explorative purposes). But feel to see if it works, and fix it plus
submitting a PR if it doesn't.

--------------

**Q.** What about how to shard the data? This package does nothing,
Niels is right!

**A.** We trust you are savvy enough to do that by yourself before
ingestion. We could help you with that though, just drop
`us <mailto:signal@godatadriven.com>`__ a line.

--------------

**Q.** I want to know more!

**A.** That's technically not a question, but you can begin by watching
Niels present the project at PyData Paris 2015. It's on
`Youtube <https://www.youtube.com/watch?v=g0eNQSzIbpQ>`__.
