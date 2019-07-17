from typing import NamedTuple, Type
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.param import Param
from webapp.apps.comp.parser import Parser


class IOClasses(NamedTuple):
    displayer: Displayer
    Param: Type[Param]
    Parser: Type[Parser]


def get_ioutils(project, **kwargs):
    return IOClasses(
        displayer=kwargs.get("Displayer", Displayer)(
            project, kwargs.get("Param", Param)
        ),
        Param=kwargs.get("Param", Param),
        Parser=kwargs.get("Parser", Parser),
    )
