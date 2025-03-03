import json
import os

def read_json(filepath):
    """Read data from a JSON file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def write_json(filepath, data):
    """Write data to a JSON file"""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def user_exists(username):
    """Check if a user exists"""
    return os.path.exists(f'data/users/{username}.json')

def get_all_users():
    """Get a list of all users"""
    users = []
    for filename in os.listdir('data/users'):
        if filename.endswith('.json'):
            users.append(filename.replace('.json', ''))
    return users
