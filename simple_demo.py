#!/usr/bin/env python3
"""
Simple Demo Server
Basic HTTP server showcasing the accident intelligence system
"""

import json
import random
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import webbrowser
import threading
import time

# Demo data storage
accidents_data = []
person_profiles = []

def generate_demo_data():
    """Generate realistic demo data"""
    global accidents_data, person_profiles
    
    # Generate accidents
    locations = [
        (40.7128, -74.0060, "New York City"),
        (34.0522, -118.2437, "Los Angeles"),
        (41.8781, -87.6298, "Chicago"),
        (29.7604, -95.3698, "Houston"),
    ]
    
    descriptions = [
        "Multi-vehicle collision on I-95",
        "Single car accident at intersection",
        "Rear-end collision during rush hour",
        "Vehicle rollover on highway",
        "Side-impact crash at traffic light",
        "Head-on collision on rural road",
        "Motorcycle accident on bridge",
        "Truck accident blocking lanes"
    ]
    
    for i in range(25):
        lat, lon, city = random.choice(locations)
        lat += random.uniform(-0.1, 0.1)
        lon += random.uniform(-0.1, 0.1)
        
        accident = {
            "id": f"ACC-{i+1:03d}",
            "timestamp": (datetime.now() - timedelta(hours=random.randint(0, 72))).isoformat(),
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "city": city,
            "description": random.choice(descriptions),
            "severity": random.choice(["Minor", "Moderate", "Severe", "Critical"]),
            "source": random.choice(["Waze RSS", "Traffic Cameras", "911 Calls", "Social Media"]),
            "cluster_id": f"CLUSTER-{random.randint(1, 8)}",
            "person_identified": random.choice([True, False]),
            "vehicles_involved": random.randint(1, 4),
            "injuries": random.randint(0, 6) if random.choice([True, False]) else 0
        }
        accidents_data.append(accident)
    
    # Generate person profiles
    profiles = [
        {
            "name": "John Smith",
            "age": 34,
            "social_profiles": ["@johnsmith_nyc", "john.smith.1234"],
            "confidence_score": 0.85,
            "last_seen": (datetime.now() - timedelta(hours=2)).isoformat(),
            "location": "New York City",
            "status": "Safe - Contacted family"
        },
        {
            "name": "Sarah Johnson",
            "age": 28,
            "social_profiles": ["@sarah_j_official", "sarah.johnson.photos"],
            "confidence_score": 0.92,
            "last_seen": (datetime.now() - timedelta(hours=5)).isoformat(),
            "location": "Los Angeles",
            "status": "Under medical care"
        },
        {
            "name": "Mike Chen",
            "age": 42,
            "social_profiles": ["@mike_chen_la", "mikechen.traveler"],
            "confidence_score": 0.78,
            "last_seen": (datetime.now() - timedelta(hours=12)).isoformat(),
            "location": "Chicago",
            "status": "Missing - Search ongoing"
        },
        {
            "name": "Emma Davis",
            "age": 31,
            "social_profiles": ["@emma_davis_houston", "emma.d.photographer"],
            "confidence_score": 0.89,
            "last_seen": (datetime.now() - timedelta(hours=8)).isoformat(),
            "location": "Houston",
            "status": "Safe - Minor injuries"
        }
    ]
    person_profiles.extend(profiles)

