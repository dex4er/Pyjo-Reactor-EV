=======================================
Pyjo-Reactor-EV |release| documentation
=======================================

Low level event reactor for Pyjoyment with pyev support.


Pyjoyment
=========

An asynchronous, event driver web framework for the Python programming language.

Pyjoyment provides own reactor which handles I/O and timer events in its own
main event loop but it supports other loops, ie. EV.

See http://www.pyjoyment.net/


pyev
====

Python libev interface.

``libev`` is a high-performance event loop, supporting eight event types (I/O,
real time timers, wall clock timers, signals, child status changes, idle, check
and prepare handlers). ``libev`` supports ``select``, ``poll``, the
Linux-specific ``epoll``, the BSD-specific ``kqueue`` and the Solaris-specific
event port mechanisms for file descriptor events (I/O).

See https://pythonhosted.org/pyev/ and http://libev.schmorp.de/


Contents:

.. toctree::
    :maxdepth: 2

    installation
    api/index
    authors
    license
