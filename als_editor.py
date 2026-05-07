"""
Ableton .als file editor — reads/writes gzipped XML project files.
"""
import gzip
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


# ── helpers ──────────────────────────────────────────────────────────────────

def db_to_linear(db: float) -> float:
    if db <= -70:
        return 0.0
    return 10 ** (db / 20)

def linear_to_db(v: float) -> float:
    if v <= 0:
        return -math.inf
    return 20 * math.log10(v)

def pan_to_linear(pct: float) -> float:
    """Convert -100..100 percent to -1..1"""
    return max(-1.0, min(1.0, pct / 100.0))


# ── ID management ─────────────────────────────────────────────────────────────

class IDCounter:
    def __init__(self, start: int):
        self._n = start

    def next(self) -> int:
        v = self._n
        self._n += 1
        return v


# ── device XML templates ──────────────────────────────────────────────────────

def _base_device(tag: str, dev_id: int, pointee_id: int, user_name: str = "") -> ET.Element:
    dev = ET.fromstring(f"""<{tag} Id="{dev_id}">
        <LomId Value="0" /><LomIdView Value="0" />
        <IsExpanded Value="true" />
        <On>
            <LomId Value="0" />
            <Manual Value="true" />
            <AutomationTarget Id="{pointee_id + 100}"><LockEnvelope Value="0" /></AutomationTarget>
            <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
        </On>
        <ModulationSourceCount Value="0" />
        <ParametersListWrapper LomId="0" />
        <Pointee Id="{pointee_id}" />
        <LastSelectedTimeableIndex Value="0" />
        <LastSelectedClipEnvelopeIndex Value="0" />
        <LastPresetRef><Value /></LastPresetRef>
        <LockedScripts />
        <IsFolded Value="false" />
        <ShouldShowPresetName Value="true" />
        <UserName Value="{user_name}" />
        <Annotation Value="" />
        <SourceContext><Value /></SourceContext>
        <OverwriteProtectionNumber Value="2816" />
    </{tag}>""")
    return dev


def _param(name: str, value: str, aid: int, mid: Optional[int] = None,
           min_v: str = "0", max_v: str = "1") -> str:
    mod = f"""<ModulationTarget Id="{mid}"><LockEnvelope Value="0" /></ModulationTarget>""" if mid else ""
    return f"""<{name}>
        <LomId Value="0" />
        <Manual Value="{value}" />
        <MidiControllerRange><Min Value="{min_v}" /><Max Value="{max_v}" /></MidiControllerRange>
        <AutomationTarget Id="{aid}"><LockEnvelope Value="0" /></AutomationTarget>
        {mod}
    </{name}>"""


def _bool_param(name: str, value: str, aid: int) -> str:
    return f"""<{name}>
        <LomId Value="0" />
        <Manual Value="{value}" />
        <AutomationTarget Id="{aid}"><LockEnvelope Value="0" /></AutomationTarget>
        <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
    </{name}>"""


