# pyre-strict

from .helpers import (
    JSON2PY,
    PY2JSON,
    INSP_JSON,
    INSP_PY,
    PATTERN,
    SENTINEL,
    has_origin,
    identity,
    is_attrs_field_required,
    issub_safe,
    resolve_fwd_ref,
)
from .action_v1 import (
    check_dict,
    check_isinst,
    check_tuple_as_list,
    convert_attrs_to_dict,
    convert_dict_to_attrs,
    convert_tuple_as_list,
)
from . import pattern as pat

from functools import partial


def attrs_classes(
    verb,
    typ,
    ctx,
    pre_hook="__json_pre_decode__",
    post_hook="__json_post_encode__",
    check="__json_check__",
):
    """
    Handle an ``@attr.s`` or ``@dataclass`` decorated class.

    This rule also implements several hooks to handle complex cases, especially to
    manage backwards compatibility. Hooks should be resilient against invalid data,
    and should not mutate their inputs.

    `__json_pre_decode__` is used by decoders constructed by `RuleSet.json_to_python`.
    It will be called before decoding with the JSON object and may adjust them to fit
    the expected structure, which must be a `dict` with the necessary fields.

    The checker generated by `inspect_json` will also call `__json_pre_decode__` before
    inspecting the value generated.

    `__json_post_encode__` is used by encoders constructed by `RuleSet.python_to_json`.
    It will be called after encoding with the JSON object and may adjust it as
    necessary.

    `__json_check__` may be used to completely override the `inspect_json` check generated
    for this class.
    """
    if verb not in (JSON2PY, PY2JSON, INSP_PY, INSP_JSON, PATTERN):
        return
    try:
        fields = typ.__attrs_attrs__
    except AttributeError:
        try:
            fields = typ.__dataclass_fields__
        except AttributeError:
            return
        else:
            fields = fields.values()

    if verb == INSP_PY:
        return partial(check_isinst, typ=typ)

    inner_map = []
    for field in fields:
        if field.init:
            tup = (
                field.name,
                ctx.lookup(
                    verb=verb, typ=resolve_fwd_ref(field.type, typ), accept_missing=True
                ),
            )
            if verb == PY2JSON:
                tup += (field.default,)
            elif verb in (INSP_JSON, PATTERN):
                tup += (is_attrs_field_required(field),)
            inner_map.append(tup)

    if verb == JSON2PY:
        pre_hook_method = getattr(typ, pre_hook, identity)
        return partial(
            convert_dict_to_attrs,
            pre_hook=pre_hook_method,
            inner_map=tuple(inner_map),
            con=typ,
        )
    elif verb == PY2JSON:
        post_hook = post_hook if hasattr(typ, post_hook) else None
        return partial(
            convert_attrs_to_dict, post_hook=post_hook, inner_map=tuple(inner_map)
        )
    elif verb == INSP_JSON:
        check = getattr(typ, check, None)
        if check:
            return check
        pre_hook_method = getattr(typ, pre_hook, identity)
        return partial(check_dict, inner_map=inner_map, pre_hook=pre_hook_method)
    elif verb == PATTERN:
        return pat.Object.exact(
            (pat.String.exact(name), inner or pat.Unkown)
            for name, inner, req in inner_map
            if req
        )


def named_tuples(verb, typ, ctx):
    """
    Handle a ``NamedTuple(name, [('field', type), ('field', type)])`` type.

    Also handles a ``collections.namedtuple`` if you have a fallback handler.
    """
    if verb not in (JSON2PY, PY2JSON, INSP_PY, INSP_JSON, PATTERN) or not issub_safe(
        typ, tuple
    ):
        return
    try:
        fields = typ._field_types
    except AttributeError:
        try:
            fields = typ._fields
        except AttributeError:
            return
        fields = [(name, None) for name in fields]
    else:
        fields = fields.items()
    if verb == INSP_PY:
        return partial(check_isinst, typ=typ)

    defaults = {}
    defaults.update(getattr(typ, "_fields_defaults", ()))
    defaults.update(getattr(typ, "_field_defaults", ()))
    inner_map = []
    for name, inner in fields:
        tup = (
            name,
            ctx.lookup(verb=verb, typ=resolve_fwd_ref(inner, typ), accept_missing=True),
        )
        if verb == PY2JSON:
            tup += (defaults.get(name, SENTINEL),)
        elif verb in (INSP_JSON, PATTERN):
            tup += (name not in defaults,)
        inner_map.append(tup)

    if verb == JSON2PY:
        return partial(
            convert_dict_to_attrs,
            pre_hook=identity,
            inner_map=tuple(inner_map),
            con=typ,
        )
    elif verb == PY2JSON:
        return partial(
            convert_attrs_to_dict, post_hook=None, inner_map=tuple(inner_map)
        )
    elif verb == INSP_JSON:
        return partial(check_dict, pre_hook=identity, inner_map=tuple(inner_map))
    elif verb == PATTERN:
        return pat.Object.exact(
            (pat.String.exact(name), inner) for name, inner, req in inner_map if req
        )


def tuples(verb, typ, ctx):
    """
    Handle a ``Tuple[type, type, type]`` product type. Use a ``NamedTuple`` if you don't
    want a list.
    """
    if verb not in (JSON2PY, PY2JSON, INSP_PY, INSP_JSON, PATTERN) or not has_origin(
        typ, tuple
    ):
        return
    args = typ.__args__
    if Ellipsis in args:
        # This is a homogeneous tuple, use the lists rule.
        return
    inner = [ctx.lookup(verb=verb, typ=arg) for arg in args]
    if verb == JSON2PY:
        return partial(convert_tuple_as_list, inner=inner, con=tuple)
    elif verb == PY2JSON:
        return partial(convert_tuple_as_list, inner=inner, con=list)
    elif verb == INSP_PY:
        return partial(check_tuple_as_list, inner=inner, con=tuple)
    elif verb == INSP_JSON:
        return partial(check_tuple_as_list, inner=inner, con=list)
    elif verb == PATTERN:
        return pat.Array.exact(inner)
