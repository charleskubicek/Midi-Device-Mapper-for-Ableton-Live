from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field, model_validator


class CustomEncoderEntry(BaseModel):
    number: int
    name: Optional[str] = None
    display: Optional[str] = None
    button: Optional[str] = None


class GroupMember(BaseModel):
    number: int
    name: Optional[str] = None
    display: Optional[str] = None
    activeWhen: List[int]


class GroupedEncoderEntry(BaseModel):
    controlledBy: str
    group: List[GroupMember]
    name: Optional[str] = None

    @model_validator(mode='after')
    def _check_active_when(self):
        seen: dict = {}
        for m in self.group:
            for v in m.activeWhen:
                if v in seen:
                    raise ValueError(
                        f"group controlledBy={self.controlledBy!r}: selector value {v} "
                        f"appears in activeWhen of both number={seen[v]} and number={m.number}"
                    )
                seen[v] = m.number
        if not self.group:
            raise ValueError(f"group controlledBy={self.controlledBy!r} has no members")
        return self


EncoderEntry = Union[GroupedEncoderEntry, CustomEncoderEntry]


class CustomButtonEntry(BaseModel):
    type: Literal['param'] = 'param'
    number: int
    name: Optional[str] = None
    display: Optional[str] = None
    min: Optional[int] = None
    max: Optional[int] = None


class LomEnumButtonEntry(BaseModel):
    type: Literal['enum']
    lom_property: str
    display: Optional[str] = None


class LomBoolButtonEntry(BaseModel):
    type: Literal['bool']
    lom_property: str
    display: Optional[str] = None


class LomFunctionButtonEntry(BaseModel):
    type: Literal['function']
    lom_function: str
    display: Optional[str] = None


ButtonEntry = Union[
    LomEnumButtonEntry,
    LomBoolButtonEntry,
    LomFunctionButtonEntry,
    CustomButtonEntry,
]


class CustomDeviceEntry(BaseModel):
    className: str
    deviceName: Optional[str] = None
    fixed: Optional[bool] = None
    encoders: List[EncoderEntry] = Field(default_factory=list)
    buttons: List[ButtonEntry] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def _default_button_type(cls, data):
        if isinstance(data, dict):
            buttons = data.get('buttons')
            if isinstance(buttons, list):
                for b in buttons:
                    if isinstance(b, dict) and 'type' not in b:
                        b['type'] = 'param'
        return data


class CustomDeviceMappings(BaseModel):
    devices: List[CustomDeviceEntry]

    @model_validator(mode='after')
    def _check_group_selectors_resolve(self):
        for d in self.devices:
            encoder_names = {e.name for e in d.encoders if isinstance(e, CustomEncoderEntry) and e.name}
            button_names = {b.name for b in d.buttons if isinstance(b, CustomButtonEntry) and b.name}
            known = encoder_names | button_names
            for e in d.encoders:
                if isinstance(e, GroupedEncoderEntry):
                    if known and e.controlledBy not in known:
                        # We can't fully validate against the live device here,
                        # but we can warn if the selector isn't named anywhere
                        # in the JSON (likely a typo). Soft check — print only.
                        import sys
                        print(
                            f"[custom_device_mappings] warning: device {d.className!r} "
                            f"group references controlledBy={e.controlledBy!r} which is not "
                            f"declared as an encoder/button name in this device entry — "
                            f"verify it matches a real parameter in Live.",
                            file=sys.stderr,
                        )
        return self


def validate_custom_device_mappings(raw: dict) -> dict:
    """Parse-and-validate; return the original dict so it can be baked into
    the generated surface unchanged."""
    CustomDeviceMappings.model_validate(raw)
    return raw
