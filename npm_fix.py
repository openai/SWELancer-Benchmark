import json

def remove_integrity_keys(data):
    if isinstance(data, dict):
        # If it's a dictionary, remove the "integrity" key if present
        if "integrity" in data:
            del data["integrity"]
        # Recursively apply this function to all dictionary values
        for key, value in data.items():
            remove_integrity_keys(value)
    elif isinstance(data, list):
        # If it's a list, apply this function to all elements
        for item in data:
            remove_integrity_keys(item)

def main():
    file_path = 'package-lock.json'
    
    # Read the package-lock.json file
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Remove all integrity keys
    remove_integrity_keys(data)
    
    # Save the modified JSON back to the file
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

    print("All 'integrity' keys have been removed.")

if __name__ == '__main__':
    main()
