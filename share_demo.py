#!/usr/bin/env python3
"""
Quick Demo Sharing Script
Automatically sets up ngrok tunnel for email sharing
"""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def check_ngrok_installed():
    """Check if ngrok is installed"""
    try:
        result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def install_ngrok():
    """Provide instructions to install ngrok"""
    print("\n🔧 Ngrok not found. Please install it:")
    print("\n1. Visit: https://ngrok.com/download")
    print("2. Download ngrok for Windows")
    print("3. Extract to a folder in your PATH")
    print("4. Create free account at https://ngrok.com/signup")
    print("5. Get your auth token from https://dashboard.ngrok.com/get-started/your-authtoken")
    print("6. Run: ngrok config add-authtoken YOUR_TOKEN")
    print("\nThen run this script again!")
    return False

def check_demo_running():
    """Check if demo server is running on port 8000"""
    try:
        import urllib.request
        urllib.request.urlopen('http://localhost:8000', timeout=2)
        return True
    except:
        return False

def start_demo_server():
    """Start the demo server if not running"""
    if not Path('simple_demo.py').exists():
        print("❌ simple_demo.py not found in current directory!")
        return False
    
    print("🚀 Starting demo server...")
    try:
        # Start demo server in background
        subprocess.Popen([sys.executable, 'simple_demo.py'], 
                        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0)
        
        # Wait for server to start
        for i in range(10):
            time.sleep(1)
            if check_demo_running():
                print("✅ Demo server started successfully!")
                return True
            print(f"⏳ Waiting for server... ({i+1}/10)")
        
        print("❌ Failed to start demo server")
        return False
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False

def create_ngrok_tunnel():
    """Create ngrok tunnel to localhost:8000"""
    print("\n🌐 Creating ngrok tunnel...")
    try:
        # Start ngrok tunnel
        process = subprocess.Popen(
            ['ngrok', 'http', '8000', '--log=stdout'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for tunnel to establish
        time.sleep(3)
        
        # Get tunnel URL from ngrok API
        try:
            import urllib.request
            import json
            
            response = urllib.request.urlopen('http://localhost:4040/api/tunnels')
            data = json.loads(response.read().decode())
            
            if data['tunnels']:
                public_url = data['tunnels'][0]['public_url']
                print(f"\n🎉 SUCCESS! Your demo is now accessible at:")
                print(f"\n🌐 {public_url}")
                print(f"\n📧 EMAIL TEMPLATE:")
                print(f"\n" + "="*60)
                print(f"Subject: 🚨 Live Demo - Accident Intelligence System")
                print(f"\nHi [Name],")
                print(f"\nI'm excited to share our Accident Intelligence System demo!")
                print(f"\n🌐 Live Demo: {public_url}")
                print(f"\n✨ Key Features:")
                print(f"• Real-time accident monitoring dashboard")
                print(f"• Click '⚡ Simulate New' to add live accidents")
                print(f"• AI-powered person identification")
                print(f"• Auto-refreshing statistics every 30 seconds")
                print(f"\n📋 Full demo guide attached (DEMO_GUIDE.md)")
                print(f"\nThe demo is live now - please try it out!")
                print(f"\nBest regards,")
                print(f"[Your Name]")
                print(f"\n" + "="*60)
                print(f"\n💡 TIP: Copy the URL above and paste it in your email!")
                print(f"\n⚠️  Keep this terminal open to maintain the tunnel")
                print(f"\n🛑 Press Ctrl+C to stop sharing")
                
                # Open the URL in browser
                webbrowser.open(public_url)
                
                # Keep the process running
                try:
                    process.wait()
                except KeyboardInterrupt:
                    print("\n\n🛑 Stopping ngrok tunnel...")
                    process.terminate()
                    print("✅ Tunnel stopped. Demo is no longer accessible externally.")
                
                return True
            else:
                print("❌ No tunnels found")
                return False
                
        except Exception as e:
            print(f"❌ Error getting tunnel URL: {e}")
            print("\n💡 Try visiting http://localhost:4040 to see ngrok dashboard")
            return False
            
    except Exception as e:
        print(f"❌ Error creating tunnel: {e}")
        return False

def main():
    print("🚨 Accident Intelligence Demo - Email Sharing Setup")
    print("=" * 55)
    
    # Check if ngrok is installed
    if not check_ngrok_installed():
        install_ngrok()
        return
    
    # Check if demo is running
    if not check_demo_running():
        print("📡 Demo server not detected on localhost:8000")
        if not start_demo_server():
            return
    else:
        print("✅ Demo server is already running on localhost:8000")
    
    # Create ngrok tunnel
    create_ngrok_tunnel()

if __name__ == "__main__":
    main()