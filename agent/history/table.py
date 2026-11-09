"""The narrow table port history needs, with a DynamoDB adapter and an in-memory double.

Only three write shapes exist: create-if-absent, complete-if-open and nothing
else. History never issues an unconditional put, update or delete.
"""

from __future__ import annotations

import copy
import math
from decimal import Decimal
from typing import Any, Callable, Protocol

from history.identity import json_safe


class ConditionFailed(Exception):
    """A conditional write lost; ``existing`` is the stored item, if any."""

    def __init__(self, existing: dict[str, Any] | None):
        super().__init__("conditional write refused")
        self.existing = existing


class HistoryTable(Protocol):
    name: str
    key_name: str

    def put_if_absent(self, item: dict[str, Any]) -> None: ...

    def complete_if_open(
        self,
        key_value: str,
        fields: dict[str, Any],
        *,
        open_statuses: tuple[str, ...],
        guard_attribute: str,
    ) -> None: ...

    def get(self, key_value: str) -> dict[str, Any] | None: ...

    def scan_page(
        self, limit: int, start_key: dict[str, Any] | None
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]: ...


def to_dynamo(value: Any) -> Any:
    """Prepare plain JSON values for DynamoDB (floats become exact decimal text)."""
    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return str(value)
        return Decimal(repr(value))
    if isinstance(value, dict):
        return {str(k): to_dynamo(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_dynamo(v) for v in value]
    return str(value)


class DynamoDBTable:
    """Adapter over a low-level boto3 DynamoDB client."""

    def __init__(self, client: Any, name: str, key_name: str):
        from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

        self.client = client
        self.name = name
        self.key_name = key_name
        self._ser = TypeSerializer()
        self._de = TypeDeserializer()

    def _encode(self, item: dict[str, Any]) -> dict[str, Any]:
        return {k: self._ser.serialize(to_dynamo(v)) for k, v in item.items()}

    def _decode(self, item: dict[str, Any] | None) -> dict[str, Any] | None:
        if item is None:
            return None
        return json_safe({k: self._de.deserialize(v) for k, v in item.items()})

    def _key(self, key_value: str) -> dict[str, Any]:
        return {self.key_name: {"S": key_value}}

    def _refused(self, err: Exception, key_value: str) -> ConditionFailed | None:
        response = getattr(err, "response", {}) or {}
        if response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            return None
        existing = response.get("Item")
        if existing is not None:
            return ConditionFailed(self._decode(existing))
        return ConditionFailed(self.get(key_value))

    def put_if_absent(self, item: dict[str, Any]) -> None:
        from botocore.exceptions import ClientError

        try:
            self.client.put_item(
                TableName=self.name,
                Item=self._encode(item),
                ConditionExpression="attribute_not_exists(#k)",
                ExpressionAttributeNames={"#k": self.key_name},
                ReturnValuesOnConditionCheckFailure="ALL_OLD",
            )
        except ClientError as err:
            refused = self._refused(err, item[self.key_name])
            if refused is None:
                raise
            raise refused from err

    def complete_if_open(
        self,
        key_value: str,
        fields: dict[str, Any],
        *,
        open_statuses: tuple[str, ...],
        guard_attribute: str,
    ) -> None:
        from botocore.exceptions import ClientError

        names: dict[str, str] = {"#k": self.key_name, "#status": "status", "#g": guard_attribute}
        values: dict[str, Any] = {}
        sets = []
        for i, (field, value) in enumerate(sorted(fields.items())):
            names[f"#f{i}"] = field
            values[f":v{i}"] = self._ser.serialize(to_dynamo(value))
            sets.append(f"#f{i} = :v{i}")
        status_refs = []
        for i, status in enumerate(open_statuses):
            values[f":open{i}"] = {"S": status}
            status_refs.append(f":open{i}")
        try:
            self.client.update_item(
                TableName=self.name,
                Key=self._key(key_value),
                UpdateExpression="SET " + ", ".join(sets),
                ConditionExpression=(
                    f"attribute_exists(#k) AND #status IN ({', '.join(status_refs)}) "
                    "AND attribute_not_exists(#g)"
                ),
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values,
                ReturnValuesOnConditionCheckFailure="ALL_OLD",
            )
        except ClientError as err:
            refused = self._refused(err, key_value)
            if refused is None:
                raise
            raise refused from err

    def get(self, key_value: str) -> dict[str, Any] | None:
        out = self.client.get_item(
            TableName=self.name, Key=self._key(key_value), ConsistentRead=True
        )
        return self._decode(out.get("Item"))

    def scan_page(
        self, limit: int, start_key: dict[str, Any] | None
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        request: dict[str, Any] = {"TableName": self.name, "Limit": limit}
        if start_key is not None:
            request["ExclusiveStartKey"] = self._encode(start_key)
        out = self.client.scan(**request)
        items = [self._decode(item) or {} for item in out.get("Items", [])]
        last = out.get("LastEvaluatedKey")
        return items, self._decode(last) if last else None


class MemoryTable:
    """In-memory double with DynamoDB's conditional-write semantics for these shapes.

    It is local test evidence, not evidence about DynamoDB itself. Items are
    stored as DynamoDB would return them (floats round-trip through Decimal).
    """

    def __init__(self, name: str, key_name: str):
        self.name = name
        self.key_name = key_name
        self.items: dict[str, dict[str, Any]] = {}
        self.before_write: Callable[[str, dict[str, Any]], None] | None = None

    @staticmethod
    def _stored(item: dict[str, Any]) -> dict[str, Any]:
        return json_safe(to_dynamo(copy.deepcopy(item)))

    def seed(self, item: dict[str, Any]) -> None:
        """Write a pre-existing (legacy or tampered) item outside history's write rules."""
        self.items[item[self.key_name]] = self._stored(item)

    def put_if_absent(self, item: dict[str, Any]) -> None:
        if self.before_write is not None:
            self.before_write("put", item)
        key = item[self.key_name]
        if key in self.items:
            raise ConditionFailed(copy.deepcopy(self.items[key]))
        self.items[key] = self._stored(item)

    def complete_if_open(
        self,
        key_value: str,
        fields: dict[str, Any],
        *,
        open_statuses: tuple[str, ...],
        guard_attribute: str,
    ) -> None:
        if self.before_write is not None:
            self.before_write("complete", {self.key_name: key_value, **fields})
        current = self.items.get(key_value)
        if (
            current is None
            or current.get("status") not in open_statuses
            or guard_attribute in current
        ):
            raise ConditionFailed(copy.deepcopy(current) if current else None)
        current.update(self._stored(fields))

    def get(self, key_value: str) -> dict[str, Any] | None:
        item = self.items.get(key_value)
        return copy.deepcopy(item) if item is not None else None

    def scan_page(
        self, limit: int, start_key: dict[str, Any] | None
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        keys = sorted(self.items)
        if start_key is not None:
            keys = [k for k in keys if k > start_key[self.key_name]]
        page = keys[:limit]
        last = {self.key_name: page[-1]} if len(page) == limit and len(keys) > limit else None
        return [copy.deepcopy(self.items[k]) for k in page], last
