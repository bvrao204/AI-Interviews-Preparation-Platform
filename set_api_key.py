import sys
import os

def set_key():
    if len(sys.argv) < 2:
        print("❌ Error: No API key provided.")
        print("Usage: python set_api_key.py <YOUR_GEMINI_API_KEY>")
        sys.exit(1)

    api_key = sys.argv[1].strip().strip("'\"")
    
    # Define paths
    env_path = ".env"
    
    # Read existing lines if .env exists, to preserve other variables
    lines = []
    key_exists = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    # Update or append the GEMINI_API_KEY
    new_lines = []
    for line in lines:
        if line.strip().startswith("GEMINI_API_KEY="):
            new_lines.append(f"GEMINI_API_KEY={api_key}\n")
            key_exists = True
        else:
            new_lines.append(line)
            
    if not key_exists:
        # If there's no trailing newline in the last line, add one
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"GEMINI_API_KEY={api_key}\n")
        
    # Write back to .env
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        
    print(f"✅ Gemini API Key successfully saved to .env!")

if __name__ == "__main__":
    set_key()
