"""Validation for the shipped smart-zoning tables
(`data/synth_zone_tables.json`). Mirrors `model_custom_devices` in spirit:
parse-and-validate, return the raw dict so gen.py can bake it into the surface
unchanged.

The template is what makes zone positions immovable, so the invariants guard
exactly that: the template must cover every pot slot (1..32) and button slot
(1..16) exactly once, template role ids must be unique, every per-synth role
must exist in the template, and no synth may bind the same parameter to two
different pots (or two buttons) — that duplicate is the muscle-memory reshuffle
smart-zoning exists to prevent. See grid-po16-synth-surface-plan §6.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

ENCODER_SLOTS = 32
BUTTON_SLOTS = 16


class ZoneTemplateEntry(BaseModel):
    model_config = ConfigDict(extra='forbid')

    slot: int
    role: str
    zone: str
    display: Optional[str] = None


class ZoneRoleParam(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str
    display: Optional[str] = None


class ZoneTemplate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    encoders: List[ZoneTemplateEntry]
    buttons: List[ZoneTemplateEntry]


class SynthZoneEntry(BaseModel):
    model_config = ConfigDict(extra='forbid')

    display: str
    encoders: Dict[str, ZoneRoleParam] = Field(default_factory=dict)
    buttons: Dict[str, ZoneRoleParam] = Field(default_factory=dict)


class SynthZoneTables(BaseModel):
    model_config = ConfigDict(extra='forbid')

    comment: Optional[str] = None
    template: ZoneTemplate
    synths: Dict[str, SynthZoneEntry]

    @staticmethod
    def _check_slot_cover(entries, count, kind):
        slots = sorted(e.slot for e in entries)
        if slots != list(range(1, count + 1)):
            raise ValueError(
                f"template {kind} must cover slots 1..{count} exactly once, got {slots}")

    @staticmethod
    def _template_roles(entries, kind):
        roles = [e.role for e in entries]
        dupes = {r for r in roles if roles.count(r) > 1}
        if dupes:
            raise ValueError(f"template {kind} has duplicate role id(s): {sorted(dupes)}")
        return set(roles)

    @model_validator(mode='after')
    def _check(self):
        self._check_slot_cover(self.template.encoders, ENCODER_SLOTS, 'encoders')
        self._check_slot_cover(self.template.buttons, BUTTON_SLOTS, 'buttons')
        enc_roles = self._template_roles(self.template.encoders, 'encoders')
        btn_roles = self._template_roles(self.template.buttons, 'buttons')

        for class_name, synth in self.synths.items():
            for role in synth.encoders:
                if role not in enc_roles:
                    raise ValueError(
                        f"synth {class_name!r} encoder role {role!r} is not in the template")
            for role in synth.buttons:
                if role not in btn_roles:
                    raise ValueError(
                        f"synth {class_name!r} button role {role!r} is not in the template")
            self._check_no_dupe_params(class_name, 'encoder', synth.encoders)
            self._check_no_dupe_params(class_name, 'button', synth.buttons)
        return self

    @staticmethod
    def _check_no_dupe_params(class_name, kind, role_map):
        names = [p.name for p in role_map.values()]
        dupes = {n for n in names if names.count(n) > 1}
        if dupes:
            raise ValueError(
                f"synth {class_name!r} binds the same {kind} parameter to two roles: "
                f"{sorted(dupes)}")


def validate_synth_zone_tables(raw: dict) -> dict:
    """Parse-and-validate; return the original dict unchanged so it can be baked
    into the generated surface."""
    SynthZoneTables.model_validate(raw)
    return raw
