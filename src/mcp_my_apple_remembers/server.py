import logging
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
import json
import os
import asyncio
from datetime import datetime
import sys

# Import MCP server libraries
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mcp_my_apple_remembers')
logger.setLevel(logging.INFO)

# Load environment variables for SSH connection
MACOS_HOST = os.environ.get('MACOS_HOST', '')
MACOS_PORT = int(os.environ.get('MACOS_PORT', '22'))  # Use SSH default port
MACOS_USERNAME = os.environ.get('MACOS_USERNAME', '')
MACOS_PASSWORD = os.environ.get('MACOS_PASSWORD', '')

# Log environment variable status (without exposing actual values)
logger.info(f"MACOS_HOST from environment: {'Set' if MACOS_HOST else 'Not set'}")
logger.info(f"MACOS_PORT from environment: {MACOS_PORT}")
logger.info(f"MACOS_USERNAME from environment: {'Set' if MACOS_USERNAME else 'Not set'}")
logger.info(f"MACOS_PASSWORD from environment: {'Set' if MACOS_PASSWORD else 'Not set (Required)'}")

# Validate required environment variables
if not MACOS_HOST:
    logger.error("MACOS_HOST environment variable is required but not set")
    raise ValueError("MACOS_HOST environment variable is required but not set")

if not MACOS_PASSWORD:
    logger.error("MACOS_PASSWORD environment variable is required but not set")
    raise ValueError("MACOS_PASSWORD environment variable is required but not set")

