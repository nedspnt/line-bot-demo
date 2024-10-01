import json

file_path = "logs/event_logs.jsonl"

def log_event(event):
    with open(file_path, 'a') as file:
        json_event = json.dumps(event)
        file.write(json_event + '\n')
        
