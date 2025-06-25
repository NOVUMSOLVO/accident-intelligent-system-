#!/usr/bin/env python3
"""
Demo Web Application
Fast demo showcasing the accident intelligence system capabilities
"""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Accident Intelligence Demo", version="1.0.0")

# Demo data models
class AccidentData(BaseModel):
    id: str
    timestamp: datetime
    latitude: float
    longitude: float
    description: str
    severity: str
    source: str
    cluster_id: Optional[str] = None
    person_identified: bool = False

class PersonProfile(BaseModel):
    name: str
    social_profiles: List[str]
    confidence_score: float
    last_seen: datetime

# Mock data storage
accidents_db: List[AccidentData] = []
person_profiles: List[PersonProfile] = []

# Generate demo data
def generate_demo_accidents():
    """Generate realistic demo accident data"""
    locations = [
        (40.7128, -74.0060),  # NYC
        (34.0522, -118.2437), # LA
        (41.8781, -87.6298),  # Chicago
        (29.7604, -95.3698),  # Houston
    ]
    
    for i in range(20):
        lat, lon = random.choice(locations)
        # Add some random variation
        lat += random.uniform(-0.1, 0.1)
        lon += random.uniform(-0.1, 0.1)
        
        accident = AccidentData(
            id=f"acc_{i:03d}",
            timestamp=datetime.now() - timedelta(hours=random.randint(0, 48)),
            latitude=lat,
            longitude=lon,
            description=random.choice([
                "Vehicle collision on highway",
                "Multi-car accident at intersection",
                "Single vehicle rollover",
                "Rear-end collision",
                "Side-impact crash"
            ]),
            severity=random.choice(["Minor", "Moderate", "Severe"]),
            source="Waze RSS",
            cluster_id=f"cluster_{random.randint(1, 5)}",
            person_identified=random.choice([True, False])
        )
        accidents_db.append(accident)

def generate_demo_profiles():
    """Generate demo person profiles"""
    profiles = [
        PersonProfile(
            name="John Smith",
            social_profiles=["@johnsmith_nyc", "john.smith.1234"],
            confidence_score=0.85,
            last_seen=datetime.now() - timedelta(hours=2)
        ),
        PersonProfile(
            name="Sarah Johnson",
            social_profiles=["@sarah_j_official", "sarah.johnson.photos"],
            confidence_score=0.92,
            last_seen=datetime.now() - timedelta(hours=5)
        ),
        PersonProfile(
            name="Mike Chen",
            social_profiles=["@mike_chen_la", "mikechen.traveler"],
            confidence_score=0.78,
            last_seen=datetime.now() - timedelta(hours=12)
        )
    ]
    person_profiles.extend(profiles)

