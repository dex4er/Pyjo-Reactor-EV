"""
Pyjo.Reactor.EV - Low-level event reactor with pyev support
===========================================================
::

    import Pyjo.Reactor.EV

    # Watch if handle becomes readable or writable
    reactor = Pyjo.Reactor.EV.new()

    def io_cb(reactor, writable):
        if writable:
            print('Handle is writable')
        else:
            print('Handle is readable')

    reactor.io(io_cb, handle)

    # Change to watching only if handle becomes writable
    reactor.watch(handle, read=False, write=True)

    # Add a timer
    def timer_cb(reactor):
        reactor.remove(handle)
        print('Timeout!')

    reactor.timer(timer_cb, 15)

    # Start reactor if necessary
    if not reactor.is_running:
        reactor.start()

:mod:`Pyjo.Reactor.EV` is a low-level event reactor based on :mod:`pyev`.

:mod:`Pyjo.Reactor.EV` will be used as the default backend for
:mod:`Pyjo.IOLoop` if it is loaded before any module using the loop or if
the ``PYJO_REACTOR`` environment variable is set to ``Pyjo.Reactor.EV`` value.

Debugging
---------

You can set the ``PYJO_REACTOR_DEBUG`` environment variable to get some
advanced diagnostics information printed to ``stderr``. ::

    PYJO_REACTOR_DEBUG=1

You can set the ``PYJO_REACTOR_DIE`` environment variable to make reactor die if task
dies with exception. ::

    PYJO_REACTOR_DIE=1

Events
------

:mod:`Pyjo.Reactor.EV` inherits all events from :mod:`Pyjo.Reactor.Select`.

Classes
-------
"""

import Pyjo.Reactor.Select

import pyev
import weakref

from Pyjo.Util import getenv, setenv


setenv('PYJO_REACTOR', getenv('PYJO_REACTOR', 'Pyjo.Reactor.EV'))


class Pyjo_Reactor_EV(Pyjo.Reactor.Select.object):
    """
    :mod:`Pyjo.Reactor.EV` inherits all attributes and methods from
    :mod:`Pyjo.Reactor.Select` and implements the following new ones.
    """

    def __init__(self, **kwargs):
        super(Pyjo_Reactor_EV, self).__init__(**kwargs)

        self._loop = pyev.Loop()

    def again(self, tid):
        """::

            reactor.again(tid)

        Restart active timer.
        """
        self._timers[tid]['watcher'].reset()

    @property
    def is_running(self):
        """::

            boolean = reactor.is_running

        Check if reactor is running.
        """
        return self._loop.depth

    def one_tick(self):
        """::

            reactor.one_tick()

        Run reactor until an event occurs. Note that this method can recurse back into
        the reactor, so you need to be careful. Meant to be overloaded in a subclass.
        """
        self._loop.start(pyev.EVRUN_ONCE)

    def recurring(self, cb, after):
        """::

            tid = reactor.recurring(cb, 0.25)

        Create a new recurring timer, invoking the callback repeatedly after a given
        amount of time in seconds.
        """
        return self._timer(cb, True, after)

    def remove(self, remove):
        """::

            boolean = reactor.remove(handle)
            boolean = reactor.remove(tid)

        Remove handle or timer.
        """
        if isinstance(remove, str):
            if remove in self._timers:
                if 'watcher' in self._timers[remove]:
                    self._timers[remove]['watcher'].stop()
                    del self._timers[remove]['watcher']

        elif remove is not None:
            fd = remove.fileno()
            if fd in self._ios:
                if 'watcher' in self._ios[fd]:
                    self._ios[fd]['watcher'].stop()
                    del self._ios[fd]['watcher']

        super(Pyjo_Reactor_EV, self).remove(remove)

    def reset(self):
        """::

            reactor.reset()

        Remove all handles and timers.
        """
        for fd in self._ios:
            self._ios[fd]['watcher'].stop()

        for tid in self._timers:
            self._timers[tid]['watcher'].stop()

        super(Pyjo_Reactor_EV, self).reset()

    def start(self):
        """::

            reactor.start()

        Start watching for I/O and timer events, this will block until :meth:`stop` is
        called.
        """
        self._loop.start()

    def stop(self):
        """::

            reactor.stop()

        Stop watching for I/O and timer events.
        """
        self._loop.stop(pyev.EVBREAK_ALL)

    def timer(self, cb, after):
        """::

            tid = reactor.timer(cb, 0.5)

        Create a new timer, invoking the callback after a given amount of time in
        seconds.
        """
        return self._timer(cb, False, after)

    def watch(self, handle, read, write):
        """::

            reactor = reactor.watch(handle, read, write)

        Change I/O events to watch handle for with true and false values. Meant to be
        overloaded in a subclass. Note that this method requires an active I/O
        watcher.
        """
        mode = 0

        if read:
            mode |= pyev.EV_READ

        if write:
            mode |= pyev.EV_WRITE

        fd = handle.fileno()

        if fd not in self._ios:
            self._ios[fd] = {}

        io = self._ios[fd]

        if mode == 0:
            if 'watcher' in io:
                io['watcher'].stop()
                del io['watcher']
        else:
            if 'watcher' in io:
                w = io['watcher']
                w.stop()
                w.set(fd, mode)  # TODO Exception pyev.Error: 'cannot set a watcher while it is active'
                w.start()
            else:
                reactor = weakref.proxy(self)

                def watcher_cb(watcher, revents):
                    if dir(reactor):
                        reactor._io(fd, watcher, revents)

                watcher = self._loop.io(fd, mode, watcher_cb)
                watcher.start()
                io['watcher'] = watcher

        return self

    def _io(self, fd, w, revents):
        if fd in self._ios:
            io = self._ios[fd]
            if revents & pyev.EV_READ:
                self._sandbox(io['cb'], 'Read', False)
            if revents & pyev.EV_WRITE:
                self._sandbox(io['cb'], 'Write', True)

    def _timer(self, cb, recurring, after):
        if recurring and not after:
            after = 0.000001  # 1 us

        tid = super(Pyjo_Reactor_EV, self)._timer(cb, 0, 0)
        reactor = weakref.proxy(self)

        def timer_cb(self, tid, watcher, revents):
            timer = reactor._timers[tid]
            if not recurring:
                reactor.remove(tid)
            reactor._sandbox(timer['cb'], 'Timer {0}'.format(tid))

        def watcher_cb(watcher, revents):
            if dir(reactor):
                timer_cb(reactor, tid, watcher, revents)

        watcher = self._loop.timer(after, after, watcher_cb)
        watcher.start()
        self._timers[tid]['watcher'] = watcher

        return tid


new = Pyjo_Reactor_EV.new
object = Pyjo_Reactor_EV