class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/' or path == '/dashboard':
            self.serve_dashboard()
        elif path == '/api/stats':
            self.serve_stats()
        elif path == '/api/accidents':
            self.serve_accidents()
        elif path == '/api/persons':
            self.serve_persons()
        elif path == '/api/simulate':
            self.simulate_accident()
        else:
            self.send_error(404)
    
    def serve_dashboard(self):
        html_content = '''
<!DOCTYPE html>
<html>
<head>
    <title>Accident Intelligence System - Live Demo</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: rgba(255,255,255,0.95); padding: 30px; border-radius: 15px; margin-bottom: 30px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
        .header h1 { color: #2c3e50; font-size: 2.5em; margin-bottom: 10px; }
        .header p { color: #7f8c8d; font-size: 1.2em; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px; text-align: center; box-shadow: 0 8px 25px rgba(0,0,0,0.15); }
        .stat-number { font-size: 3em; font-weight: bold; margin-bottom: 10px; }
        .stat-number.accidents { color: #e74c3c; }
        .stat-number.persons { color: #27ae60; }
        .stat-number.clusters { color: #3498db; }
        .stat-number.rate { color: #f39c12; }
        .stat-label { color: #7f8c8d; font-size: 1.1em; font-weight: 500; }
        .content { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 30px; }
        .panel { background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px; box-shadow: 0 8px 25px rgba(0,0,0,0.15); }
        .panel h3 { color: #2c3e50; margin-bottom: 20px; font-size: 1.5em; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        .accident-item, .person-item { border-left: 4px solid #3498db; padding: 15px; margin-bottom: 15px; background: #f8f9fa; border-radius: 8px; }
        .severity-minor { border-left-color: #27ae60; }
        .severity-moderate { border-left-color: #f39c12; }
        .severity-severe { border-left-color: #e74c3c; }
        .severity-critical { border-left-color: #8e44ad; }
        .refresh-btn { background: linear-gradient(45deg, #3498db, #2980b9); color: white; border: none; padding: 12px 25px; border-radius: 25px; cursor: pointer; font-size: 1em; margin-bottom: 20px; }
        .simulate-btn { background: linear-gradient(45deg, #e74c3c, #c0392b); color: white; border: none; padding: 12px 25px; border-radius: 25px; cursor: pointer; font-size: 1em; margin-left: 10px; }
        .timestamp { color: #7f8c8d; font-size: 0.9em; }
        .confidence { background: #3498db; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.8em; }
        .loading { text-align: center; padding: 20px; color: #7f8c8d; }
        @media (max-width: 768px) {
            .content { grid-template-columns: 1fr; }
            .stats { grid-template-columns: repeat(2, 1fr); }
            .header h1 { font-size: 2em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 Accident Intelligence System</h1>
            <p>Real-time accident monitoring, deduplication, and person identification</p>
            <p><strong>Live Demo Environment</strong></p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number accidents" id="total-accidents">0</div>
                <div class="stat-label">Total Accidents</div>
            </div>
            <div class="stat-card">
                <div class="stat-number persons" id="identified-persons">0</div>
                <div class="stat-label">Persons Identified</div>
            </div>
            <div class="stat-card">
                <div class="stat-number clusters" id="active-clusters">0</div>
                <div class="stat-label">Active Clusters</div>
            </div>
            <div class="stat-card">
                <div class="stat-number rate" id="processing-rate">0</div>
                <div class="stat-label">Events/Hour</div>
            </div>
        </div>
        
        <div class="content">
            <div class="panel">
                <h3>📍 Recent Accidents</h3>
                <button class="refresh-btn" onclick="refreshData()">🔄 Refresh Data</button>
                <button class="simulate-btn" onclick="simulateAccident()">⚡ Simulate New</button>
                <div id="accidents-list" class="loading">Loading accidents...</div>
            </div>
            
            <div class="panel">
                <h3>👤 Identified Persons</h3>
                <div id="persons-list" class="loading">Loading persons...</div>
            </div>
        </div>
    </div>
    
    <script>
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                
                document.getElementById('total-accidents').textContent = stats.total_accidents;
                document.getElementById('identified-persons').textContent = stats.identified_persons;
                document.getElementById('active-clusters').textContent = stats.active_clusters;
                document.getElementById('processing-rate').textContent = stats.processing_rate;
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }
        
        async function loadAccidents() {
            try {
                const response = await fetch('/api/accidents');
                const accidents = await response.json();
                
                const container = document.getElementById('accidents-list');
                container.innerHTML = accidents.slice(0, 8).map(acc => `
                    <div class="accident-item severity-${acc.severity.toLowerCase()}">
                        <strong>${acc.description}</strong><br>
                        <div class="timestamp">📅 ${new Date(acc.timestamp).toLocaleString()}</div>
                        <div class="timestamp">📍 ${acc.city}</div>
                        <div class="timestamp">🚗 ${acc.vehicles_involved} vehicles | 🏥 ${acc.injuries} injuries</div>
                        <div style="margin-top: 8px;">
                            <span class="confidence">${acc.severity}</span>
                            ${acc.person_identified ? '<span style="background: #27ae60; color: white; padding: 2px 6px; border-radius: 10px; font-size: 0.8em; margin-left: 5px;">✅ Person ID</span>' : '<span style="background: #f39c12; color: white; padding: 2px 6px; border-radius: 10px; font-size: 0.8em; margin-left: 5px;">⏳ Processing</span>'}
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error loading accidents:', error);
            }
        }
        
        async function loadPersons() {
            try {
                const response = await fetch('/api/persons');
                const persons = await response.json();
                
                const container = document.getElementById('persons-list');
                container.innerHTML = persons.map(person => `
                    <div class="person-item">
                        <strong>${person.name}, ${person.age}</strong><br>
                        <div class="timestamp">🔗 ${person.social_profiles.join(', ')}</div>
                        <div class="timestamp">📍 ${person.location}</div>
                        <div class="timestamp">👁️ Last seen: ${new Date(person.last_seen).toLocaleString()}</div>
                        <div style="margin-top: 8px; font-weight: bold; color: ${person.status.includes('Safe') ? '#27ae60' : person.status.includes('medical') ? '#f39c12' : '#e74c3c'};">
                            ${person.status}
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error loading persons:', error);
            }
        }
        
        async function simulateAccident() {
            try {
                const response = await fetch('/api/simulate');
                const result = await response.json();
                alert('✅ New accident simulated!\\n\\n' + result.message);
                refreshData();
            } catch (error) {
                console.error('Error simulating accident:', error);
            }
        }
        
        function refreshData() {
            loadStats();
            loadAccidents();
            loadPersons();
        }
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            refreshData();
            setInterval(refreshData, 30000);
        });
    </script>
</body>
</html>
        '''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def serve_stats(self):
        identified_count = sum(1 for acc in accidents_data if acc['person_identified'])
        clusters = len(set(acc['cluster_id'] for acc in accidents_data))
        
        stats = {
            "total_accidents": len(accidents_data),
            "identified_persons": len(person_profiles),
            "active_clusters": clusters,
            "processing_rate": random.randint(15, 45)
        }
        
        self.send_json_response(stats)
    
    def serve_accidents(self):
        sorted_accidents = sorted(accidents_data, key=lambda x: x['timestamp'], reverse=True)
        self.send_json_response(sorted_accidents[:15])
    
    def serve_persons(self):
        self.send_json_response(person_profiles)
    
    def simulate_accident(self):
        locations = [(40.7128, -74.0060, "New York City"), (34.0522, -118.2437, "Los Angeles")]
        lat, lon, city = random.choice(locations)
        lat += random.uniform(-0.05, 0.05)
        lon += random.uniform(-0.05, 0.05)
        
        new_accident = {
            "id": f"SIM-{len(accidents_data)+1:03d}",
            "timestamp": datetime.now().isoformat(),
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "city": city,
            "description": "🔴 LIVE: Simulated accident for demo",
            "severity": random.choice(["Minor", "Moderate", "Severe"]),
            "source": "Live Demo Simulation",
            "cluster_id": f"SIM-CLUSTER-{random.randint(1, 3)}",
            "person_identified": random.choice([True, False]),
            "vehicles_involved": random.randint(1, 3),
            "injuries": random.randint(0, 4)
        }
        
        accidents_data.insert(0, new_accident)
        
        result = {
            "message": f"New accident simulated in {city}",
            "accident_id": new_accident['id'],
            "timestamp": new_accident['timestamp']
        }
        
        self.send_json_response(result)
    
    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def log_message(self, format, *args):
        pass

def start_server():
    generate_demo_data()
    
    server_address = ('localhost', 8000)
    httpd = HTTPServer(server_address, DemoHandler)
    
    print("🚀 Starting Accident Intelligence Demo Server...")
    print(f"📊 Dashboard: http://localhost:8000")
    print(f"🔧 API Stats: http://localhost:8000/api/stats")
    print("\n✨ Demo Features:")
    print("   • Real-time accident monitoring dashboard")
    print("   • Person identification system")
    print("   • Accident clustering and deduplication")
    print("   • Live accident simulation")
    print("\n🎯 Click 'Simulate New' to add live accidents!")
    print("\n⏹️  Press Ctrl+C to stop the server")
    
    def open_browser():
        time.sleep(2)
        webbrowser.open('http://localhost:8000')
    
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Demo server stopped")
        httpd.shutdown()

if __name__ == "__main__":
    start_server()