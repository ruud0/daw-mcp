# DAW MCP Server

An MCP (Model Context Protocol) server that lets Claude read and edit Ableton Live `.als` project files. Mix tracks, add effects, and adjust parameters through natural language.

## Demo

![demo](docs/demo.gif)

<!-- Record a short screen capture of a real session and save it to
     docs/demo.gif. Until then this image renders as broken. -->

## What it does

- **Load/save** Ableton `.als` projects (gzipped XML)
- **List tracks** with volume, pan, mute state, and device chains
- **Mix**: set volume, pan, and send levels per track
- **Add devices**: Compressor, Limiter, Channel EQ, Glue Compressor, Saturator, with full parameter control
- **Edit devices**: modify any parameter on existing devices
- **Remove devices** and **mute/unmute** tracks

## Setup

```bash
pip install mcp
python server.py
```

Then add to your Claude Code MCP config:

```json
{
  "mcpServers": {
    "daw": {
      "command": "python",
      "args": ["C:/path/to/daw_mcp/server.py"]
    }
  }
}
```

## Usage

Once connected, tell Claude to:
- `load_project("C:/path/to/beat.als")`
- `list_tracks` to see what's in the session
- `set_volume("Kick", -3)` or `add_device("Master", "limiter", ceiling_db=-0.3)`
- `save_project("C:/path/to/beat_mixed.als")`

## Architecture

- `server.py`: FastMCP tool definitions
- `als_editor.py`: Ableton XML parser/editor with device template generation

## Requirements

- Python 3.10+
- `mcp` package
- Ableton Live `.als` files (any version that uses gzipped XML)
