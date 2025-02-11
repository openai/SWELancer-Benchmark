from __future__ import annotations

import logging
from typing import Any, Callable, ClassVar, Self

from pydantic import BaseModel, model_validator

Migration = Callable[[dict[str, Any]], dict[str, Any]]
logger = logging.getLogger(__name__)


class VersionedModel(BaseModel):
    """
    A simple versioned Pydantic model. Supports migrations, defined by overriding _migrations.

    When you make a backwards incompatible change, please increment schema_version and add a migration
    from the previous version to the new version.
    """

    # schema_version must be present when you load the model from its serialized form. If you are
    # transitioning an unversioned model to VersionedModel, you should setdefault this to 0 when
    # loading old data.
    # If schema_version isn't present in `values`, Pydantic will use the latest version. This is
    # necessary because when you create a new instance of a model, Pydantic will call the same
    # validator but without `schema_version` in `values`, and in this case we know we are using
    # the latest schema.
    schema_version: int = 1
    _migrations: ClassVar[dict[int, Migration]] = dict()

    @model_validator(mode="after")
    def _can_migrate_to_current(self) -> Self:
        prevschema_version = self.schema_version - 1
        assert prevschema_version in self._migrations, (
            f"No migration found for schema version {prevschema_version} -> {self.schema_version}"
        )
        return self

    @model_validator(mode="before")
    @classmethod
    def _migrate_schemas(cls, values: dict[str, Any]) -> dict[str, Any]:
        latest_version: int = cls.model_fields["schema_version"].default
        while (current_version := values.get("schema_version", latest_version)) < latest_version:
            migration = cls._migrations.get(current_version)
            if migration is None:
                raise ValueError(f"No migration found for schema version {current_version}")
            logger.info("Migrating %s -> %s", current_version, current_version + 1)
            values = migration(values)
            values["schema_version"] = current_version + 1

        return values
