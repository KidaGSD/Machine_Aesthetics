#!/usr/bin/env python3
import os
import sys
import subprocess
import threading
import time
import webbrowser
import signal

# Get absolute paths
script_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.abspath(os.path.join(script_dir, "..", "frontend_web"))

# Define server and client ports
SERVER_PORT = 3001
CLIENT_PORT = 3000

def start_server():
    """Start the Flask backend server"""
    print("Starting backend server...")
    server_script = os.path.join(script_dir, "server.py")
    
    env = os.environ.copy()
    env["PORT"] = str(SERVER_PORT)
    
    # Run the server in a new process
    server_process = subprocess.Popen(
        [sys.executable, server_script],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    # Read server output in real-time
    while True:
        line = server_process.stdout.readline()
        if not line:
            break
        print(f"[SERVER] {line.strip()}")
    
    return server_process

def start_client():
    """Start the React frontend application"""
    print("Starting frontend client...")
    
    # Original directory to return to later
    original_dir = os.getcwd()
    
    # Change to frontend directory
    os.chdir(frontend_dir)
    
    # Try multiple approaches to find npm
    npm_found = False
    npm_cmd = "npm"
    
    # First try: Use npm directly (if in PATH)
    try:
        subprocess.run([npm_cmd, "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        npm_found = True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("npm not found in PATH, trying alternative locations...")
    
    # Second try: Check for npm in frontend_web/node_modules/.bin
    if not npm_found:
        local_npm = os.path.join(frontend_dir, "node_modules", ".bin", "npm")
        if os.path.exists(local_npm):
            npm_cmd = local_npm
            npm_found = True
            print(f"Found npm in node_modules: {local_npm}")
    
    # Third try: Look for package.json and use "npm start" anyway
    if not npm_found and os.path.exists(os.path.join(frontend_dir, "package.json")):
        npm_found = True
        print("package.json found, will attempt to use npm anyway")
    
    if not npm_found:
        print("Error: npm not found. Will start only the server component.")
        print("You can manually start the frontend by running 'npm start' in the frontend_web directory.")
        os.chdir(original_dir)
        return None
    
    # Check if node_modules exists
    if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
        print("Node modules not found. The 'npm start' command might fail.")
        print("You may need to run 'npm install' in the frontend_web directory first.")
    
    # Set environment variables for the React app
    env = os.environ.copy()
    env["REACT_APP_API_URL"] = f"http://localhost:{SERVER_PORT}"
    env["PORT"] = str(CLIENT_PORT)
    
    try:
        # Start the React development server
        print(f"Starting React app with: {npm_cmd} start")
        client_process = subprocess.Popen(
            [npm_cmd, "start"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Read client output in real-time
        while True:
            line = client_process.stdout.readline()
            if not line:
                break
            print(f"[CLIENT] {line.strip()}")
        
        return client_process
    except Exception as e:
        print(f"Error starting frontend: {e}")
        print(f"Alternative: run 'npm start' manually in {frontend_dir}")
        os.chdir(original_dir)
        return None

def open_browser():
    """Open the browser with the application"""
    # Wait for servers to start
    time.sleep(5)
    
    # Check if frontend directory exists and contains node_modules
    frontend_exists = os.path.exists(os.path.join(frontend_dir, "node_modules"))
    
    # Open browser to appropriate URL
    if frontend_exists:
        url = f"http://localhost:{CLIENT_PORT}"
        print(f"Opening browser at {url} (frontend)")
    else:
        url = f"http://localhost:{SERVER_PORT}"
        print(f"Opening browser at {url} (backend only)")
    
    webbrowser.open(url)

def signal_handler(sig, frame):
    """Handle Ctrl+C to gracefully shut down all processes"""
    print("\nShutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"Starting Machine Aesthetics Texture Lamp Application")
    print(f"Backend directory: {script_dir}")
    print(f"Frontend directory: {frontend_dir}")
    
    # Start backend in a separate thread
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Start client in a separate thread
    client_thread = threading.Thread(target=start_client)
    client_thread.daemon = True
    client_thread.start()
    
    # Open browser in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0) 