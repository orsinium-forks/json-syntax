import attr
from collections import namedtuple


@attr.s
class Flat1:
    a = attr.ib(type=int)
    b = attr.ib("default", type=str)


flat_types = [Flat1]


class Hooks:
    @classmethod
    def __json_pre_decode__(cls, value):
        if isinstance(value, list):
            value = {"a": value[0], "b": value[1]}
        return value

    @classmethod
    def __json_check__(cls, value):
        return value.get("_type_") == "Hook"

    def __json_post_encode__(cls, value):
        return dict(value, _type_="Hook")


@attr.s
class Hook1(Hooks):
    a = attr.ib(type=int)
    b = attr.ib("default", type=str)


hook_types = [Hook1]
Named1 = namedtuple("Named1", ["a", "b"])
try:
    Named2 = namedtuple("Named2", ["a", "b"], defaults=["default"])
except TypeError:
    Named2 = None
Named3 = None
