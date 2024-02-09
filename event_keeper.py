import json

file_path = "event_logs.json"

def log_event(event):
    with open(file_path, 'a') as file:
        json_event = json.dumps(event)
        file.write(json_event + '\n')
        
