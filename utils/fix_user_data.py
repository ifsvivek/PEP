import json
import os
import sys

def read_json(filepath):
    """Read and return JSON data from a file"""
    try:
        with open(filepath, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading {filepath}: {e}")
        return {}

def write_json(filepath, data):
    """Write JSON data to a file"""
    try:
        with open(filepath, 'w') as file:
            json.dump(data, file, indent=4)
        return True
    except Exception as e:
        print(f"Error writing to {filepath}: {e}")
        return False

def fix_user_data(username):
    """Fix and repair user data for a specific username"""
    user_file = f'data/users/{username}.json'
    
    if not os.path.exists(user_file):
        print(f"User file not found: {user_file}")
        return False
    
    user_data = read_json(user_file)
    print(f"Original data for {username}:")
    print(json.dumps(user_data, indent=4))
    
    # Ensure all required fields exist
    if 'topics' not in user_data:
        user_data['topics'] = []
    if 'progress' not in user_data:
        user_data['progress'] = {}
    if 'quiz_scores' not in user_data:
        user_data['quiz_scores'] = {}
    
    # Update progress for all topics
    for topic in user_data['topics']:
        if topic not in user_data['progress']:
            user_data['progress'][topic] = 100  # Assuming all viewed topics are completed
    
    # Fix inconsistencies in quiz_scores
    for topic, data in user_data.get('quiz_scores', {}).items():
        if isinstance(data, dict) and 'percentage' in data:
            data['percentage'] = float(data['percentage'])
        elif isinstance(data, dict) and 'score' in data and 'total' in data:
            data['percentage'] = (data['score'] / data['total']) * 100
    
    # Write updated data
    success = write_json(user_file, user_data)
    if success:
        print(f"\nFixed data for {username}:")
        print(json.dumps(user_data, indent=4))
        print("\nUser data has been fixed successfully!")
    else:
        print("\nFailed to update user data.")
    
    return success

def main():
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = input("Enter username to fix: ")
    
    fix_user_data(username)

if __name__ == "__main__":
    main()
