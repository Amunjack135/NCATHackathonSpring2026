import requests
import json
import os
import csv
import time
from pathlib import Path

def get_pump_data():
    """
    Fetches pump data from the /api/pump-statuses endpoint.
    Returns a list of dictionaries containing pump metrics.
    """
    url = 'https://iotaspheresystems.com/api/pump-statuses'
    pumps_data = []
    
    try:
        response = requests.post(url, json={}, timeout=10, verify=False)
        print(f"Fetching pump data from {url}")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Convert API response format to pump_data format
            for pump_id, pump_info in data.items():
                pump_data = {
                    'pump_id': pump_info.get('pump-id', pump_id),
                    'temperature': float(pump_info.get('temperature', 0)),
                    'pressure': float(pump_info.get('pressure', 0)),
                    'flow_rate': float(pump_info.get('flow-rate', 0)),
                    'rpm': float(pump_info.get('rpm', 0)),
                    'operational_hours': float(pump_info.get('operational-hours', 0)),
                    'requires_maintenance': pump_info.get('requires-maintenance', False),
                    'load_percent': float(pump_info.get('load-percent', 0)),
                    'is_running': pump_info.get('is-running', False)
                }
                pumps_data.append(pump_data)
        else:
            print(f"Error: Received status code {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching pump data: {e}")
    
    return pumps_data


def request_pump_failure_reason(pump_data):
    """
    Sends pump data to the AI API endpoint to get failure reason explanations.
    Includes pump_id and timestamp in the request.
    """
    url = 'https://iotaspheresystems.com/api/pump-failure-reason'
    
    # Create minimal payload with required fields, ensuring valid values
    payload = {
        'pump-id': pump_data['pump_id'],
        'timestamp': 1,
        'temperature': max(0, pump_data['temperature']),  # Ensure non-negative
        'pressure': max(0, pump_data['pressure']),  # Ensure non-negative
        'flow_rate': max(0, pump_data['flow_rate']),  # Ensure non-negative
        'rpm': max(0, pump_data['rpm']),  # Ensure non-negative
        'operational_hours': max(0, pump_data['operational_hours']),  # Ensure non-negative
        'requires_maintenance': pump_data['requires_maintenance'],
        'load_percent': max(0, min(100, pump_data['load_percent'])),  # Clamp to 0-100
        'is_running': pump_data['is_running']
    }
    
    try:
        print(f"  Sending payload: {json.dumps(payload)}")
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=payload, headers=headers, timeout=10, verify=False)
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            print(f"  Error: {response.status_code} - {response.reason}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None


def main():
    """Main function to fetch pump data and request AI failure reasons."""
    print("Fetching pump data...")
    pump_data = get_pump_data()
    
    if not pump_data:
        print("No pump data found.")
        return
    
    print(f"Found {len(pump_data)} pumps")
    
    for pump in pump_data:
        print(f"\nProcessing Pump: {pump['pump_id']}")
        print(f"  Temperature: {pump['temperature']}°C")
        print(f"  Pressure: {pump['pressure']} PSI")
        print(f"  Load: {pump['load_percent']}%")
        print(f"  Requires Maintenance: {pump['requires_maintenance']}")
        
        # Request AI explanation for this pump
        result = request_pump_failure_reason(pump)
        
        if result:
            print(f"  AI Failure Reason: {result}")
        else:
            print("  Failed to get AI explanation")


if __name__ == '__main__':
    main()
