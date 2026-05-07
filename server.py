"""
DAW MCP Server — Ableton .als file editor exposed as MCP tools for Claude.

Usage:
  py server.py
  Then add to Claude's MCP config (see README).
"""
from mcp.server.fastmcp import FastMCP
from als_editor import ALSEditor

mcp = FastMCP("DAW Assistant")
editor = ALSEditor()


@mcp.tool()
def load_project(path: str) -> str:
    """
    Load an Ableton .als project file. Must be called before any other tool.

    Args:
        path: Absolute path to the .als file, e.g. C:/Users/Ruudo/Downloads/beat.als
    """
    return editor.load(path)


@mcp.tool()
def list_tracks() -> str:
    """
    List all tracks in the loaded project with their volumes, pans, mute state,
    and device chains.
    """
    return editor.list_tracks()


@mcp.tool()
def set_volume(track_name: str, db: float) -> str:
    """
    Set a track's volume.

    Args:
        track_name: Full or prefix of the track's EffectiveName (e.g. "1-ZENOLOGY", "Master", "A-Reverb")
        db: Volume in dB. 0 = unity. Typical range: -inf to +6. Use -70 for silence.
    """
    return editor.set_volume(track_name, db)


@mcp.tool()
def set_pan(track_name: str, percent: float) -> str:
    """
    Set a track's stereo pan position.

    Args:
        track_name: Track name prefix.
        percent: Pan position. -100 = full left, 0 = center, 100 = full right.
    """
    return editor.set_pan(track_name, percent)


@mcp.tool()
def set_send(track_name: str, send_index: int, db: float) -> str:
    """
    Set the send level from a track to a return track.

    Args:
        track_name: Source track name.
        send_index: 0 = Send A (Reverb), 1 = Send B (Delay), etc.
        db: Send level in dB. -inf (use -70) = off. -20 = subtle, -12 = present, -6 = heavy.
    """
    return editor.set_send(track_name, send_index, db)


@mcp.tool()
def add_device(
    track_name: str,
    device_type: str,
    threshold_db: float = -20,
    ratio: float = 4.0,
    attack_ms: float = 10.0,
    release_ms: float = 100.0,
    makeup_db: float = 0.0,
    ceiling_db: float = -0.3,
    lookahead_ms: float = 1.5,
    highpass: bool = False,
    low_shelf_db: float = 0.0,
    mid_gain_db: float = 0.0,
    mid_freq_hz: float = 1500.0,
    high_shelf_db: float = 0.0,
    drive_db: float = 6.0,
    dry_wet: float = 1.0,
    attack_glue: float = 0.5,
    release_glue: float = 0.5,
) -> str:
    """
    Add a new device to a track's device chain.

    Args:
        track_name: Track name prefix.
        device_type: One of: compressor, limiter, channel_eq, glue_compressor, saturator

        --- Compressor params ---
        threshold_db: Threshold in dB (default -20)
        ratio: Compression ratio (default 4.0)
        attack_ms: Attack in ms (default 10)
        release_ms: Release in ms (default 100)
        makeup_db: Makeup gain in dB (default 0)

        --- Limiter params ---
        ceiling_db: Output ceiling in dB (default -0.3)
        lookahead_ms: Lookahead in ms (default 1.5)

        --- Channel EQ params ---
        highpass: Enable highpass filter (default False)
        low_shelf_db: Low shelf gain in dB (default 0)
        mid_gain_db: Mid band gain in dB (default 0)
        mid_freq_hz: Mid band frequency in Hz (default 1500)
        high_shelf_db: High shelf gain in dB (default 0)

        --- Glue Compressor params ---
        attack_glue: Attack (0-7 index, 0=0.1ms, 7=30ms, default 0.5)
        release_glue: Release (0-6 index, default 0.5)

        --- Saturator params ---
        drive_db: Drive amount in dB (0-40, default 6)
        dry_wet: Dry/wet mix 0-1 (default 1.0)
    """
    dt = device_type.lower().replace(" ", "_")

    if dt in ("compressor", "comp"):
        return editor.add_device(track_name, device_type,
                                 threshold_db=threshold_db, ratio=ratio,
                                 attack_ms=attack_ms, release_ms=release_ms,
                                 makeup_db=makeup_db)
    elif dt == "limiter":
        return editor.add_device(track_name, device_type,
                                 ceiling_db=ceiling_db, lookahead_ms=lookahead_ms)
    elif dt in ("channel_eq", "channeleq", "eq"):
        return editor.add_device(track_name, device_type,
                                 highpass=highpass, low_shelf_db=low_shelf_db,
                                 mid_gain_db=mid_gain_db, mid_freq_hz=mid_freq_hz,
                                 high_shelf_db=high_shelf_db)
    elif dt in ("glue_compressor", "glue"):
        return editor.add_device(track_name, device_type,
                                 threshold_db=threshold_db, ratio=ratio,
                                 attack=attack_glue, release=release_glue,
                                 makeup_db=makeup_db)
    elif dt == "saturator":
        return editor.add_device(track_name, device_type,
                                 drive_db=drive_db, dry_wet=dry_wet)
    else:
        return editor.add_device(track_name, device_type)


@mcp.tool()
def list_devices(track_name: str) -> str:
    """
    List all devices on a track with their index numbers and available parameters.
    Use this before set_device_param to find device indices and parameter names.

    Args:
        track_name: Track name prefix.
    """
    return editor.list_devices(track_name)


@mcp.tool()
def set_device_param(track_name: str, device_index: int, param_name: str, value: float) -> str:
    """
    Modify a parameter on an existing device. Use list_devices first to find
    device indices and parameter names.

    Args:
        track_name: Track name prefix.
        device_index: Device index (0-based) from list_devices output.
        param_name: XML parameter tag name, e.g. "Threshold", "Ratio", "Attack",
                    "Release", "Gain", "MidFrequency", "Drive", "Ceiling"
        value: New value (in the device's native units — see Ableton docs).
               For Compressor: Threshold in dB, Ratio as number, Attack/Release in ms.
               For Limiter: Ceiling as linear amplitude (e.g. 0.946 = -0.5dB).
               For ChannelEq: gains as linear ratio (1.0 = 0dB), frequency in Hz.
    """
    return editor.set_device_param(track_name, device_index, param_name, value)


@mcp.tool()
def remove_device(track_name: str, device_index: int) -> str:
    """
    Remove a device from a track's chain.

    Args:
        track_name: Track name prefix.
        device_index: Device index (0-based) from list_devices output.
    """
    return editor.remove_device(track_name, device_index)


@mcp.tool()
def mute_track(track_name: str, muted: bool) -> str:
    """
    Mute or unmute a track.

    Args:
        track_name: Track name prefix.
        muted: True to mute, False to unmute.
    """
    return editor.mute_track(track_name, muted)


@mcp.tool()
def save_project(output_path: str = "") -> str:
    """
    Save the current project back to an .als file.
    IMPORTANT: Close Ableton before opening the saved file, or save to a new path.

    Args:
        output_path: Path to save to. Leave empty to overwrite the original.
                     Recommended: provide a new path to avoid overwriting your source file.
                     e.g. C:/Users/Ruudo/Downloads/beat_mixed.als
    """
    return editor.save(output_path if output_path else None)


if __name__ == "__main__":
    mcp.run(transport="stdio")
