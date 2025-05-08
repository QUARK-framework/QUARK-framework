import sys


def delete_newlines(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read().replace('\n', '')
        with open(file_path, 'w') as file:
            file.write(content)
        print(f"Newlines removed and file saved: {file_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python delete_newlines.py <file_path>")
    else:
        delete_newlines(sys.argv[1])