# Initialize demo data
generate_demo_accidents()
generate_demo_profiles()

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Accident Intelligence System - Demo</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
            .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stat-number { font-size: 2em; font-weight: bold; color: #3498db; }
            .stat-label { color: #7f8c8d; margin-top: 5px; }
            .content { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .panel { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .accident-item { border-bottom: 1px solid #eee; padding: 10px 0; }
            .accident-item:last-child { border-bottom: none; }
            .severity-minor { color: #27ae60; }
            .severity-moderate { color: #f39c12; }
            .severity-severe { color: #e74c3c; }
            .status-identified { color: #27ae60; }
            .status-pending { color: #f39c12; }
            .refresh-btn { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
            .refresh-btn:hover { background: #2980b9; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚨 Accident Intelligence System - Live Demo</h1>
            <p>Real-time accident monitoring, deduplication, and person identification</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number" id="total-accidents">0</div>
                <div class="stat-label">Total Accidents</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="identified-persons">0</div>
                <div class="stat-label">Persons Identified</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="active-clusters">0</div>
                <div class="stat-label">Active Clusters</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="processing-rate">0</div>
                <div class="stat-label">Events/Hour</div>
            </div>
        </div>
        
        <div class="content">
            <div class="panel">
                <h3>📍 Recent Accidents</h3>
                <button class="refresh-btn" onclick="refreshData()">Refresh Data</button>
                <div id="accidents-list"></div>
            </div>
            
            <div class="panel">
                <h3>👤 Identified Persons</h3>
                <div id="persons-list"></div>
            </div>
        </div>
        
        <div class="panel" style="margin-top: 20px;">
            <h3>📊 System Performance</h3>
            <canvas id="performanceChart" width="400" height="200"></canvas>
        </div>
        
        <script>
            async function loadStats() {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                
                document.getElementById('total-accidents').textContent = stats.total_accidents;
                document.getElementById('identified-persons').textContent = stats.identified_persons;
                document.getElementById('active-clusters').textContent = stats.active_clusters;
                document.getElementById('processing-rate').textContent = stats.processing_rate;
            }
            
            async function loadAccidents() {
                const response = await fetch('/api/accidents');
                const accidents = await response.json();
                
                const container = document.getElementById('accidents-list');
                container.innerHTML = accidents.map(acc => `
                    <div class="accident-item">
                        <strong>${acc.description}</strong><br>
                        <small>📅 ${new Date(acc.timestamp).toLocaleString()}</small><br>
                        <small>📍 ${acc.latitude.toFixed(4)}, ${acc.longitude.toFixed(4)}</small><br>
                        <span class="severity-${acc.severity.toLowerCase()}">${acc.severity}</span>
                        <span class="${acc.person_identified ? 'status-identified' : 'status-pending'}">
                            ${acc.person_identified ? '✅ Person ID' : '⏳ Processing'}
                        </span>
                    </div>
                `).join('');
            }
            
            async function loadPersons() {
                const response = await fetch('/api/persons');
                const persons = await response.json();
                
                const container = document.getElementById('persons-list');
                container.innerHTML = persons.map(person => `
                    <div class="accident-item">
                        <strong>${person.name}</strong><br>
                        <small>🔗 ${person.social_profiles.join(', ')}</small><br>
                        <small>📊 Confidence: ${(person.confidence_score * 100).toFixed(1)}%</small><br>
                        <small>👁️ Last seen: ${new Date(person.last_seen).toLocaleString()}</small>
                    </div>
                `).join('');
            }
            
            function createPerformanceChart() {
                const ctx = document.getElementById('performanceChart').getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: ['1h ago', '45m ago', '30m ago', '15m ago', 'Now'],
                        datasets: [{
                            label: 'Accidents Processed',
                            data: [12, 19, 15, 25, 22],
                            borderColor: '#3498db',
                            tension: 0.1
                        }, {
                            label: 'Persons Identified',
                            data: [5, 8, 6, 12, 9],
                            borderColor: '#27ae60',
                            tension: 0.1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        }
                    }
                });
            }
            
            function refreshData() {
                loadStats();
                loadAccidents();
                loadPersons();
            }
            
            // Initialize dashboard
            document.addEventListener('DOMContentLoaded', function() {
                refreshData();
                createPerformanceChart();
                
                // Auto-refresh every 30 seconds
                setInterval(refreshData, 30000);
            });
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    identified_count = sum(1 for acc in accidents_db if acc.person_identified)
    clusters = len(set(acc.cluster_id for acc in accidents_db if acc.cluster_id))
    
    return {
        "total_accidents": len(accidents_db),
        "identified_persons": identified_count,
        "active_clusters": clusters,
        "processing_rate": random.randint(15, 35)  # Simulated
    }

@app.get("/api/accidents")
async def get_accidents():
    """Get recent accidents"""
    # Return last 10 accidents, sorted by timestamp
    sorted_accidents = sorted(accidents_db, key=lambda x: x.timestamp, reverse=True)
    return sorted_accidents[:10]

@app.get("/api/persons")
async def get_persons():
    """Get identified persons"""
    return person_profiles

@app.post("/api/simulate")
async def simulate_new_accident():
    """Simulate a new accident for demo purposes"""
    locations = [(40.7128, -74.0060), (34.0522, -118.2437)]
    lat, lon = random.choice(locations)
    lat += random.uniform(-0.05, 0.05)
    lon += random.uniform(-0.05, 0.05)
    
    new_accident = AccidentData(
        id=f"acc_{len(accidents_db):03d}",
        timestamp=datetime.now(),
        latitude=lat,
        longitude=lon,
        description="Live simulated accident",
        severity=random.choice(["Minor", "Moderate", "Severe"]),
        source="Live Demo",
        cluster_id=f"cluster_{random.randint(1, 5)}",
        person_identified=random.choice([True, False])
    )
    
    accidents_db.append(new_accident)
    return {"message": "New accident simulated", "accident": new_accident}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": "1.0.0",
        "components": {
            "database": "connected",
            "kafka": "simulated",
            "spark": "simulated",
            "ai_engine": "active"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Accident Intelligence Demo...")
    print("📊 Dashboard: http://localhost:8000")
    print("🔧 API Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)