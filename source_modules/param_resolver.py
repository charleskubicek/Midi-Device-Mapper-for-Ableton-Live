"""Pure parameter-resolution logic, extracted from Helpers (plan item R9).

`ParameterResolver` owns the device→parameter mapping problem: BOB / standard-
bank / unknown-class fallback resolution, the two name indices (strict
`original_name` vs display-name), encoder/button paging math, and LOM enum/bool
introspection. It has no Live-surface coupling — its only outside dependency is
a `log` callable — so it is testable with plain data and fakes, not a whole
surface. The Live-coupled side (writing parameter.value, listeners, messages)
stays in Helpers, which owns one of these and delegates to it.
"""
from dataclasses import dataclass
from typing import Any, Optional

from .hud_protocol import SlotPayload


@dataclass
class RealParameter:
    param: Any
    alias: Optional[str] = None
    button: Optional[str] = None


@dataclass
class ParameterMapping:
    #(2, (5, 'Mono'), 'toggle')
    mapped_parameter: int
    alias: Optional[str] = None
    button: Optional[str] = None

    @classmethod
    def from_tuple(cls, tuple):
        return cls(tuple[0], tuple[1], tuple[2])

    @classmethod
    def on_off(cls, param=0):
        return cls(param, "On/Off", None)

    def with_real_param(self, real_param):
        return RealParameter(real_param, self.alias, self.button)


@dataclass
class SwitchSlotMapping:
    switch_idx: int
    d_idx: Optional[int] = None
    alias: str = ''
    payload: Optional[SlotPayload] = None  # set for LOM-kind entries


# Max-for-Live wrappers: every M4L plugin reports the same class_name, so
# entries for these must be disambiguated by device.name. Non-M4L entries
# are keyed by (class_name, None) and resolve regardless of device.name.
M4L_CLASSES = ('MxDeviceMidiEffect', 'MxDeviceAudioEffect', 'MxDeviceInstrument')

# Racks share a className across all instances, so BOB entries targeting a
# specific Rack must be disambiguated by device.name (same scheme as M4L).
# Standard Macro banks still resolve by className alone — see standard_banks.
RACK_CLASSES = ('AudioEffectGroupDevice', 'InstrumentGroupDevice',
                'MidiEffectGroupDevice', 'DrumGroupDevice')

NAME_DISAMBIGUATED_CLASSES = M4L_CLASSES + RACK_CLASSES


def _build_device_table(raw):
    table = {}
    if not raw:
        return table
    for d in raw.get('devices', []):
        cn = d['className']
        key = (cn, d.get('deviceName')) if cn in NAME_DISAMBIGUATED_CLASSES else (cn, None)
        table[key] = {
            'encoders': d.get('encoders', []) or [],
            'buttons': d.get('buttons', []) or [],
        }
    return table


def _build_zone_tables(raw):
    """Compile the shipped smart-zoning tables into the lookup form the resolver
    uses: slot -> role maps (from the immovable template) plus the per-className
    role -> param tables. Returns None when zoning ships no data, so the resolver
    can treat "no zone tables" and "zoning off" identically. See
    grid-po16-synth-surface-plan §6."""
    if not raw:
        return None
    template = raw.get('template', {}) or {}
    enc_slot_role = {e['slot']: e['role'] for e in template.get('encoders', [])}
    btn_slot_role = {e['slot']: e['role'] for e in template.get('buttons', [])}
    # slot -> zone (fixed template property; drives LED/HUD colour, independent
    # of which param resolves — an unmapped slot still shows its zone hue).
    enc_slot_zone = {e['slot']: e.get('zone') for e in template.get('encoders', [])}
    btn_slot_zone = {e['slot']: e.get('zone') for e in template.get('buttons', [])}
    synths = {}
    for class_name, entry in (raw.get('synths', {}) or {}).items():
        synths[class_name] = {
            'display': entry.get('display', class_name),
            'encoders': entry.get('encoders', {}) or {},
            'buttons': entry.get('buttons', {}) or {},
        }
    return {
        'enc_slot_role': enc_slot_role,
        'btn_slot_role': btn_slot_role,
        'enc_slot_zone': enc_slot_zone,
        'btn_slot_zone': btn_slot_zone,
        'zone_colors': raw.get('zone_colors', {}) or {},
        'synths': synths,
    }


