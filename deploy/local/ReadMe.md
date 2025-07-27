# Where DockerCompose looks for stuff
There are stored just outside of this project directory. This is so that they are 
not accidentally committed to the repo.
```bash
../keys 
    └── dev
        ├── firebase_config.json
        ├── firebase_key.json
        └── gcf_manager_key.json
```

# How to generate .env JSON keys

```bash
python scripts/json_helper.py
    Enter the app name, choices = ['app_web', 'app_api']: app_api
    Enter the path to the JSON file: ../keys/dev/gcf_manager_key.json
    Enter the variable name for the JSON string: GCF_SERVICE_ACCOUNT_JSON
    JSON string written to ./deploy/local/app_api/.env with variable name GCF_SERVICE_ACCOUNT_JSON.
```