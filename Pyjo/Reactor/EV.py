"""
Pyjo.Reactor.EV - Low-level event reactor with libev support
============================================================
::

    import Pyjo.Reactor.EV

    # Watch if handle becomes readable or writable
    reactor = Pyjo.Reactor.Poll.new()

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

Events
------

:mod:`Pyjo.Reactor.EV` inherits all events from :mod:`Pyjo.Reactor.Select`.

Classes
-------
"""

VERSION = (0, 0, 1)

__version__ = '.'.join(map(str, VERSION))


import Pyjo.Reactor.Select

from Pyjo.Base import lazy

import pyev
import weakref


class Pyjo_Reactor_EV(Pyjo.Reactor.Select.object):

    _loop = lazy(lambda self: pyev.default_loop())

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
        else:
            fd = remove.fileno()
            if fd in self._ios:
                if 'watcher' in self._ios[fd]:
                    self._ios[fd]['watcher'].stop()
                    del self._ios[fd]['watcher']

        super(Pyjo_Reactor_EV, self).remove(remove)

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
                self = weakref.proxy(self)

                watcher = self._loop.io(fd, mode,
                                        lambda watcher, revents:
                                        self._io(watcher, fd, revents))
                watcher.start()
                io['watcher'] = watcher

        return self

    def _io(self, fd, w, revents):
        io = self._ios[fd]
        if revents & pyev.EV_READ:
            self._sandbox(io['cb'], 'Read', False)
        if revents & pyev.EV_WRITE:
            self._sandbox(io['cb'], 'Write', True)

    def _timer(self, cb, recurring, after):
        if recurring and not after:
            after = 0.0001

        tid = super(Pyjo_Reactor_EV, self)._timer(cb, 0, 0)
        self = weakref.proxy(self)

        def timer_cb(self, tid, watcher, revents):
            timer = self._timers[tid]
            if not recurring:
                self.remove(tid)
            self._sandbox(timer['cb'], 'Timer {0}'.format(tid))

        watcher = self._loop.timer(after, after,
                                   lambda watcher, revents:
                                   timer_cb(self, tid, watcher, revents))
        watcher.start()
        self._timers[tid]['watcher'] = watcher

        return tid


new = Pyjo_Reactor_EV.new
object = Pyjo_Reactor_EV  # @ReservedAssignment