async def main():
    """Run the My Apple Remembers MCP server."""
    logger.info("My Apple Remembers server starting")
    server = Server("my-apple-remembers")

    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        return []

    @server.read_resource()
    async def handle_read_resource(uri: types.AnyUrl) -> str:
        return ""

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available tools"""
        return [
            types.Tool(
                name="my_apple_recall_memory",
                description="Run Apple Script on a remote MacOs machine. This call should be used to recall the apple notes, apple calendar, imessages, chat messages, files, context or any other information of a MacOs machine can have access to.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code_snippet": {"type": "string", "description": "AppleScript code to execute on the remote machine. Can be a single line or multi-line script. You should prefer multi-line scripts for complex operations."},
                        "timeout": {"type": "integer", "description": "Command execution timeout in seconds (default: 60)"}
                    },
                    "required": ["code_snippet"]
                },
            ),
            types.Tool(
                name="my_apple_save_memory",
                description="Run Apple Script on a remote MacOs machine. This call should be used to save relevant information to the apple notes. You decide what information to save. You should always add a new notes with a timestamp as the title.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code_snippet": {"type": "string", "description": "AppleScript code to execute on the remote machine. Can be a single line or multi-line script. You should prefer multi-line scripts for complex operations."},
                        "timeout": {"type": "integer", "description": "Command execution timeout in seconds (default: 60)"}
                    },
                    "required": ["code_snippet"]
                },
            )
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool execution requests"""
        try:
            logger.info(f"Tool execution requested: {name}")
            
            if not arguments:
                arguments = {}
            
            if name == "my_apple_recall_memory" or name == "my_apple_save_memory":
                # Use environment variables
                ## Since this is running inside the docker, if user want to connect to the local macos machine, we need to use the host.docker.internal
                host = MACOS_HOST
                if host == "localhost" or host == "127.0.0.1" or host == "0.0.0.0":
                    host = "host.docker.internal"
                port = MACOS_PORT
                username = MACOS_USERNAME
                password = MACOS_PASSWORD

                logger.info(f"Connecting to {host}:{port} as {username}")
                
                # Get parameters from arguments
                code_snippet = arguments.get("code_snippet")
                timeout = int(arguments.get("timeout", 60))
                
                # Check if we have required parameters
                if not code_snippet:
                    logger.error("Missing required parameter: code_snippet")
                    raise ValueError("code_snippet is required to execute on the remote machine")
                
                try:
                    # Import required libraries
                    import paramiko
                    import io
                    import base64
                    import time
                    import uuid
                    from socket import timeout as socket_timeout
                except ImportError as e:
                    logger.error(f"Missing required libraries: {str(e)}")
                    return [types.TextContent(
                        type="text",
                        text=f"Error: Missing required libraries. Please install paramiko: {str(e)}"
                    )]
                
                # Initialize SSH client
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                try:
                    # Connect with password
                    ssh.connect(
                        hostname=host,
                        port=port,
                        username=username,
                        password=password,
                        timeout=10
                    )
                    
                    logger.info(f"Successfully connected to {host}")
                    
                    # Determine execution method based on script complexity
                    is_multiline = '\n' in code_snippet
                    
                    if is_multiline:
                        # File-based execution for multi-line scripts
                        
                        # Generate a unique temporary filename
                        temp_script_filename = f"/tmp/applescript_{uuid.uuid4().hex}.scpt"
                        
                        # Open SFTP session and upload the script
                        sftp = ssh.open_sftp()
                        
                        try:
                            # Create the script file on the remote system
                            with sftp.open(temp_script_filename, 'w') as remote_file:
                                remote_file.write(code_snippet)
                            
                            logger.info(f"Script file uploaded to {temp_script_filename}")
                            
                            # Set execute permissions
                            sftp.chmod(temp_script_filename, 0o755)
                            
                            # Execute the script file
                            command = f'osascript {temp_script_filename}'
                            logger.info(f"Executing AppleScript file: {command}")
                            
                        finally:
                            # Always close SFTP after file operations
                            sftp.close()
                            
                    else:
                        # Direct command execution for single-line scripts
                        escaped_script = code_snippet.replace('"', '\\"')
                        command = f'osascript -e "{escaped_script}"'
                        logger.info(f"Executing AppleScript command")
                    
                    # Execute command with PTY (pseudo-terminal) for interactive commands
                    channel = ssh.get_transport().open_session()
                    channel.get_pty()
                    channel.settimeout(timeout)
                    channel.exec_command(command)
                    
                    # Initialize byte buffers instead of strings
                    stdout_buffer = b""
                    stderr_buffer = b""
                    
                    # Read from stdout and stderr until closed or timeout
                    start_time = time.time()
                    
                    while not channel.exit_status_ready():
                        if channel.recv_ready():
                            chunk = channel.recv(1024)
                            stdout_buffer += chunk
                        if channel.recv_stderr_ready():
                            chunk = channel.recv_stderr(1024)
                            stderr_buffer += chunk
                        
                        # Check timeout
                        elapsed = time.time() - start_time
                        if elapsed > timeout:
                            logger.warning(f"Command execution timed out after {elapsed:.2f} seconds")
                            raise TimeoutError(f"Command execution timed out after {timeout} seconds")
                        
                        # Small sleep to prevent CPU spinning
                        time.sleep(0.1)
                    
                    # Get any remaining output
                    while channel.recv_ready():
                        chunk = channel.recv(1024)
                        stdout_buffer += chunk
                    while channel.recv_stderr_ready():
                        chunk = channel.recv_stderr(1024)
                        stderr_buffer += chunk
                    
                    # Get exit status
                    exit_status = channel.recv_exit_status()
                    logger.info(f"Command completed with exit status: {exit_status}")
                    
                    # Cleanup temp file if created
                    if is_multiline:
                        try:
                            # Open a new SFTP session for cleanup
                            sftp = ssh.open_sftp()
                            sftp.remove(temp_script_filename)
                            sftp.close()
                            logger.info(f"Script file {temp_script_filename} removed")
                        except Exception as e:
                            logger.warning(f"Failed to remove script file: {str(e)}")
                    
                    # Decode complete buffers once all data is received
                    try:
                        output = stdout_buffer.decode('utf-8')
                    except UnicodeDecodeError:
                        # Fallback to error-tolerant decoding if strict decoding fails
                        logger.warning("UTF-8 decoding failed for stdout, using replacement character for errors")
                        output = stdout_buffer.decode('utf-8', errors='replace')
                    
                    try:
                        stderr_output = stderr_buffer.decode('utf-8')
                    except UnicodeDecodeError:
                        logger.warning("UTF-8 decoding failed for stderr, using replacement character for errors")
                        stderr_output = stderr_buffer.decode('utf-8', errors='replace')
                    
                    # Format response
                    response = f"Command executed with exit status: {exit_status}\n\n"
                    
                    if output:
                        response += f"STDOUT:\n{output}\n\n"
                    
                    if stderr_output:
                        response += f"STDERR:\n{stderr_output}\n"
                    
                    return [types.TextContent(type="text", text=response)]
                    
                except paramiko.AuthenticationException:
                    logger.error(f"Authentication failed for {username}@{host}:{port}")
                    return [types.TextContent(
                        type="text", 
                        text=f"Authentication failed for {username}@{host}:{port}. Check credentials."
                    )]
                except socket_timeout:
                    logger.error(f"Connection timeout while connecting to {host}:{port}")
                    return [types.TextContent(
                        type="text",
                        text=f"Connection timeout while connecting to {host}:{port}."
                    )]
                except TimeoutError as e:
                    logger.error(f"Command execution timed out: {str(e)}")
                    return [types.TextContent(
                        type="text",
                        text=str(e)
                    )]
                except Exception as e:
                    logger.error(f"Error executing SSH command: {str(e)}")
                    return [types.TextContent(
                        type="text",
                        text=f"Error executing SSH command: {str(e)}"
                    )]
                finally:
                    # Close SSH connection
                    ssh.close()
                    logger.info(f"SSH connection to {host} closed")
            else:
                logger.error(f"Unknown tool requested: {name}")
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.error(f"Error in handle_call_tool: {str(e)}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running with stdio transport")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="my-apple-remembers",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    try:
        # Run the server
        asyncio.run(main())
    except ValueError as e:
        logger.error(f"Initialization failed: {str(e)}")
        print(f"ERROR: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"ERROR: Unexpected error occurred: {str(e)}")
        sys.exit(1) 