import os
import json


def convert_json_file_to_string(file_location):
    try:
        # Open the file in read mode and load the JSON content
        with open(file_location, "r") as json_file:
            json_data = json.load(json_file)

        # Convert the Python dictionary back into a JSON formatted string
        return json.dumps(json_data, separators=(",", ":"))
    except FileNotFoundError:
        return "File not found. Please check the file path."
    except json.JSONDecodeError:
        return "Invalid JSON file. Please check the file content."
    except Exception as e:
        return f"An error occurred: {str(e)}"


def create_json_string(json_var_name, json_string):
    return f"{json_var_name}=\"{json_string}\"\n".replace("\\n", "\\\\n")


if __name__ == "__main__":

    print("If you don't know how to use this script, type 'help'")

    if len(os.sys.argv) > 1 and os.sys.argv[1] == "help":
        print(
            """The Script asks for these inputs:
            - App name (app_web or app_api)
            - Path to the JSON file
            - Variable name for the JSON string
            
            This script reads a JSON file provided as input and converts it into a
            JSON formatted string. The JSON formatted string is then written to 
            the `.env` file with the specified Variable Name.
            
            OBS: the script will replace the content of an EXISTING variable 
            name in the .env file. If the variable name does not exist, it will
            do NOTHING.
            """
        )
        exit()

    # Path to the JSON file
    app_name = input(
        "Optional: Enter the app name, choices = ['app_web', 'app_api']. \n"
        "If no existing app name is provided then we will create a new "
        "output.json file."
    )
    if app_name in ("app_web", "app_api"):
        print(f"We will update the .env file for the app.{app_name}")
    else:
        print("We will create a new output.json file in the current directory.")

    file_path = input("Enter the path to the JSON file: ")
    json_var_name = input("Enter the variable name for the JSON string: ")

    # check if the file path exists
    if not os.path.exists(file_path):
        print("File path does not exist. Please check the file path.")
        exit()

    # Call the function and get the JSON string
    json_string = convert_json_file_to_string(file_path)
    json_string = json_string.replace("\n", "")
    json_string = (
        json_string.replace('"', "***").replace("'", '"').replace("***", "'")
    )

    env_file_path = f"./deploy/local/{app_name}/.env"

    if os.path.exists(env_file_path):
        with open(env_file_path, "r") as env_file:
            env_file_data = env_file.readlines()

        for index, line in enumerate(env_file_data):
            if line.startswith(f"{json_var_name}="):
                env_file_data[index] = create_json_string(
                    json_var_name=json_var_name, json_string=json_string
                )
                break
    else:
        env_file_path = "output.json"
        env_file_data = create_json_string(
            json_var_name=json_var_name, json_string=json_string
        )

    with open(env_file_path, "w") as env_file:
        env_file.writelines(env_file_data)

    print(
        f"JSON string written to {env_file_path} with variable name {json_var_name}."
    )
