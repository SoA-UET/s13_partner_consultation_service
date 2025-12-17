#!/usr/bin/env python3
"""
S13 Service Status Checker

This script checks if all required services and dependencies
are properly configured and running before starting S13.
"""

import os
import sys
import socket
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import pika


def check_mark(condition):
    """Return a check mark or X based on condition"""
    return "✅" if condition else "❌"


def check_mongodb(uri="mongodb://localhost:27017/"):
    """Check MongoDB connection"""
    print("\n📊 Checking MongoDB...")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print(f"  {check_mark(True)} MongoDB is running and accessible")
        print(f"      URI: {uri}")
        client.close()
        return True
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"  {check_mark(False)} MongoDB connection failed")
        print(f"      Error: {e}")
        print(f"      URI: {uri}")
        return False
    except Exception as e:
        print(f"  {check_mark(False)} Unexpected error: {e}")
        return False


def check_rabbitmq(url="amqp://guest:guest@localhost:5672/"):
    """Check RabbitMQ connection"""
    print("\n🐰 Checking RabbitMQ...")
    try:
        params = pika.URLParameters(url)
        params.heartbeat = 0
        params.blocked_connection_timeout = 5
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        print(f"  {check_mark(True)} RabbitMQ is running and accessible")
        print(f"      URL: {url}")
        connection.close()
        return True
    except pika.exceptions.AMQPConnectionError as e:
        print(f"  {check_mark(False)} RabbitMQ connection failed")
        print(f"      Error: {e}")
        print(f"      URL: {url}")
        return False
    except Exception as e:
        print(f"  {check_mark(False)} Unexpected error: {e}")
        return False


def check_port_available(port):
    """Check if a port is available"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', port))
        sock.close()
        return True
    except OSError:
        return False


def check_env_file():
    """Check if .env file exists"""
    print("\n⚙️  Checking configuration...")
    env_exists = os.path.exists('.env')
    print(f"  {check_mark(env_exists)} .env file exists")
    
    if not env_exists:
        print(f"      Run: cp .env.example .env")
        return False
    
    # Load and check key variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'MONGODB_URI',
        'MONGODB_DB_NAME',
        'RABBITMQ_URL',
        'FLASK_PORT'
    ]
    
    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        is_set = value is not None and value != ''
        print(f"  {check_mark(is_set)} {var}: {'Set' if is_set else 'Not set'}")
        if not is_set:
            all_set = False
    
    return env_exists and all_set


def check_dependencies():
    """Check if required Python packages are installed"""
    print("\n📦 Checking Python dependencies...")
    required_packages = [
        'flask',
        'flask_socketio',
        'flask_cors',
        'flask_restx',
        'pymongo',
        'pika',
        'dotenv'
    ]
    
    all_installed = True
    for package in required_packages:
        try:
            __import__(package)
            print(f"  {check_mark(True)} {package}")
        except ImportError:
            print(f"  {check_mark(False)} {package} (not installed)")
            all_installed = False
    
    if not all_installed:
        print(f"\n  Run: uv sync")
    
    return all_installed


def main():
    print("=" * 60)
    print("S13 Partner Consultation Service - Status Check")
    print("=" * 60)
    
    # Load .env if it exists
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check .env configuration
    config_ok = check_env_file()
    
    # Check MongoDB
    mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    mongo_ok = check_mongodb(mongo_uri)
    
    # Check RabbitMQ
    rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
    rabbitmq_ok = check_rabbitmq(rabbitmq_url)
    
    # Check Flask port
    print("\n🌐 Checking Flask port...")
    flask_port = int(os.getenv('FLASK_PORT', 5000))
    port_available = check_port_available(flask_port)
    print(f"  {check_mark(port_available)} Port {flask_port} is {'available' if port_available else 'in use'}")
    
    if not port_available:
        print(f"      To free the port: lsof -ti:{flask_port} | xargs kill -9")
        print(f"      Or change FLASK_PORT in .env")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    all_checks = [
        ("Python dependencies", deps_ok),
        ("Configuration (.env)", config_ok),
        ("MongoDB connection", mongo_ok),
        ("RabbitMQ connection", rabbitmq_ok),
        ("Flask port available", port_available)
    ]
    
    for check_name, status in all_checks:
        print(f"  {check_mark(status)} {check_name}")
    
    all_ok = all(status for _, status in all_checks)
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ All checks passed! You're ready to run:")
        print("   uv run -m app")
        print("   or")
        print("   ./start_s13.sh")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("   See S13_README.md for detailed setup instructions.")
    print("=" * 60)
    
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
