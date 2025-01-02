import json
from typing import Any

from temporalio import workflow
from temporalio.api.common.v1 import Payload
from temporalio.converter import CompositePayloadConverter, DefaultPayloadConverter, JSONPlainPayloadConverter

with workflow.unsafe.imports_passed_through():
    from pydantic.json import pydantic_encoder


class PydanticJSONPayloadConverter(JSONPlainPayloadConverter):
    """Pydantic JSON payload converter.

    This extends the :py:class:`JSONPlainPayloadConverter` to override
    :py:meth:`to_payload` using the Pydantic encoder.
    """

    def to_payload(self: "PydanticJSONPayloadConverter", value: Any) -> Payload | None:
        """Convert all values with Pydantic encoder or fail.

        Like the base class, we fail if we cannot convert. This payload
        converter is expected to be the last in the chain, so it can fail if
        unable to convert.
        """
        # We let JSON conversion errors be thrown to caller
        return Payload(
            metadata={"encoding": self.encoding.encode()},
            data=json.dumps(value, separators=(",", ":"), sort_keys=True, default=pydantic_encoder).encode(),
        )


class PydanticPayloadConverter(CompositePayloadConverter):
    """Payload converter that replaces Temporal JSON conversion with Pydantic
    JSON conversion.
    """

    def __init__(self: "PydanticPayloadConverter") -> None:
        super().__init__(
            *(
                c if not isinstance(c, JSONPlainPayloadConverter) else PydanticJSONPayloadConverter()
                for c in DefaultPayloadConverter.default_encoding_payload_converters
            ),
        )
