import Pyjo.Reactor.Select


# Dummy reactor
class TestReactor(Pyjo.Reactor.Select.object):
    pass


def new():
    return TestReactor()
