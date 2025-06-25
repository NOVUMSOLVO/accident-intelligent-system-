#!/usr/bin/env python3
"""
Setup Script for Real-Time Accident Detection & Person Identification System
Handles environment setup, dependency installation, and initial configuration
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional


class SystemSetup:
    """Setup and configuration manager for the accident detection system"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "venv"
        self.logs_dir = self.project_root / "logs"
        self.data_dir = self.project_root / "data"
        self.checkpoints_dir = self.project_root / "checkpoints"
        
    def print_banner(self):
        """Print setup banner"""
        print("="*70)
        print("Real-Time Accident Detection & Person Identification System")
        print("Setup and Configuration Tool")
        print("="*70)
        print()
    
    def check_python_version(self) -> bool:
        """Check if Python version is compatible"""
        print("Checking Python version...")
        
        version = sys.version_info
        if version.major != 3 or version.minor < 8:
            print(f"❌ Python 3.8+ required, found {version.major}.{version.minor}")
            return False
        
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
        return True
    
    def check_system_requirements(self) -> Dict[str, bool]:
        """Check system requirements"""
        print("\nChecking system requirements...")
        
        requirements = {
            'docker': self._check_command('docker --version'),
            'docker-compose': self._check_command('docker-compose --version'),
            'java': self._check_command('java -version'),
            'git': self._check_command('git --version')
        }
        
        for req, available in requirements.items():
            status = "✅" if available else "❌"
            print(f"  {status} {req}")
        
        return requirements
    
    def _check_command(self, command: str) -> bool:
        """Check if a command is available"""
        try:
            subprocess.run(
                command.split(),
                capture_output=True,
                check=True,
                timeout=10
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def create_virtual_environment(self) -> bool:
        """Create Python virtual environment"""
        print("\nSetting up Python virtual environment...")
        
        if self.venv_path.exists():
            print("  Virtual environment already exists")
            return True
        
        try:
            subprocess.run([
                sys.executable, '-m', 'venv', str(self.venv_path)
            ], check=True)
            print("  ✅ Virtual environment created")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to create virtual environment: {e}")
            return False
    
    def install_python_dependencies(self) -> bool:
        """Install Python dependencies"""
        print("\nInstalling Python dependencies...")
        
        # Determine pip executable
        if os.name == 'nt':  # Windows
            pip_exe = self.venv_path / "Scripts" / "pip.exe"
        else:  # Unix-like
            pip_exe = self.venv_path / "bin" / "pip"
        
        if not pip_exe.exists():
            print("  ❌ Virtual environment pip not found")
            return False
        
        requirements_file = self.project_root / "requirements.txt"
        if not requirements_file.exists():
            print("  ❌ requirements.txt not found")
            return False
        
        try:
            # Determine Python executable
            if os.name == 'nt':  # Windows
                python_exe = self.venv_path / "Scripts" / "python.exe"
            else:  # Unix-like
                python_exe = self.venv_path / "bin" / "python"
            
            # Upgrade pip first using python -m pip (handles spaces in paths better)
            subprocess.run([
                str(python_exe), '-m', 'pip', 'install', '--upgrade', 'pip'
            ], check=True)
            
            # Install requirements using python -m pip
            subprocess.run([
                str(python_exe), '-m', 'pip', 'install', '-r', str(requirements_file)
            ], check=True)
            
            print("  ✅ Python dependencies installed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to install dependencies: {e}")
            return False
    
    def create_directories(self) -> bool:
        """Create necessary directories"""
        print("\nCreating project directories...")
        
        directories = [
            self.logs_dir,
            self.data_dir,
            self.checkpoints_dir,
            self.project_root / "data" / "raw",
            self.project_root / "data" / "processed",
            self.project_root / "data" / "output",
            self.project_root / "logs" / "application",
            self.project_root / "logs" / "spark",
            self.project_root / "logs" / "kafka"
        ]
        
        try:
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                print(f"  ✅ {directory.relative_to(self.project_root)}")
            return True
        except Exception as e:
            print(f"  ❌ Failed to create directories: {e}")
            return False
    
    def setup_environment_file(self) -> bool:
        """Setup environment configuration file"""
        print("\nSetting up environment configuration...")
        
        env_example = self.project_root / ".env.example"
        env_file = self.project_root / ".env"
        
        if not env_example.exists():
            print("  ❌ .env.example not found")
            return False
        
        if env_file.exists():
            print("  .env file already exists")
            return True
        
        try:
            shutil.copy2(env_example, env_file)
            print("  ✅ .env file created from template")
            print("  ⚠️  Please edit .env file with your API keys and configuration")
            return True
        except Exception as e:
            print(f"  ❌ Failed to create .env file: {e}")
            return False
    
    def setup_docker_services(self) -> bool:
        """Setup Docker services"""
        print("\nSetting up Docker services...")
        
        docker_compose_file = self.project_root / "docker-compose.yml"
        if not docker_compose_file.exists():
            print("  ❌ docker-compose.yml not found")
            return False
        
        try:
            # Pull Docker images
            print("  Pulling Docker images...")
            subprocess.run([
                'docker-compose', 'pull'
            ], cwd=self.project_root, check=True)
            
            print("  ✅ Docker images pulled successfully")
            print("  ℹ️  Run 'docker-compose up -d' to start services")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to pull Docker images: {e}")
            return False
    
    def create_sample_config(self) -> bool:
        """Create sample configuration files"""
        print("\nCreating sample configuration files...")
        
        try:
            # Create sample Kafka topics script
            kafka_script = self.project_root / "scripts" / "create_kafka_topics.sh"
            kafka_script.parent.mkdir(exist_ok=True)
            
            kafka_script_content = '''#!/bin/bash
# Create Kafka topics for accident detection system

echo "Creating Kafka topics..."

# Wait for Kafka to be ready
sleep 30

# Create topics
docker-compose exec kafka kafka-topics.sh --create --topic accidents-raw --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
docker-compose exec kafka kafka-topics.sh --create --topic accidents-processed --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
docker-compose exec kafka kafka-topics.sh --create --topic accidents-enriched --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
docker-compose exec kafka kafka-topics.sh --create --topic social-profiles --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

echo "Kafka topics created successfully!"
'''
            
            with open(kafka_script, 'w') as f:
                f.write(kafka_script_content)
            
            # Make script executable on Unix-like systems
            if os.name != 'nt':
                os.chmod(kafka_script, 0o755)
            
            print("  ✅ Kafka topics script created")
            
            # Create sample run script
            run_script = self.project_root / "run.py"
            run_script_content = '''#!/usr/bin/env python3
"""
Quick start script for the accident detection system
"""

import subprocess
import sys
import time
from pathlib import Path

def main():
    project_root = Path(__file__).parent
    
    print("Starting Accident Detection System...")
    
    # Check if Docker services are running
    try:
        result = subprocess.run(['docker-compose', 'ps'], 
                              cwd=project_root, capture_output=True, text=True)
        if 'Up' not in result.stdout:
            print("Starting Docker services...")
            subprocess.run(['docker-compose', 'up', '-d'], cwd=project_root, check=True)
            print("Waiting for services to start...")
            time.sleep(30)
    except subprocess.CalledProcessError:
        print("Failed to start Docker services")
        return
    
    # Run the main application
    try:
        if sys.platform == 'win32':
            python_exe = project_root / "venv" / "Scripts" / "python.exe"
        else:
            python_exe = project_root / "venv" / "bin" / "python"
        
        subprocess.run([str(python_exe), "main.py"], cwd=project_root)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
'''
            
            with open(run_script, 'w') as f:
                f.write(run_script_content)
            
            print("  ✅ Run script created")
            return True
            
        except Exception as e:
            print(f"  ❌ Failed to create configuration files: {e}")
            return False
    
    def print_next_steps(self):
        """Print next steps for the user"""
        print("\n" + "="*70)
        print("SETUP COMPLETE!")
        print("="*70)
        print("\nNext steps:")
        print("\n1. Configure your environment:")
        print("   - Edit .env file with your API keys")
        print("   - Update configuration as needed")
        print("\n2. Start Docker services:")
        print("   docker-compose up -d")
        print("\n3. Create Kafka topics:")
        if os.name == 'nt':
            print("   .\\scripts\\create_kafka_topics.sh")
        else:
            print("   ./scripts/create_kafka_topics.sh")
        print("\n4. Run the system:")
        print("   python run.py")
        print("   # OR")
        print("   python main.py")
        print("\n5. Monitor logs:")
        print("   tail -f logs/application/app.log")
        print("\nFor more information, see README.md")
        print()
    
    def run_setup(self):
        """Run the complete setup process"""
        self.print_banner()
        
        # Check Python version
        if not self.check_python_version():
            return False
        
        # Check system requirements
        requirements = self.check_system_requirements()
        
        # Create virtual environment
        if not self.create_virtual_environment():
            return False
        
        # Install Python dependencies
        if not self.install_python_dependencies():
            return False
        
        # Create directories
        if not self.create_directories():
            return False
        
        # Setup environment file
        if not self.setup_environment_file():
            return False
        
        # Setup Docker services (if Docker is available)
        if requirements.get('docker') and requirements.get('docker-compose'):
            self.setup_docker_services()
        else:
            print("\n⚠️  Docker not available, skipping Docker setup")
        
        # Create sample configuration
        if not self.create_sample_config():
            return False
        
        # Print next steps
        self.print_next_steps()
        
        return True


def main():
    """Main setup function"""
    setup = SystemSetup()
    
    try:
        success = setup.run_setup()
        if success:
            print("Setup completed successfully!")
            sys.exit(0)
        else:
            print("Setup failed. Please check the errors above.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nSetup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error during setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()