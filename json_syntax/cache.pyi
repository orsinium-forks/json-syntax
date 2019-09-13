from typing import Optional

class ForwardAction:
    def __init__(self, call) -> None: ...
    def __repr__(self) -> str: ...

class SimpleCache:
    def __init__(self) -> None: ...
    def in_flight(self, verb, typ) -> Optional[ForwardAction]: ...
    def de_flight(self, verb, typ, forward) -> None: ...
    def complete(self, verb, typ, action) -> None: ...

class ThreadLocalCache:
    def __init__(self) -> None: ...
