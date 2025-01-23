from __future__ import annotations

import importlib
from typing import Any, Self

from pydantic import BaseModel, model_serializer
from pydantic_core.core_schema import SerializationInfo, SerializerFunctionWrapHandler


class SerializableBaseModel(BaseModel):
    """
    A model which, when serialized, saves the class and module name of the
    current instance to secret fields. This allows the instance to be
    deserialized later without knowing the class in advance.

    This should only be used with TRUSTED DATA, as the deserializer can
    import any class.

    Serialize: `d.model_dump`
    Deserialize: Class.deserialize(dict)`
    """

    @model_serializer(when_used="always", mode="wrap")
    def _save_class_and_module_fields(
        self, serializer: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> dict[str, Any]:
        del info
        data: dict[str, Any] = serializer(self)
        data["__class_name__"] = self.__class__.__name__
        data["__module_name__"] = self.__module__
        return data

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> Self:
        # Do not modify the input!
        data = data.copy()
        # Extract class info
        class_name = data.pop("__class_name__")
        module_name = data.pop("__module_name__")

        # Dynamically import the module and get the class
        module = importlib.import_module(module_name)
        klass = getattr(module, class_name)

        if not issubclass(klass, cls):
            raise ValueError(f"Deserialized class {class_name} is not a subclass of {cls}.")

        # Create an instance of the class with the remaining data
        return klass.model_validate(data)
