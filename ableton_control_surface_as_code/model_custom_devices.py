from typing import List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CustomEncoderEntry(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str
    display: Optional[str] = None
    button: Optional[str] = None


class GroupMember(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str
    display: Optional[str] = None
    activeWhen: List[int]


class GroupedEncoderEntry(BaseModel):
    model_config = ConfigDict(extra='forbid')

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
                        f"appears in activeWhen of both name={seen[v]!r} and name={m.name!r}"
                    )
                seen[v] = m.name
        if not self.group:
            raise ValueError(f"group controlledBy={self.controlledBy!r} has no members")
        return self


EncoderEntry = Union[GroupedEncoderEntry, CustomEncoderEntry]


class CustomButtonEntry(BaseModel):
    model_config = ConfigDict(extra='forbid')

    type: Literal['param'] = 'param'
    name: str
    display: Optional[str] = None
    min: Optional[int] = None
    max: Optional[int] = None
    min_max: Optional[bool] = None


class LomEnumButtonEntry(BaseModel):
    model_config = ConfigDict(extra='forbid')

    type: Literal['enum']
    lom_property: str
    display: Optional[str] = None


class LomBoolButtonEntry(BaseModel):
    model_config = ConfigDict(extra='forbid')

    type: Literal['bool']
    lom_property: str
    display: Optional[str] = None


class LomFunctionButtonEntry(BaseModel):
    model_config = ConfigDict(extra='forbid')

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
    model_config = ConfigDict(extra='forbid')

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
            encoder_names = {e.name for e in d.encoders if isinstance(e, CustomEncoderEntry)}
            button_names = {b.name for b in d.buttons if isinstance(b, CustomButtonEntry)}
            known = encoder_names | button_names
            for e in d.encoders:
                if isinstance(e, GroupedEncoderEntry):
                    if known and e.controlledBy not in known:
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