def _device_table_key(device):
    cn = _safe_device_attr(device, 'class_name')
    if cn in NAME_DISAMBIGUATED_CLASSES:
        return (cn, _safe_device_attr(device, 'name'))
    return (cn, None)


def _safe_device_attr(device, attr, default=None):
    """Read an attribute off a Live *device*, treating a dead Boost.Python
    handle the same as absent. A replaced/deleted device (e.g. Wavetable
    swapped for Drift) becomes a dead handle whose every attribute access
    raises Boost.Python.ArgumentError — a TypeError subclass, NOT
    AttributeError, so a plain `getattr(device, attr, default)` does not
    shield us. Mirrors `ParameterResolver._attr` for the device object."""
    try:
        return getattr(device, attr, default)
    except Exception:
        return default


def _device_alive(device):
    """True iff `device` is a readable (non-dead) Live handle. Reading the
    cheapest attribute exercises the underlying C++ handle; a freed handle
    raises instead of returning."""
    if device is None:
        return False
    try:
        device.name
        return True
    except Exception:
        return False


def _same_device(new, prev):
    """Fail-OPEN device-identity check for the focus/selection guards. Returns
    True only when `prev` is a *live* handle equal to `new`; a dead or None
    `prev` can never legitimately equal a live selection, so it returns False
    (treat as changed → proceed). This is what lets a session self-recover
    after a device replace left a dead handle pinned: without fail-open the
    same-device guard short-circuits forever and the HUD stays dead."""
    if new is None or not _device_alive(prev):
        return False
    try:
        return new == prev
    except Exception:
        return False


def _load_bundled_banks():
    # In the generated surface, live_device_banks.py is shipped next to
    # helpers.py (gen.py copies it). When running from the repo root for tests
    # it lives at data/live_device_banks.py.
    try:
        from .live_device_banks import DEVICE_BANKS, BANK_NAMES
        return DEVICE_BANKS, BANK_NAMES
    except ImportError:
        pass
    try:
        from data.live_device_banks import DEVICE_BANKS, BANK_NAMES
        return DEVICE_BANKS, BANK_NAMES
    except ImportError:
        return {}, {}


def _default_device_banks():
    return _load_bundled_banks()[0]


def _default_bank_names():
    return _load_bundled_banks()[1]