def make_compressor(dev_id: int, ids: IDCounter,
                    threshold_db: float = -20, ratio: float = 4,
                    attack_ms: float = 10, release_ms: float = 100,
                    makeup_db: float = 0) -> ET.Element:
    threshold = threshold_db
    xml = f"""<Compressor2 Id="{dev_id}">
        <LomId Value="0" /><LomIdView Value="0" />
        <IsExpanded Value="true" />
        <On><LomId Value="0" /><Manual Value="true" />
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
        </On>
        <ModulationSourceCount Value="0" /><ParametersListWrapper LomId="0" />
        <Pointee Id="{ids.next()}" />
        <LastSelectedTimeableIndex Value="0" /><LastSelectedClipEnvelopeIndex Value="0" />
        <LastPresetRef><Value /></LastPresetRef>
        <LockedScripts /><IsFolded Value="false" /><ShouldShowPresetName Value="true" />
        <UserName Value="" /><Annotation Value="" /><SourceContext><Value /></SourceContext>
        <OverwriteProtectionNumber Value="2816" />
        <Threshold>
            <LomId Value="0" /><Manual Value="{threshold}" />
            <MidiControllerRange><Min Value="-36" /><Max Value="0" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </Threshold>
        <Ratio>
            <LomId Value="0" /><Manual Value="{ratio}" />
            <MidiControllerRange><Min Value="1" /><Max Value="100" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </Ratio>
        <Attack>
            <LomId Value="0" /><Manual Value="{attack_ms}" />
            <MidiControllerRange><Min Value="0.1" /><Max Value="500" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </Attack>
        <Release>
            <LomId Value="0" /><Manual Value="{release_ms}" />
            <MidiControllerRange><Min Value="1" /><Max Value="9999" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </Release>
        <Gain>
            <LomId Value="0" /><Manual Value="{db_to_linear(makeup_db)}" />
            <MidiControllerRange><Min Value="0.031622776" /><Max Value="31.622776" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </Gain>
        <Knee><LomId Value="0" /><Manual Value="3" />
            <MidiControllerRange><Min Value="0" /><Max Value="20" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </Knee>
        <Model Value="0" />
        <LookAhead Value="0" />
        <Env Value="0" />
        <AutoRelease><LomId Value="0" /><Manual Value="false" />
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
        </AutoRelease>
        <ExpansionRatio>
            <LomId Value="0" /><Manual Value="1" />
            <MidiControllerRange><Min Value="1" /><Max Value="100" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </ExpansionRatio>
    </Compressor2>"""
    return ET.fromstring(xml)


def make_limiter(dev_id: int, ids: IDCounter,
                 ceiling_db: float = -0.3, lookahead_ms: float = 1.5) -> ET.Element:
    ceiling_lin = db_to_linear(ceiling_db)
    xml = f"""<Limiter Id="{dev_id}">
        <LomId Value="0" /><LomIdView Value="0" />
        <IsExpanded Value="true" />
        <On><LomId Value="0" /><Manual Value="true" />
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
        </On>
        <ModulationSourceCount Value="0" /><ParametersListWrapper LomId="0" />
        <Pointee Id="{ids.next()}" />
        <LastSelectedTimeableIndex Value="0" /><LastSelectedClipEnvelopeIndex Value="0" />
        <LastPresetRef><Value /></LastPresetRef>
        <LockedScripts /><IsFolded Value="false" /><ShouldShowPresetName Value="true" />
        <UserName Value="" /><Annotation Value="" /><SourceContext><Value /></SourceContext>
        <OverwriteProtectionNumber Value="2816" />
        <Ceiling>
            <LomId Value="0" /><Manual Value="{ceiling_lin}" />
            <MidiControllerRange><Min Value="0.031622776" /><Max Value="1" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </Ceiling>
        <Lookahead Value="{lookahead_ms}" />
        <Release>
            <LomId Value="0" /><Manual Value="50" />
            <MidiControllerRange><Min Value="0.1" /><Max Value="10000" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </Release>
        <AutoRelease><LomId Value="0" /><Manual Value="true" />
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
        </AutoRelease>
        <Mono><LomId Value="0" /><Manual Value="false" />
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
        </Mono>
    </Limiter>"""
    return ET.fromstring(xml)


