#!/usr/bin/env python3
"""
Ngrok Quick Setup Script
Configures ngrok with auth token and starts demo sharing
"""

import subprocess
import sys
import time
import webbrowser
import json
import urllib.request
from pathlib import Path

# Your ngrok auth token
NGROK_TOKEN = "2yzwPDfPDhhm6TIks6BoDHaAyyb_8a4rsXjrQNj5ZNGNDEp73"

def setup_ngrok_auth():
    """Configure ngrok with auth token"""
    print("🔧 Configuring ngrok with your auth token...")
    try:
        result = subprocess.run(
            ['ngrok', 'config', 'add-authtoken', NGROK_TOKEN],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ Ngrok auth token configured successfully!")
            return True
        else:
            print(f"❌ Error configuring ngrok: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Ngrok not found. Please install it first:")
        print("   1. Download from: https://ngrok.com/download")
        print("   2. Extract to a folder in your PATH")
        print("   3. Run this script again")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_demo_running():
    """Check if demo server is running on port 8000"""
    try:
        urllib.request.urlopen('http://localhost:8000', timeout=2)
        return True
    except:
        return False

def start_demo_if_needed():
    """Start demo server if not already running"""
    if check_demo_running():
        print("✅ Demo server is already running on localhost:8000")
        return True
    
    if not Path('simple_demo.py').exists():
        print("❌ simple_demo.py not found in current directory!")
        return False
    
    print("🚀 Starting demo server...")
    try:
        # Start demo server in background
        subprocess.Popen(
            [sys.executable, 'simple_demo.py'],
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
        )
        
        # Wait for server to start
        for i in range(15):
            time.sleep(1)
            if check_demo_running():
                print("✅ Demo server started successfully!")
                return True
            print(f"⏳ Waiting for server... ({i+1}/15)")
        
        print("❌ Failed to start demo server")
        return False
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False

def create_tunnel():
    """Create ngrok tunnel and display sharing information"""
    print("\n🌐 Creating public tunnel for your demo...")
    
    try:
        # Start ngrok tunnel
        process = subprocess.Popen(
            ['ngrok', 'http', '8000', '--log=stdout'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for tunnel to establish
        print("⏳ Establishing tunnel...")
        time.sleep(4)
        
        # Get tunnel URL from ngrok API
        try:
            response = urllib.request.urlopen('http://localhost:4040/api/tunnels')
            data = json.loads(response.read().decode())
            
            if data['tunnels']:
                public_url = data['tunnels'][0]['public_url']
                
                print("\n" + "="*70)
                print("🎉 SUCCESS! Your demo is now live and shareable!")
                print("="*70)
                print(f"\n🌐 PUBLIC URL: {public_url}")
                print(f"\n📧 READY-TO-SEND EMAIL:")
                print("\n" + "-"*50)
                
                email_template = f"""Subject: 🚨 Live Demo - Accident Intelligence System

Hi [Name],

I'm excited to share our Accident Intelligence System demo with you!

🌐 **Live Demo:** {public_url}

✨ **Key Features to Try:**
• Real-time accident monitoring dashboard
• Click "⚡ Simulate New" to add live accidents
• AI-powered person identification system
• Auto-refreshing statistics every 30 seconds
• Interactive simulation capabilities

🎯 **What to Explore:**
1. Visit the link above
2. Browse the real-time dashboard
3. Try the "Simulate New" button for live testing
4. Watch the system update automatically

📊 **System Highlights:**
• 25 realistic accidents across major US cities
• 4 identified persons with social media profiles
• Advanced deduplication algorithms
• Production-ready scalable architecture

💼 **Business Value:**
• Faster emergency response times
• AI-powered person identification
• Real-time data processing capabilities
• Ready for immediate deployment

The demo is live right now - please explore and let me know your thoughts!

Best regards,
[Your Name]

P.S. The system processes 32+ events/second and is ready for production scaling!"""
                
                print(email_template)
                print("\n" + "-"*50)
                print(f"\n💡 INSTRUCTIONS:")
                print(f"   1. Copy the email template above")
                print(f"   2. Replace [Name] and [Your Name] with actual names")
                print(f"   3. Send to your recipients")
                print(f"   4. They can access the demo immediately!")
                
                print(f"\n🔗 Direct Link: {public_url}")
                print(f"\n⚠️  IMPORTANT: Keep this terminal open to maintain the tunnel")
                print(f"\n🛑 Press Ctrl+C when you want to stop sharing")
                
                # Open the URL in browser
                print(f"\n🌐 Opening demo in your browser...")
                webbrowser.open(public_url)
                
                # Keep the process running
                try:
                    print(f"\n✅ Demo is now live and accessible worldwide!")
                    print(f"\n⏰ Tunnel will remain active until you stop it...")
                    process.wait()
                except KeyboardInterrupt:
                    print("\n\n🛑 Stopping ngrok tunnel...")
                    process.terminate()
                    print("✅ Tunnel stopped. Demo is no longer accessible externally.")
                    print("\n💡 Run this script again anytime to share your demo!")
                
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
    print("🚨 Accident Intelligence Demo - Instant Email Sharing")
    print("=" * 60)
    print("\n🎯 This script will:")
    print("   ✅ Configure ngrok with your auth token")
    print("   ✅ Start your demo server (if needed)")
    print("   ✅ Create a public tunnel")
    print("   ✅ Generate a ready-to-send email")
    print("\n🚀 Starting setup...\n")
    
    # Step 1: Configure ngrok
    if not setup_ngrok_auth():
        return
    
    # Step 2: Ensure demo is running
    if not start_demo_if_needed():
        return
    
    # Step 3: Create public tunnel
    create_tunnel()

if __name__ == "__main__":
    main()