class ParameterResolver:
    def __init__(self, device_table, device_banks, bank_names,
                 banks_per_page, button_switch_count, button_slot_count, log,
                 smart_zoning=False, zone_tables=None):
        self._device_table = device_table
        self._device_banks = device_banks
        self._bank_names = bank_names
        self._banks_per_page = banks_per_page
        self._button_switch_count = button_switch_count
        self._button_slot_count = button_slot_count
        self._log = log
        # Smart-zoning tier (grid-po16-synth-surface-plan): active only when the
        # surface toggle is on AND the focused device's class_name has a shipped
        # zone table. Off/no-tables -> `_is_zoned` is always False and every
        # resolution path below is byte-for-byte today's behavior.
        self._smart_zoning = bool(smart_zoning)
        self._zone_tables = zone_tables
        # Paging state — reset on every device focus via focus().
        self.encoder_page = 1
        self.button_page = 1
        self._name_index = None  # {original_name: idx}, rebuilt on device focus change
        self._display_name_index = None  # {name: idx}, bank fallback only
        # The device this resolver's per-device state was last built for. Lets
        # `ensure_focused` detect a burst assembled for a device the Helpers
        # funnel never reset and self-correct. None = no device focused yet.
        self._focused_device = None

    @property
    def device_table(self):
        return self._device_table

    def focus(self):
        """Reset per-device state on a focus change: drop the name indices and
        return to page 1 for both encoders and buttons."""
        self._name_index = None
        self._display_name_index = None
        self.encoder_page = 1
        self.button_page = 1

    def ensure_focused(self, device):
        """Defensive per-device guard, called at burst assembly so the burst is
        the single source of truth for per-device state. If `device` differs
        from the device this resolver was last focused on, hard-reset (drop the
        name index + return paging to page 1). A burst assembled for a device
        the Helpers funnel never reset — a bypassed selection path — thus
        self-corrects its index and page instead of inheriting the previous
        device's (the stale-index / "opened on the wrong page" bug). Idempotent
        on the same device, so it never disturbs live paging."""
        if device is not None and not _same_device(device, self._focused_device):
            self.focus()
            self._focused_device = device

    def group_selector_names(self, device):
        """Ordered, de-duplicated `controlledBy` selector names for this
        device's BOB encoders — the params the facade attaches value listeners
        to so a group-selector turn re-emits the burst."""
        entry = self.device_entry(device)
        if not entry:
            return []
        names = []
        seen = set()
        for e in entry['encoders']:
            name = e.get('controlledBy') if isinstance(e, dict) else None
            if not name or name in seen:
                continue
            seen.add(name)
            names.append(name)
        return names

    def has_user_defined_parameters(self, device):
        return device is not None and _device_table_key(device) in self._device_table

    def device_entry(self, device):
        if device is None:
            return None
        return self._device_table.get(_device_table_key(device))

    def _ensure_name_index(self, device):
        """Builds a strict `original_name` index used by BOB and switch
        resolvers — keeps user-renamed Rack macros from hijacking lookups.
        Also builds a secondary `name` (display-name) index, consulted only
        by the standard-bank resolver via `_resolve_bank_param`.

        Both indices map name -> *integer index* into `device.parameters`, not
        the parameter object. Caching the object is unsafe: devices that
        rebuild their parameter list in place (notably Live 12.4's new
        Operator, as oscillators/filters toggle) leave a cached object as a
        dead Boost.Python handle that raises `ArgumentError` on any attribute
        access. We re-fetch live by index in `_live_param` instead."""
        if self._name_index is None and device is not None:
            # Use the dead-handle-safe reader: the rebuild path can run mid-burst,
            # where a freshly-rebuilt parameter tuple could still hold an
            # unreadable entry; `_attr` treats that as absent rather than raising.
            self._name_index = {
                (self._attr(p, 'original_name') or self._attr(p, 'name') or ''): i
                for i, p in enumerate(device.parameters)
            }
            self._display_name_index = {
                self._attr(p, 'name'): i
                for i, p in enumerate(device.parameters)
                if self._attr(p, 'name')
            }

    @staticmethod
    def _attr(param, attr):
        """Read an attribute off a Live parameter, treating a dead-handle
        failure the same as 'absent'. Boost.Python raises ArgumentError (a
        TypeError subclass) — not AttributeError — so plain getattr defaults
        don't shield us."""
        try:
            return getattr(param, attr, None)
        except Exception:
            return None

    def _live_param(self, device, name, index_map, key_attr):
        """Resolve `name` to the *live* `device.parameters` entry via a cached
        name -> index map, revalidating against `key_attr` (`original_name` for
        the strict index, `name` for the display index). If the live list
        reordered/resized so the cached index no longer matches — or the cached
        index is dead — rebuild the indices once and retry, so consumers always
        get a current handle."""
        if device is None or not name or not index_map:
            return None
        p = self._param_at(device, index_map.get(name))
        if p is not None and self._attr(p, key_attr) == name:
            return p
        # Stale index (list rebuilt). Rebuild once and retry against the fresh map.
        self._name_index = None
        self._display_name_index = None
        self._ensure_name_index(device)
        fresh_map = self._name_index if key_attr == 'original_name' else self._display_name_index
        p = self._param_at(device, (fresh_map or {}).get(name))
        if p is not None and self._attr(p, key_attr) == name:
            return p
        return None

    @staticmethod
    def _param_at(device, idx):
        if idx is None:
            return None
        try:
            return device.parameters[idx]
        except (IndexError, TypeError):
            return None

    def resolve_param_by_name(self, device, name):
        """Single name → Parameter lookup. Uses `original_name` (Live's stable
        identifier); `Parameter.name` reflects user renames and must not be
        used. Returns None on miss — caller is responsible for the empty-slot
        behavior."""
        if device is None or not name:
            return None
        self._ensure_name_index(device)
        return self._live_param(device, name, self._name_index, 'original_name')

    def _resolve_bank_param(self, device, name):
        """Standard-bank lookup: prefers `original_name` like the strict
        resolver, but falls back to `Parameter.name` because the scrape in
        `data/live_device_banks.py` was generated from Live's display-name
        table (`_Generic/Devices.py`). For most built-in params the two
        match; for a handful (e.g. Reverb's filter cluster) they don't, and
        the strict-only lookup blanks them on the HUD."""
        if device is None or not name:
            return None
        self._ensure_name_index(device)
        p = self._live_param(device, name, self._name_index, 'original_name')
        if p is not None:
            return p
        return self._live_param(device, name, self._display_name_index, 'name')

    def _resolve_param_d_idx(self, device, name):
        """Return device.parameters index for the named param, or None."""
        if device is None or not name:
            return None
        self._ensure_name_index(device)
        return (self._name_index or {}).get(name)

    def _bob_encoders(self, device):
        entry = self.device_entry(device)
        return entry.get('encoders', []) if entry else []

    def _bob_buttons(self, device):
        entry = self.device_entry(device)
        return entry.get('buttons', []) if entry else []

    def standard_banks(self, device):
        # Standard banks are keyed by class_name only and only apply to
        # built-in devices; M4L plugins (one shared class) never get banks.
        cn = getattr(device, 'class_name', None)
        if cn in M4L_CLASSES:
            return ()
        return self._device_banks.get(cn, ())

    def _fallback_continuous(self, device):
        """Unknown-class identity fallback list: skip on/off and quantized,
        keyed by original_name."""
        if device is None:
            return []
        return [p for i, p in enumerate(device.parameters)
                if i > 0 and not getattr(p, 'is_quantized', False)]

    def _fallback_quantized(self, device):
        if device is None:
            return []
        return [(i, p) for i, p in enumerate(device.parameters)
                if i > 0 and getattr(p, 'is_quantized', False)]

    def _has_bob(self, device):
        return self.device_entry(device) is not None

    def _zone_synth(self, device):
        """The zone table for `device`'s className, or None. A device is zoned
        iff the surface toggle is on AND its className has a shipped `synths`
        entry — never guessed. Dead-handle-safe on class_name."""
        if not self._smart_zoning or not self._zone_tables or device is None:
            return None
        cn = _safe_device_attr(device, 'class_name')
        if cn is None:
            return None
        return self._zone_tables['synths'].get(cn)

    def _is_zoned(self, device):
        return self._zone_synth(device) is not None

    def is_zoned(self, device):
        """Public: is the focused device driven by the smart-zoning tier? Callers
        gate zone-colour emission on this so a non-zoned focus shows no tint."""
        return self._is_zoned(device)

    def zone_for_slot(self, kind, surface_slot):
        """Template zone for a 1-based surface slot ('dial'|'button' kind), or
        None if there are no zone tables or the slot isn't in the template.
        Independent of any device — a pure template lookup."""
        if not self._zone_tables:
            return None
        key = 'enc_slot_zone' if kind == 'dial' else 'btn_slot_zone'
        return self._zone_tables[key].get(surface_slot)

    def color_for_slot(self, kind, surface_slot):
        """RRGGBB hex for a slot's zone, or None. Callers apply this only for a
        zoned device (so a non-zoned focus shows no tint)."""
        zone = self.zone_for_slot(kind, surface_slot)
        if zone is None:
            return None
        return self._zone_tables['zone_colors'].get(zone)

    def _zone_lookup(self, device, kind, slot):
        """Resolve a zone slot to one of three outcomes, so callers can tell a
        slot the template doesn't own (fall through to BOB/fallback) from a
        template slot the current synth can't fill (silent dim):
          - ('fallthrough', None): `slot` is outside the zone template — e.g.
            the shift-mode second button bank binds slots 17-32, which the
            16-button template never claims. Behave exactly as pre-zoning.
          - ('unmapped', None): a real template role this synth doesn't fill —
            legitimately blank, dim LED, no log.
          - ('mapped', entry): the role's param spec, ready to resolve.
        `kind` is 'encoders' or 'buttons'; `slot` is the 1-based template slot."""
        synth = self._zone_synth(device)
        if synth is None:
            return ('fallthrough', None)
        slot_role = self._zone_tables[
            'enc_slot_role' if kind == 'encoders' else 'btn_slot_role']
        role = slot_role.get(slot)
        if role is None:
            return ('fallthrough', None)
        entry = synth[kind].get(role)
        if entry is None:
            return ('unmapped', None)
        return ('mapped', entry)

    def _has_bob_encoders(self, device):
        """BOB takes encoder page 1 only if it actually defines encoders.
        A buttons-only BOB (e.g. a Rack with `min_max` switches) must not
        push standard Macro banks off page 1."""
        return bool(self._bob_encoders(device))

    def _first_standard_page(self, device):
        """Page index where standard banks start. 2 if page 1 is taken by a zone
        layout or BOB encoders; 1 otherwise so banks lead."""
        return 2 if (self._is_zoned(device) or self._has_bob_encoders(device)) else 1

    def _standard_bank_name_for(self, device, page, slot_in_page):
        """Page is 1-based. Standard banks are paired self._banks_per_page
        at a time, starting at _first_standard_page(device)."""
        banks = self.standard_banks(device)
        first_std = self._first_standard_page(device)
        if not banks or page < first_std:
            return None
        per_page = self._banks_per_page
        first_bank_idx = (page - first_std) * per_page
        which = slot_in_page // 8
        within = slot_in_page % 8
        if which >= per_page:
            return None
        bank_idx = first_bank_idx + which
        if bank_idx >= len(banks):
            return None
        bank = banks[bank_idx]
        if within >= len(bank):
            return None
        return bank[within]

    def encoder_pages_count(self, device):
        if device is None:
            return 1
        # A zone layout and a BOB both occupy exactly encoder page 1.
        lead_pages = 1 if (self._is_zoned(device) or self._has_bob_encoders(device)) else 0
        banks = self.standard_banks(device)
        if banks:
            std_pages = (len(banks) + self._banks_per_page - 1) // self._banks_per_page
            return max(1, lead_pages + std_pages)
        if lead_pages:
            return 1
        # Unknown class fallback — chunk continuous params by 8s then pair.
        params_per_page = 8 * self._banks_per_page
        n = len(self._fallback_continuous(device))
        return max(1, (n + params_per_page - 1) // params_per_page)

    def button_pages_count(self, device):
        if device is None:
            return 1
        if self._is_zoned(device):
            # Zone buttons are the single 16-role template page; factory-bank
            # button paging is not offered on a zoned synth.
            return 1
        if self._has_bob(device):
            stride = self._button_switch_count or self._button_slot_count
            n = len(self._bob_buttons(device))
            return max(1, (n + stride - 1) // stride)
        n = len(self._fallback_quantized(device))
        return max(1, (n + self._button_slot_count - 1) // self._button_slot_count)

    def page_label_for(self, device, page):
        if device is None:
            return ''
        class_name = getattr(device, 'class_name', None)
        if page == 1 and self._is_zoned(device):
            return 'Zoned'
        if page == 1 and self._has_bob_encoders(device):
            return 'Best of'
        names = self._bank_names.get(class_name)
        banks = self.standard_banks(device)
        first_std = self._first_standard_page(device)
        if not names or not banks or page < first_std:
            return ''
        per_page = self._banks_per_page
        first = (page - first_std) * per_page
        labels = []
        for offset in range(per_page):
            idx = first + offset
            if idx < len(names):
                labels.append(names[idx])
        return ' / '.join(labels)

    def resolve_encoder(self, device, c_idx):
        if device is None:
            return None
        page = self.encoder_page
        slot_in_page = c_idx - 1
        class_name = getattr(device, 'class_name', None)
        known = (self._has_bob(device) or bool(self.standard_banks(device))
                 or self._is_zoned(device))

        # Zone tier — page 1 of an enrolled synth. Precedes BOB (zone beats BOB;
        # by design they never both apply — custom mappings stay effects-only).
        # A slot outside the template falls through; only a mapped-but-unfilled
        # role dims.
        if page == 1 and self._is_zoned(device):
            outcome, entry = self._zone_lookup(device, 'encoders', c_idx)
            if outcome == 'unmapped':
                return None  # dim LED, blank HUD — a legitimate role miss
            if outcome == 'mapped':
                name = entry['name']
                p = self.resolve_param_by_name(device, name)
                if p is None:
                    self._log(
                        f"[zone] '{name}' (slot {c_idx}) not found in "
                        f"{class_name} original_names — zone table drift."
                    )
                    return None
                return RealParameter(p, entry.get('display') or name, entry.get('button'))
            # outcome == 'fallthrough' — slot not owned by the template

        if page == 1 and self._has_bob_encoders(device):
            encoders = self._bob_encoders(device)
            if slot_in_page < len(encoders):
                e = encoders[slot_in_page]
                if 'controlledBy' in e and 'group' in e:
                    e = self._resolve_group_member(device, e)
                    if e is None:
                        return None
                name = e.get('name')
                p = self.resolve_param_by_name(device, name)
                if p is None:
                    available = list((self._name_index or {}).keys())[:30]
                    self._log(
                        f"[bob] '{name}' not found in {getattr(device,'class_name','?')} "
                        f"({getattr(device,'name','?')}) original_names. "
                        f"Available (first 30): {available}"
                    )
                    return None
                return RealParameter(p, e.get('display') or name, e.get('button'))
            return None

        if page >= self._first_standard_page(device) and self.standard_banks(device):
            name = self._standard_bank_name_for(device, page, slot_in_page)
            if name is None:
                return None
            p = self._resolve_bank_param(device, name)
            if p is None:
                available = list((self._name_index or {}).keys())[:30]
                self._log(
                    f"[bank] '{name}' (slot {slot_in_page}, page {page}) not found in "
                    f"{getattr(device,'class_name','?')} original_names. "
                    f"Available (first 30): {available}"
                )
                return None
            return RealParameter(p, None, None)

        if known:
            # Known class but no banks (only BOB), and we've already handled
            # page 1 above. Higher pages render empty.
            return None

        # Unknown class — chunked identity fallback over continuous params,
        # paired onto pages when slot_count >= 16.
        params = self._fallback_continuous(device)
        offset = (page - 1) * 8 * self._banks_per_page + slot_in_page
        if offset >= len(params):
            return None
        return RealParameter(params[offset], None, None)

    def _resolve_group_member(self, device, entry):
        selector_name = entry['controlledBy']
        selector = self.resolve_param_by_name(device, selector_name)
        if selector is None:
            return None
        try:
            sel_value = int(round(selector.value))
        except (TypeError, ValueError):
            return None
        for member in entry['group']:
            if sel_value in member.get('activeWhen', []):
                return member
        return None

    def resolve_switch(self, device, switch_idx):
        if device is None:
            return None
        class_name = getattr(device, 'class_name', None)
        # Zone tier — button slot on an enrolled synth (page 1 only). Precedes
        # BOB, same precedence as the encoder path. A slot outside the 16-button
        # template (e.g. shift-mode's grid-1 second bank on slots 17-32) falls
        # through to BOB/fallback so pre-zoning behavior is preserved there.
        if self._is_zoned(device):
            outcome, entry = self._zone_lookup(device, 'buttons', switch_idx + 1)
            if outcome != 'fallthrough':
                if self.button_page != 1 or outcome == 'unmapped':
                    return None  # dim LED / no zone paging beyond page 1
                name = entry['name']
                p = self.resolve_param_by_name(device, name)
                if p is None:
                    self._log(
                        f"[zone] button '{name}' (slot {switch_idx + 1}) not found in "
                        f"{class_name} original_names — zone table drift."
                    )
                    return None
                # has_range=False: a quantized param (Algorithm 0-10, filter
                # type, on/off) is cycled by the switch handler over its own
                # min/max — identical to a rangeless BOB toggle button.
                return {
                    'kind': 'param',
                    'param': p,
                    'alias': entry.get('display') or name,
                    'd_idx': self._resolve_param_d_idx(device, name),
                    'has_range': False, 'min': None, 'max': None, 'min_max': False,
                }
        if self._has_bob(device):
            buttons = self._bob_buttons(device)
            stride = self._button_switch_count or self._button_slot_count
            actual_idx = (self.button_page - 1) * stride + switch_idx
            if actual_idx >= len(buttons):
                return None
            b = buttons[actual_idx]
            btype = b.get('type', 'param')
            if btype == 'enum':
                prop = b['lom_property']
                return {'kind': 'enum', 'device': device, 'prop': prop,
                        'alias': b.get('display') or prop}
            if btype == 'bool':
                prop = b['lom_property']
                return {'kind': 'bool', 'device': device, 'prop': prop,
                        'alias': b.get('display') or prop}
            if btype == 'function':
                fn = b['lom_function']
                return {'kind': 'function', 'device': device, 'fn': fn,
                        'alias': b.get('display') or fn}
            name = b.get('name')
            p = self.resolve_param_by_name(device, name)
            if p is None:
                available = list((self._name_index or {}).keys())[:20]
                self._log(
                    f"[switch] '{name}' not found in {class_name} params. "
                    f"Available (first 20): {available}"
                )
                return None
            has_range = b.get('min') is not None and b.get('max') is not None
            return {
                'kind': 'param',
                'param': p,
                'alias': b.get('display') or name,
                'd_idx': self._resolve_param_d_idx(device, name),
                'has_range': has_range,
                'min': int(b['min']) if has_range else None,
                'max': int(b['max']) if has_range else None,
                'min_max': bool(b.get('min_max')),
            }
        # Unknown-class fallback: existing quantized chunking.
        idx = (self.button_page - 1) * self._button_slot_count + switch_idx
        quantized = self._fallback_quantized(device)
        if idx >= len(quantized):
            return None
        d_idx, p = quantized[idx]
        return {
            'kind': 'param',
            'param': p, 'alias': getattr(p, 'name', ''), 'd_idx': d_idx,
            'has_range': True, 'min': int(p.min), 'max': int(p.max),
            'min_max': False,
        }

    def enum_members(self, current_value, device=None, prop=None):
        """Return ordered list of enum members for an LOM enum property.

        Three discovery paths, tried in order:
          1. `type(current_value).values` (Boost.Python enum returned as its
             own type, e.g. Device.DeviceType.instrument).
          2. `iter(type(current_value))` (stdlib Enum etc).
          3. Live module lookup: many Live properties (Simpler.playback_mode,
             etc.) return a plain `int`, while the enum class lives at
             `Live.<DeviceModule>.<CamelCaseProperty>`. We resolve that class
             and use its `.values` dict, returning the integer members so they
             can be assigned back via `setattr(device, prop, int_value)`.
        Returns None if every path fails."""
        cls = type(current_value)
        values = getattr(cls, 'values', None)
        if isinstance(values, dict) and values:
            try:
                return sorted(values.values(), key=lambda m: int(m))
            except (TypeError, ValueError):
                return list(values.values())
        try:
            members = list(cls)
            if members:
                return members
        except TypeError:
            pass

        if device is not None and prop is not None:
            resolved = self._resolve_live_enum_class(device, prop)
            if resolved is not None:
                vals = getattr(resolved, 'values', None)
                if isinstance(vals, dict) and vals:
                    try:
                        return sorted(vals.values(), key=lambda m: int(m))
                    except (TypeError, ValueError):
                        return list(vals.values())
                try:
                    members = list(resolved)
                    if members:
                        return members
                except TypeError:
                    pass
        return None

    @staticmethod
    def _resolve_live_enum_class(device, prop):
        """Look up `Live.<device_module>.<CamelCaseProp>` — the convention
        Live uses for enum classes belonging to a device. Returns the class
        or None."""
        try:
            import Live
        except ImportError:
            return None
        module_name = type(device).__module__
        cls_name = ''.join(part.capitalize() for part in prop.split('_'))
        module = getattr(Live, module_name, None)
        if module is None:
            return None
        return getattr(module, cls_name, None)

    @staticmethod
    def enum_index_of(members, current):
        """Find current's position in `members`. Tries equality first, then
        falls back to comparing int casts (covers the case where the property
        returns a plain int but members are enum objects)."""
        try:
            return members.index(current)
        except ValueError:
            pass
        try:
            cur_int = int(current)
            for i, m in enumerate(members):
                try:
                    if int(m) == cur_int:
                        return i
                except (TypeError, ValueError):
                    continue
        except (TypeError, ValueError):
            pass
        return -1

    def lom_slot_payload(self, info):
        kind = info['kind']
        alias = info.get('alias') or ''
        device = info['device']
        try:
            if kind == 'enum':
                current = getattr(device, info['prop'])
                members = self.enum_members(current, device, info['prop']) or []
                idx = self.enum_index_of(members, current) if members else 0
                if idx < 0:
                    idx = 0
                vmax = max(0, len(members) - 1)
                current_label = members[idx] if members else current
                label = f"{alias}: {current_label}" if alias else str(current_label)
                return SlotPayload(label, float(idx), 0.0, float(vmax) if vmax > 0 else 1.0)
            if kind == 'bool':
                current = bool(getattr(device, info['prop']))
                return SlotPayload(alias, 1.0 if current else 0.0, 0.0, 1.0)
            if kind == 'function':
                return SlotPayload(alias, 0.0, 0.0, 1.0)
        except Exception as ex:
            self._log(f"[lom-hud] failed to build payload for {info}: {ex}")
        return None