def make_channel_eq(dev_id: int, ids: IDCounter,
                    highpass: bool = False,
                    low_shelf_db: float = 0, mid_gain_db: float = 0,
                    mid_freq_hz: float = 1500, high_shelf_db: float = 0) -> ET.Element:
    # ChannelEq uses linear gain ratios for band gains (1.0 = 0dB)
    # Range: 0.18 to 5.6 (approx -15 to +15 dB)
    def shelf_lin(db):
        return max(0.18, min(5.6, db_to_linear(db) if db != 0 else 1.0))
    xml = f"""<ChannelEq Id="{dev_id}">
        <LomId Value="0" /><LomIdView Value="0" />
        <IsExpanded Value="true" />
        <On><LomId Value="0" /><Manual Value="true" />
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
        </On>
        <ModulationSourceCount Value="0" /><ParametersListWrapper LomId="0" />
        <Pointee Id="{ids.next()}" />
        <LastSelectedTimeableIndex Value="0" /><LastSelectedClipEnvelopeIndex Value="0" />
        <LastPresetRef><Value /></LastPresetRef>
        <LockedScripts /><IsFolded Value="false" /><ShouldShowPresetName Value="true" />
        <UserName Value="" /><Annotation Value="" /><SourceContext><Value /></SourceContext>
        <OverwriteProtectionNumber Value="2816" />
        <HighpassOn><LomId Value="0" /><Manual Value="{'true' if highpass else 'false'}" />
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
        </HighpassOn>
        <LowShelfGain>
            <LomId Value="0" /><Manual Value="{shelf_lin(low_shelf_db)}" />
            <MidiControllerRange><Min Value="0.1800000072" /><Max Value="5.60000134" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </LowShelfGain>
        <MidGain>
            <LomId Value="0" /><Manual Value="{max(0.25, min(4.0, db_to_linear(mid_gain_db) if mid_gain_db != 0 else 1.0))}" />
            <MidiControllerRange><Min Value="0.25" /><Max Value="4" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </MidGain>
        <MidFrequency>
            <LomId Value="0" /><Manual Value="{mid_freq_hz}" />
            <MidiControllerRange><Min Value="119.999985" /><Max Value="7500.00049" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </MidFrequency>
        <HighShelfGain>
            <LomId Value="0" /><Manual Value="{shelf_lin(high_shelf_db)}" />
            <MidiControllerRange><Min Value="0.1800000072" /><Max Value="5.60000134" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </HighShelfGain>
        <Gain>
            <LomId Value="0" /><Manual Value="1" />
            <MidiControllerRange><Min Value="0.25" /><Max Value="4" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </Gain>
    </ChannelEq>"""
    return ET.fromstring(xml)


def make_glue_compressor(dev_id: int, ids: IDCounter,
                         threshold_db: float = -20, ratio: float = 4,
                         attack: float = 0.5, release: float = 0.5,
                         makeup_db: float = 0) -> ET.Element:
    xml = f"""<GlueCompressor Id="{dev_id}">
        <LomId Value="0" /><LomIdView Value="0" />
        <IsExpanded Value="true" />
        <On><LomId Value="0" /><Manual Value="true" />
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
        </On>
        <ModulationSourceCount Value="0" /><ParametersListWrapper LomId="0" />
        <Pointee Id="{ids.next()}" />
        <LastSelectedTimeableIndex Value="0" /><LastSelectedClipEnvelopeIndex Value="0" />
        <LastPresetRef><Value /></LastPresetRef>
        <LockedScripts /><IsFolded Value="false" /><ShouldShowPresetName Value="true" />
        <UserName Value="" /><Annotation Value="" /><SourceContext><Value /></SourceContext>
        <OverwriteProtectionNumber Value="2816" />
        <Threshold>
            <LomId Value="0" /><Manual Value="{threshold_db}" />
            <MidiControllerRange><Min Value="-40" /><Max Value="0" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </Threshold>
        <Ratio><LomId Value="0" /><Manual Value="{ratio}" />
            <MidiControllerRange><Min Value="1.5" /><Max Value="10" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </Ratio>
        <Attack><LomId Value="0" /><Manual Value="{attack}" />
            <MidiControllerRange><Min Value="0" /><Max Value="7" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </Attack>
        <Release><LomId Value="0" /><Manual Value="{release}" />
            <MidiControllerRange><Min Value="0" /><Max Value="6" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </Release>
        <MakeupGain>
            <LomId Value="0" /><Manual Value="{makeup_db}" />
            <MidiControllerRange><Min Value="-12" /><Max Value="12" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </MakeupGain>
        <DryWet>
            <LomId Value="0" /><Manual Value="1" />
            <MidiControllerRange><Min Value="0" /><Max Value="1" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </DryWet>
        <PeakClipIn><LomId Value="0" /><Manual Value="false" />
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
        </PeakClipIn>
    </GlueCompressor>"""
    return ET.fromstring(xml)


