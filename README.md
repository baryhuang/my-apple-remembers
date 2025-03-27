# MCP Server - My Apple Remembers
**A simple MCP server that enables AI to execute AppleScript on remote macOS systems.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

* **AppleScript Execution**: Run AppleScript commands on remote macOS systems
* **Minimal Setup**: Just enable SSH on the target Mac 
* **Universal Compatibility**: Works with all macOS versions

## Installation
- [Enable SSH on MacOS](https://support.apple.com/guide/mac-help/allow-a-remote-computer-to-access-your-mac-mchlp1066/mac)
- [Install Docker Desktop for local Mac](https://docs.docker.com/desktop/setup/install/mac-install/)
- [Add this MCP server to Claude Desktop](https://modelcontextprotocol.io/quickstart/user)

You can configure Claude Desktop to use the Docker image by adding the following to your Claude configuration:
```json
{
  "mcpServers": {
    "my-apple-remembers": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "buryhuang/mcp-my-apple-remembers:latest"
      ]
    }
  }
}
```

## Developer Instructions
### Clone the repo
```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-my-apple-remembers.git
cd mcp-my-apple-remembers
```

### Building the Docker Image

```bash
# Build the Docker image
docker build -t mcp-my-apple-remembers .
```

## Usage with Claude Desktop

### Docker Usage

You can configure Claude Desktop to use the Docker image by adding the following to your Claude configuration:

```json
{
  "mcpServers": {
    "my-apple-remembers": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "-e",
        "MACOS_USERNAME=your_macos_username",
        "-e",
        "MACOS_PASSWORD=your_macos_password",
        "-e",
        "MACOS_HOST=your_macos_hostname_or_ip",
        "--rm",
        "your-docker-username/mcp-my-apple-remembers:latest"
      ]
    }
  }
}
```

## Usage

The server provides AppleScript execution functionality through MCP tools.

### Tools Specifications

#### remote_macos_apple_script
Run AppleScript commands on a remote macOS system. Example:
```json
{
  "apple_script": "tell application \"System Events\" to get the name of every process",
  "timeout": 60
}
```

All tools require macOS SSH access, with host and password.

## Security Note

Always use secure, authenticated connections when accessing remote macOS machines. This tool should only be used with servers you trust and have permission to access.

## License

See the LICENSE file for details. 
