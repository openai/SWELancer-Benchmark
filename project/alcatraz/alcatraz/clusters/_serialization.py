"""
Alcatraz cluster objects support JSON serialization, which will preserve their state so they
can be loaded later to connect to the same remote instance.

To serialize: config.model_dump_json()
To deserialize: config = serializable_adapter.validate_json(serialized)

Deserialization handles type lookup automatically, so e.g. a serialized SwarmConfig will
be deserialized as a SwarmConfig object.

Serialization is NOT guaranteed to be stable across commits. Do not save it anywhere persistent
and expect it to be loadable in future versions of Alcatraz.
"""

import importlib
from typing import Any, Self

from pydantic import BaseModel, model_serializer
from pydantic_core.core_schema import SerializationInfo, SerializerFunctionWrapHandler


class SerializableBaseModel(BaseModel):
    """
    A model which, when serialized, saves the class and module name of the
    current instance to secret fields. This allows the instance to be
    deserialized later without knowing the class in advance.

    Copied from nanoeval as there's no good place to put it without duplication.
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
        # Extract class info
        class_name: str = data["__class_name__"]
        module_name: str = data["__module_name__"]

        # Dynamically import the module and get the class
        module = importlib.import_module(module_name)
        klass = getattr(module, class_name)

        if not issubclass(klass, cls):
            raise ValueError(f"Deserialized class {class_name} is not a subclass of {cls}.")

        # Create an instance of the class with the remaining data
        return klass.model_validate(data)