def make_saturator(dev_id: int, ids: IDCounter,
                   drive_db: float = 6, dry_wet: float = 1.0) -> ET.Element:
    xml = f"""<Saturator Id="{dev_id}">
        <LomId Value="0" /><LomIdView Value="0" />
        <IsExpanded Value="true" />
        <On><LomId Value="0" /><Manual Value="true" />
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
        </On>
        <ModulationSourceCount Value="0" /><ParametersListWrapper LomId="0" />
        <Pointee Id="{ids.next()}" />
        <LastSelectedTimeableIndex Value="0" /><LastSelectedClipEnvelopeIndex Value="0" />
        <LastPresetRef><Value /></LastPresetRef>
        <LockedScripts /><IsFolded Value="false" /><ShouldShowPresetName Value="true" />
        <UserName Value="" /><Annotation Value="" /><SourceContext><Value /></SourceContext>
        <OverwriteProtectionNumber Value="2816" />
        <Drive>
            <LomId Value="0" /><Manual Value="{drive_db}" />
            <MidiControllerRange><Min Value="0" /><Max Value="40" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </Drive>
        <Type Value="0" />
        <ColorDrive><LomId Value="0" /><Manual Value="0.270000011" />
            <MidiControllerRange><Min Value="0" /><Max Value="1" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </ColorDrive>
        <WetDryMix>
            <LomId Value="0" /><Manual Value="{dry_wet}" />
            <MidiControllerRange><Min Value="0" /><Max Value="1" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </WetDryMix>
        <OutputGain>
            <LomId Value="0" /><Manual Value="0" />
            <MidiControllerRange><Min Value="-12" /><Max Value="12" /></MidiControllerRange>
            <AutomationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></AutomationTarget>
            <ModulationTarget Id="{ids.next()}"><LockEnvelope Value="0" /></ModulationTarget>
        </OutputGain>
    </Saturator>"""
    return ET.fromstring(xml)


# ── ALSEditor ────────────────────────────────────────────────────────────────

class ALSEditor:
    def __init__(self):
        self.path: Optional[Path] = None
        self.root: Optional[ET.Element] = None
        self._ids: Optional[IDCounter] = None

    # ── load / save ──────────────────────────────────────────────────────────

    def load(self, path: str) -> str:
        p = Path(path)
        if not p.exists():
            return f"File not found: {path}"
        with gzip.open(p, "rb") as f:
            data = f.read()
        self.root = ET.fromstring(data)
        self.path = p
        # find the highest ID in use so we can safely allocate new ones
        max_id = 0
        for el in self.root.iter():
            for attr in ("Id", "Value"):
                try:
                    v = int(el.get(attr, "0"))
                    if v > max_id:
                        max_id = v
                except (ValueError, TypeError):
                    pass
        self._ids = IDCounter(max_id + 100)
        # update NextPointeeId
        npi = self.root.find(".//NextPointeeId")
        if npi is not None:
            npi.set("Value", str(max_id + 100))
        return f"Loaded: {p.name}  ({len(data)//1024} KB, max_id={max_id})"

    def save(self, out_path: Optional[str] = None) -> str:
        if self.root is None:
            return "No project loaded."
        dest = Path(out_path) if out_path else self.path
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
            self.root, encoding="unicode"
        )
        with gzip.open(dest, "wb") as f:
            f.write(xml_str.encode("utf-8"))
        return f"Saved to: {dest}"

    # ── internal helpers ─────────────────────────────────────────────────────

    @property
    def _liveset(self) -> ET.Element:
        return self.root.find("LiveSet")

    def _all_track_types(self):
        return ["MidiTrack", "AudioTrack", "GroupTrack", "ReturnTrack", "MasterTrack"]

    def _find_track(self, name: str) -> Optional[ET.Element]:
        """Find by EffectiveName (case-insensitive prefix match)."""
        ls = self._liveset
        tracks_el = ls.find("Tracks")
        # Check regular tracks
        for tt in ["MidiTrack", "AudioTrack", "GroupTrack", "ReturnTrack"]:
            for t in tracks_el.findall(tt):
                n = t.find("Name/EffectiveName")
                if n is not None and n.get("Value", "").lower().startswith(name.lower()):
                    return t
        # Check master
        mt = ls.find("MasterTrack")
        if mt is not None:
            n = mt.find("Name/EffectiveName")
            eff = n.get("Value", "") if n is not None else "Master"
            if "master" in name.lower() or eff.lower().startswith(name.lower()):
                return mt
        return None

    def _get_mixer(self, track: ET.Element) -> Optional[ET.Element]:
        return track.find("DeviceChain/Mixer")

    def _get_device_chain(self, track: ET.Element) -> Optional[ET.Element]:
        """Returns the Devices element inside DeviceChain/DeviceChain."""
        chain = track.find("DeviceChain/DeviceChain/Devices")
        if chain is not None:
            return chain
        # Master track path
        chain = track.find("DeviceChain/Devices")
        return chain

    # ── public API ───────────────────────────────────────────────────────────

    def list_tracks(self) -> str:
        if self.root is None:
            return "No project loaded."
        ls = self._liveset
        lines = []
        tracks_el = ls.find("Tracks")
        for tt in ["MidiTrack", "AudioTrack", "GroupTrack", "ReturnTrack"]:
            for t in tracks_el.findall(tt):
                name = t.find("Name/EffectiveName").get("Value", "?")
                mixer = self._get_mixer(t)
                vol_db, pan, muted = "", "", ""
                if mixer is not None:
                    v = mixer.find("Volume/Manual")
                    vol = float(v.get("Value", "1")) if v is not None else 1
                    vol_db = f"{linear_to_db(vol):.1f}dB"
                    p = mixer.find("Pan/Manual")
                    pan = f"{float(p.get('Value', 0)) * 100:.0f}%"
                    on = mixer.find("On/Manual")
                    muted = " [MUTED]" if (on is not None and on.get("Value") == "false") else ""
                chain = self._get_device_chain(t)
                devs = []
                if chain is not None:
                    for d in chain:
                        u = d.find("UserName")
                        devs.append(u.get("Value") if (u is not None and u.get("Value")) else d.tag)
                lines.append(
                    f"[{tt[0]}] {name}{muted}  vol={vol_db}  pan={pan}  chain=[{', '.join(devs)}]"
                )
        # sends summary
        mt = ls.find("MasterTrack")
        if mt is not None:
            chain = self._get_device_chain(mt)
            devs = []
            if chain is not None:
                for d in chain:
                    u = d.find("UserName")
                    devs.append(u.get("Value") if (u is not None and u.get("Value")) else d.tag)
            lines.append(f"[Master]  chain=[{', '.join(devs)}]")
        return "\n".join(lines)

    def set_volume(self, track_name: str, db: float) -> str:
        t = self._find_track(track_name)
        if t is None:
            return f"Track not found: {track_name}"
        mixer = self._get_mixer(t)
        if mixer is None:
            return "No mixer found on track."
        v = mixer.find("Volume/Manual")
        if v is None:
            return "No Volume param found."
        lin = db_to_linear(db)
        v.set("Value", str(lin))
        return f"Set '{track_name}' volume to {db:.1f}dB (linear={lin:.6f})"

    def set_pan(self, track_name: str, pct: float) -> str:
        t = self._find_track(track_name)
        if t is None:
            return f"Track not found: {track_name}"
        mixer = self._get_mixer(t)
        p = mixer.find("Pan/Manual") if mixer is not None else None
        if p is None:
            return "No Pan param found."
        p.set("Value", str(pan_to_linear(pct)))
        return f"Set '{track_name}' pan to {pct:.0f}%"

    def set_send(self, track_name: str, send_index: int, db: float) -> str:
        """send_index: 0=A, 1=B, etc."""
        t = self._find_track(track_name)
        if t is None:
            return f"Track not found: {track_name}"
        mixer = self._get_mixer(t)
        if mixer is None:
            return "No mixer."
        sends = mixer.findall("Sends/TrackSendHolder")
        if send_index >= len(sends):
            return f"Send index {send_index} out of range (have {len(sends)} sends)."
        m = sends[send_index].find("Send/Manual")
        if m is None:
            return "Send Manual not found."
        lin = db_to_linear(db)
        m.set("Value", str(lin))
        label = chr(65 + send_index)
        return f"Set '{track_name}' Send {label} to {db:.1f}dB"

    def add_device(self, track_name: str, device_type: str, **kwargs) -> str:
        """
        device_type: compressor | limiter | channel_eq | glue_compressor | saturator
        kwargs: device-specific params (threshold_db, ratio, attack_ms, release_ms,
                makeup_db, ceiling_db, highpass, low_shelf_db, mid_gain_db,
                mid_freq_hz, high_shelf_db, drive_db, dry_wet)
        """
        t = self._find_track(track_name)
        if t is None:
            return f"Track not found: {track_name}"
        chain = self._get_device_chain(t)
        if chain is None:
            return "No device chain found on track."

        dev_id = self._ids.next()
        dt = device_type.lower().replace(" ", "_")

        if dt in ("compressor", "comp"):
            dev = make_compressor(dev_id, self._ids, **kwargs)
        elif dt == "limiter":
            dev = make_limiter(dev_id, self._ids, **kwargs)
        elif dt in ("channel_eq", "channeleq", "eq"):
            dev = make_channel_eq(dev_id, self._ids, **kwargs)
        elif dt in ("glue_compressor", "glue"):
            dev = make_glue_compressor(dev_id, self._ids, **kwargs)
        elif dt == "saturator":
            dev = make_saturator(dev_id, self._ids, **kwargs)
        else:
            return f"Unknown device type: {device_type}. Use: compressor, limiter, channel_eq, glue_compressor, saturator"

        chain.append(dev)
        return f"Added {dev.tag} to '{track_name}'"

    def set_device_param(self, track_name: str, device_index: int,
                         param_name: str, value: float) -> str:
        """Set a Manual value on a device parameter by device index (0-based) and param XML tag name."""
        t = self._find_track(track_name)
        if t is None:
            return f"Track not found: {track_name}"
        chain = self._get_device_chain(t)
        if chain is None:
            return "No device chain."
        devs = list(chain)
        if device_index >= len(devs):
            return f"Device index {device_index} out of range (have {len(devs)})."
        dev = devs[device_index]
        param = dev.find(f"{param_name}/Manual")
        if param is None:
            # Try direct attribute
            el = dev.find(param_name)
            if el is not None:
                el.set("Value", str(value))
                return f"Set {param_name}={value} on device {device_index} ({dev.tag})"
            return f"Param '{param_name}' not found on {dev.tag}. Available: {[c.tag for c in dev]}"
        param.set("Value", str(value))
        return f"Set {param_name}/Manual={value} on device {device_index} ({dev.tag})"

    def list_devices(self, track_name: str) -> str:
        t = self._find_track(track_name)
        if t is None:
            return f"Track not found: {track_name}"
        chain = self._get_device_chain(t)
        if chain is None or len(list(chain)) == 0:
            return f"No devices on '{track_name}'"
        lines = []
        for i, dev in enumerate(chain):
            u = dev.find("UserName")
            label = u.get("Value") if (u is not None and u.get("Value")) else dev.tag
            on = dev.find("On/Manual")
            active = "" if (on is None or on.get("Value") == "true") else " [OFF]"
            params = [c.tag for c in dev if c.find("Manual") is not None]
            lines.append(f"  [{i}] {label}{active}  params: {params}")
        return f"Devices on '{track_name}':\n" + "\n".join(lines)

    def remove_device(self, track_name: str, device_index: int) -> str:
        t = self._find_track(track_name)
        if t is None:
            return f"Track not found: {track_name}"
        chain = self._get_device_chain(t)
        if chain is None:
            return "No device chain."
        devs = list(chain)
        if device_index >= len(devs):
            return f"Index {device_index} out of range."
        dev = devs[device_index]
        chain.remove(dev)
        return f"Removed device [{device_index}] ({dev.tag}) from '{track_name}'"

    def mute_track(self, track_name: str, muted: bool) -> str:
        t = self._find_track(track_name)
        if t is None:
            return f"Track not found: {track_name}"
        mixer = self._get_mixer(t)
        on = mixer.find("On/Manual") if mixer is not None else None
        if on is None:
            return "No On param."
        on.set("Value", "false" if muted else "true")
        return f"{'Muted' if muted else 'Unmuted'} '{track_name}'"
