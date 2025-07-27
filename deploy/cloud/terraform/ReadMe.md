# How to setup a new project

Create a new project in Firebase and GCP

1. Create an empty service account
2. Add all the roles we need to assign to the service account
3. Build the Terraform Bucket with the security settings
4. Create an Artifact Repository for the containers
5. Build / Upload the containers that terraform will use for Cloud Run
6. Upload static files to the bucket
7. Use the script to generate the JSON secrets
8. Comment out the `google_compute_security_policy` resource in the `network.tf`
This will allow GCP to generate the SSL certificate for the domain, also in
Cloud Flare use DNS passthrough to point to the GCP IP with an A record.
9. Run `terraform init` to initialize the backend and run `terraform apply`
10. Uncomment the `google_compute_security_policy` resource in the `network.tf`
11. Run `terraform apply` again to apply the changes
12. In CloudFlare we can now implement Zero Trust to display a login page
to see the website.

Now the infrastructure is up and running.

# How we setup Terraform & GPC

```bash
# Add this to the ~/.bashrc or ~/.zshrc
export TF_VAR_SERVICE_ACCOUNT_KEY_PATH="SOME_PATH"
export GCP_PROJECT_ID="doodleops-dev"
```


### 1. Create an empty service account

# This is how we switch between projects
```bash
# make sure you are in the correct project
gcloud projects list
echo $GCP_PROJECT_ID
gcloud auth activate-service-account --key-file=$TF_VAR_SERVICE_ACCOUNT_KEY_PATH
gcloud config set project $GCP_PROJECT_ID
gcloud projects list
```


This step is only needed if you did not create a terraform service account yet
```bash
# create
gcloud iam service-accounts create terraform-service-account --description="Service account for Terraform" --display-name="Terraform Service Account" --project=$GCP_PROJECT_ID

# list all service accounts
gcloud iam service-accounts list --project $GCP_PROJECT_ID

# this is how you delete it if you need to
gcloud iam service-accounts delete {SERVICE_ACCOUNT_EMAIL} --project $GCP_PROJECT_ID
```

### 2. We add all the roles we need to assign to the service account

List of example roles:
```bash
roles/container.admin
roles/container.clusterAdmin
roles/compute.networkAdmin
roles/dns.admin
roles/redis.admin
roles/cloudsql.admin
roles/apigateway.admin
roles/cloudfunctions.admin
roles/cloudfunctions.developer
roles/iam.serviceAccountUser
roles/storage.admin
roles/compute.securityAdmin
roles/logging.logWriter
roles/monitoring.metricWriter
roles/secretmanager.admin
roles/secretmanager.secrets.create
roles/vpcaccess.admin
roles/iam.serviceAccountAdmin
roles/compute.networkAdmin
roles/compute.instanceAdmin.v1
roles/run.serviceAgent
roles/resourcemanager.projectIamAdmin
```

This is how we search for a role to make sure it exists:
```bash
gcloud iam roles list --filter="name:roles/vpcaccess.admin"
gcloud iam roles list --filter="name:roles/redis.*"
gcloud iam roles list --filter="name:roles/resourcemanager.*"
gcloud iam roles list --filter="name:roles/artifactregistry.*"
gcloud iam roles list --filter="name:roles/iam.serviceAccountKeyAdmin"
gcloud iam roles list --filter="name:roles/cloudtrace.*"
# list ai platform roles
gcloud iam roles list --filter="name:roles/aiplatform.*"
# list ai platform roles but only name and description
gcloud iam roles list --filter="name:roles/aiplatform.*" --format="table(name,description)"
```

This is how we assign a role to a service account manually:
```bash
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com --role roles/container.admin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com --role roles/container.clusterAdmin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com --role roles/compute.networkAdmin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com --role roles/dns.admin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com --role roles/redis.admin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com --role roles/cloudsql.admin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com --role roles/apigateway.admin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com --role roles/cloudfunctions.admin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com --role roles/cloudfunctions.developer && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com --role roles/iam.serviceAccountUser && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com --role roles/storage.admin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com  --role roles/compute.securityAdmin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com  --role roles/logging.logWriter && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com  --role roles/monitoring.metricWriter && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com  --role roles/secretmanager.admin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com  --role roles/vpcaccess.admin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com  --role roles/iam.serviceAccountAdmin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com  --role roles/compute.networkAdmin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com  --role roles/compute.instanceAdmin.v1 && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com  --role  roles/resourcemanager.projectIamAdmin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com  --role  roles/iam.serviceAccountKeyAdmin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com  --role  roles/compute.osLogin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com  --role  roles/artifactregistry.writer && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com  --role  roles/pubsub.admin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com  --role  roles/eventarc.admin  && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com  --role  roles/aiplatform.admin


```

### List all roles assigned to a service account

Choose None if prompted in the CLI.
```bash
export SERVICE_ACCOUNT_EMAIL=terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com
gcloud projects get-iam-policy $GCP_PROJECT_ID --flatten="bindings[].members" --format='table(bindings.role)' --filter="bindings.members:$SERVICE_ACCOUNT_EMAIL"
gcloud projects get-iam-policy $GCP_PROJECT_ID --filter="bindings.members:$SERVICE_ACCOUNT_EMAIL"
gcloud projects get-iam-policy $GCP_PROJECT_ID --flatten="bindings[].members" --format='table(bindings.role)' --filter="bindings.members:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com"
```

Now we generate the service account key. We store it in the keys folder on our local machine.
```bash
gcloud iam service-accounts keys create ../keys/dev/terraform-service-account-key.json --iam-account terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com
```


### 3. Build the services that terraform will use to run the scripts.

```bash
# activate the service account
gcloud auth activate-service-account terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com --key-file=$TF_VAR_SERVICE_ACCOUNT_KEY_PATH
gcloud config set account terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com

# create the artifact repo
gcloud artifacts repositories create docker-repo \
    --repository-format=docker \
    --location=us-central1 \
    --description="Docker repository"

# configure Docker to Authenticate with GCP
gcloud auth configure-docker us-central1-docker.pkg.dev

### OBS_1: replace {app_api} with the name of the container you want to build ex: {app_web}
### OBS_2: use versioning for the containers in the GCP Build. Avoid using :latest
### OBS_3: use the --platform flag to specify the platform of the container
export DOCKER_CLI_EXPERIMENTAL=enabled
docker buildx ls
docker buildx create --name my-amd64-builder --use
docker buildx ls

# we use flag `--load` so that we store the image locally
# if you don't want that you can use `--push` to push the image directly to the repo
# FOR TESTING: docker build --no-cache --platform linux/amd64 -t us-central1-docker.pkg.dev/doodleops-dev/docker-repo/app_api:0.1.0 -f app_dummy/Dockerfile app_dummy/ --load

docker build --no-cache --platform linux/amd64 -t us-central1-docker.pkg.dev/$GCP_PROJECT_ID/docker-repo/app_api:1.63.0 -f app_api/Dockerfile app_api/ --push
docker build --no-cache --platform linux/amd64 -t us-central1-docker.pkg.dev/$GCP_PROJECT_ID/docker-repo/app_web:1.63.0 -f app_web/Dockerfile app_web/ --push
docker build --no-cache --platform linux/amd64 -t us-central1-docker.pkg.dev/$GCP_PROJECT_ID/docker-repo/app_docs_v1:0.3 -f app_api/app_docs/cloud_run_container_app_docs/v1/Dockerfile app_api/app_docs/cloud_run_container_app_docs/v1/ --push
docker build --no-cache --platform linux/amd64 -t us-central1-docker.pkg.dev/$GCP_PROJECT_ID/docker-repo/app_epub_v1:0.1 -f app_api/app_epub/cloud_run_container_app_epub/v1/Dockerfile app_api/app_epub/cloud_run_container_app_epub/v1 --push
docker build --no-cache --platform linux/amd64 -t us-central1-docker.pkg.dev/$GCP_PROJECT_ID/docker-repo/app_images_v1:0.4 -f app_api/app_images/cloud_run_container_app_images/v1/Dockerfile app_api/app_images/cloud_run_container_app_images/v1/ --push
docker build --no-cache --platform linux/amd64 -t us-central1-docker.pkg.dev/$GCP_PROJECT_ID/docker-repo/app_pdf_v1:0.6 -f app_api/app_pdf/cloud_run_container_app_pdf/v1/Dockerfile app_api/app_pdf/cloud_run_container_app_pdf/v1/ --push
docker build --no-cache --platform linux/amd64 -t us-central1-docker.pkg.dev/$GCP_PROJECT_ID/docker-repo/app_ai_v1:0.50 -f app_api/app_ai/cloud_run_container_app_ai/v1/Dockerfile app_api/app_ai/cloud_run_container_app_ai/v1/ --push

# How to push the image to the repository manually
docker push us-central1-docker.pkg.dev/$GCP_PROJECT_ID/docker-repo/app_docs_v1:0.1

# this is how we delete a image
gcloud artifacts docker images delete us-central1-docker.pkg.dev/$GCP_PROJECT_ID/docker-repo/app_api:0.1.0 --delete-tags

# verify the image is in the repo
gcloud artifacts docker images list us-central1-docker.pkg.dev/$GCP_PROJECT_ID/docker-repo
```

### 4. Create a GCP Bucket for Terraform State
```bash
gcloud storage buckets create gs://tfstate-$GCP_PROJECT_ID --location=us-central1 --uniform-bucket-level-access

# make sure that there is no public access to the bucket
gsutil iam get gs://tfstate-$GCP_PROJECT_ID

# only for production
gsutil versioning set on gs://tfstate-$GCP_PROJECT_ID

# gsutil kms encryption -k projects/[PROJECT_ID]/locations/[LOCATION]/keyRings/[KEYRING_NAME]/cryptoKeys/[KEY_NAME] gs://[BUCKET_NAME]
gsutil kms encryption -k projects/$GCP_PROJECT_ID/locations/us-central1/keyRings/$GCP_PROJECT_ID-us-central1-keyring/cryptoKeys/$GCP_PROJECT_ID-us-central1-key gs://tfstate-$GCP_PROJECT_ID

# grant the service account access to the bucket
gsutil iam ch serviceAccount:terraform-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com:objectAdmin gs://tfstate-$GCP_PROJECT_ID

# display the permissions
gsutil iam get gs://tfstate-$GCP_PROJECT_ID

# prevent public access
gcloud storage buckets update gs://tfstate-$GCP_PROJECT_ID --public-access-prevention

# show the public access prevention status
gcloud storage buckets describe gs://tfstate-$GCP_PROJECT_ID --format="default(public_access_prevention)"
```

Now specify the bucket name in the `main.tf` file.

```terraform
terraform {
  backend "gcs" {
    bucket  = "tfstate-$GCP_PROJECT_ID"
    prefix  = "terraform/state"
  }
}
```

Now run `terraform init` to initialize the backend. If prompted, select yes to 
copy the state file to the new backend.


### 5. Use Terraform to generate the Managed Secrets

Create in deploy/cloud/terraform/{dev}/ these files:
  - `.env_app_api.json`
  - `.env_app_api_apps.json`
  - `.env_app_api_apps_ai.json`
  - `.env_app_common.json`
  - `.env_app_web.json`

OBS: you can copy them from `demo.env_app_api.json`, `demo.env_app_web.json`, etc.


In project root go to `scripts/` and run:
```bash
# this command should generate the secrets above once you have the GCP keys
python json_helper.py
```

How to write new secrets
```bash
terraform apply -target=google_secret_manager_secret_version.app-web
terraform apply -target=google_secret_manager_secret_version.app-api
terraform apply -target=google_secret_manager_secret_version.app-common
```

### 6. Copy static files to the bucket (CDN)
First copy the files to the bucket
```bash
gsutil -m cp -r ./app_web/static/*  gs://static-files-doodleops/

# this is for prod
gsutil -m cp -r ./app_web/static/*  gs://static-files-doodleops-prod/
gsutil -m cp -r ./app_web/static/404.html  gs://static-files-doodleops-prod/
gsutil -m cp -r ./app_web/staticfiles/admin/*  gs://static-files-doodleops-prod/admin/
gsutil -m rsync -r ./app_web/staticfiles/admin/  gs://static-files-doodleops-prod/admin/

# one file location
gsutil -m cp -r ./app_web/static/assets/app-api/  gs://static-files-doodleops-prod/assets/app-api/
gsutil -m cp -r ./app_web/static/assets/svg/logos/app_ai.svg  gs://static-files-doodleops-prod/assets/svg/logos/
```

Sync the files when they change
```bash
# deactivate the virtual environment
deactivate
# install the crcmod
sudo pip install -U crcmod
# sync the files in dev
gsutil -m rsync -r ./app_web/static gs://static-files-doodleops/
# sync the files in prod
gsutil -m rsync -r ./app_web/static gs://static-files-doodleops-prod/
```

### 7. How to deploy a new version of the API and WEB apps
1. change the version in tfvars based on the version file in each app
2. build the container for which the version was changed and push it
3. run the `terraform apply`

### 11. How to access Celery VM
If we try to access the VM using SSH we can't because we need a firewall rule. We
can add one temporaraly, pls see below instructions.

Create the env variables
```bash
export CELERY_BEAT_VM=celery-beat-vm && \
export CELERY_WORKER_VM=celery-worker-vm && \
export ZONE=us-central1-c && \
export VPC_NAME=doodleops-vpc && \
export MY_IP_ADDRESS="0.0.0.0/0" && \
export CELERY_VMs_FIREWALL_RULE_NAME=allow-ssh-to-celery-vms && \
export CELERY_VMs_TAG=ssh-to-celery-vms-allowed
```

Create firewall rule to allow the local machine to access Celery VM
```bash
gcloud compute firewall-rules create $CELERY_VMs_FIREWALL_RULE_NAME \
  --direction=INGRESS \
  --priority=1000 \
  --network=$VPC_NAME \
  --action=ALLOW \
  --rules=tcp:22 \
  --source-ranges=$MY_IP_ADDRESS \
  --target-tags=$CELERY_VMs_TAG

# remove it like this
gcloud compute firewall-rules delete $CELERY_VMs_FIREWALL_RULE_NAME
# allow-cloud-build-vm-ssh-access (From CI/CD)
gcloud compute firewall-rules delete allow-cloud-build-vm-ssh-access

# tag the Celery VM's to the firewall rule
gcloud compute instances add-tags $CELERY_BEAT_VM --zone=$ZONE --tags=$CELERY_VMs_TAG && \
gcloud compute instances add-tags $CELERY_WORKER_VM --zone=$ZONE --tags=$CELERY_VMs_TAG

# remove the tag
gcloud compute instances remove-tags $CELERY_BEAT_VM --zone=$ZONE --tags=$CELERY_VMs_TAG && \
gcloud compute instances remove-tags $CELERY_WORKER_VM --zone=$ZONE --tags=$CELERY_VMs_TAG

# tag: ssh-cloud-build-to-celery-vms-allowed (From CI/CD)
gcloud compute instances remove-tags $CELERY_BEAT_VM --zone=$ZONE --tags=ssh-cloud-build-to-celery-vms-allowed && \
gcloud compute instances remove-tags $CELERY_WORKER_VM --zone=$ZONE --tags=ssh-cloud-build-to-celery-vms-allowed
```

Now we can access the Celery VM's
```bash
# list all VM's 
gcloud compute instances list

gcloud compute ssh $CELERY_BEAT_VM --zone=$ZONE --quiet
# or
gcloud compute ssh $CELERY_WORKER_VM --zone=$ZONE --quiet

# you can run this (inside the VM) to debug the startup script
sudo journalctl -u google-startup-scripts.service
```

Make sure to remove the firewall rule after you are done.
```bash
gcloud compute routes list --filter="network:doodleops-vpc"
gcloud compute firewall-rules list --filter="network:doodleops-vpc" --format=json
# this is how we delete the firewall rule
gcloud compute firewall-rules delete allow-ssh-to-celery-vms

gcloud compute instances describe $CELERY_BEAT_VM --zone $ZONE --format="get(tags.items)"
gcloud compute instances describe $CELERY_WORKER_VM --zone $ZONE --format="get(tags.items)"
```


### 8. How to access Redis / Memory Store using a Bastion VM
```bash
export BASTION_NAME=bastion-vm && \
export ZONE=us-central1-c && \
export VPC_NAME=doodleops-vpc && \
export GCP_PROJECT_NAME="doodleops-dev"

gcloud iam service-accounts create bastion-service-account --description="Service account for Bastion VM" --display-name="Bastion Service Account" --project=$GCP_PROJECT_NAME && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:bastion-service-account@$GCP_PROJECT_NAME.iam.gserviceaccount.com --role roles/compute.osAdminLogin && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:bastion-service-account@$GCP_PROJECT_NAME.iam.gserviceaccount.com --role roles/compute.viewer && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:bastion-service-account@$GCP_PROJECT_NAME.iam.gserviceaccount.com --role roles/iam.serviceAccountUser && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:bastion-service-account@$GCP_PROJECT_NAME.iam.gserviceaccount.com --role roles/compute.instanceAdmin.v1 && \
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID --member serviceAccount:bastion-service-account@$GCP_PROJECT_NAME.iam.gserviceaccount.com --role roles/redis.editor

# list all roles of the service account
gcloud projects get-iam-policy $GCP_PROJECT_ID --flatten="bindings[].members" --format='table(bindings.role)' --filter="bindings.members:bastion-service-account@$GCP_PROJECT_NAME.iam.gserviceaccount.com"

gcloud compute instances create $BASTION_NAME \
  --zone=$ZONE \
  --machine-type=e2-micro \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --service-account=bastion-service-account@$GCP_PROJECT_NAME.iam.gserviceaccount.com \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --network-interface=subnet=$VPC_NAME,address=""

# how to delete the above VM if not needed
gcloud compute instances delete $BASTION_NAME --zone=$ZONE

# list all VMs
gcloud compute instances list

export VPC_NAME=doodleops-vpc && \
export MY_IP_ADDRESS=$(curl ifconfig.me) && \
export BASTION_TAG=ssh-bastion-allowed

gcloud compute firewall-rules create allow-bastion-vm-ssh-access \
  --action=ALLOW \
  --direction=INGRESS \
  --rules=tcp:22 \
  --source-ranges=$MY_IP_ADDRESS/32 \
  --target-tags=$BASTION_TAG \
  --priority=1000 \
  --network=$VPC_NAME
# remove it like this
gcloud compute firewall-rules delete allow-bastion-vm-ssh-access

# tag the Bastion VM to the firewall rule
gcloud compute instances add-tags $BASTION_NAME --zone=$ZONE --tags=$BASTION_TAG
# access the Bastion VM
gcloud compute ssh $BASTION_NAME --zone=$ZONE

# from the local machine
export redis_ip=$(gcloud redis instances describe doodleops-redis --region=us-central1 --format=json | jq -r '.host')

brew install redis

# create a gcp tunnel to the redis instance
gcloud compute ssh $BASTION_NAME --zone=$ZONE -- -N -L 6379:$redis_ip:6379

# Now use PyCharm DB Browser to connect to the redis instance

# or use the redis-cli
redis-cli -h 127.0.0.1 -p 6379
```

### 9. How to access the Cloud SQL using the same Bastion VM
```bash
sql_ip=$(gcloud sql instances describe doodleops-mysql --format=json | jq -r '.ipAddresses[] | select(.type == "PRIVATE") | .ipAddress')

gcloud compute ssh $BASTION_NAME --zone=$ZONE -- -N -L 3306:$sql_ip:3306 
```

### 10. How to set up Google SSO (oAuth / Credentials)
Firebase will set up the Google SSO for us. 
We need to add the domain to the Firebase project. 

We also need to:
- Go to the Google Cloud Console.
- in APIs & Services > OAuth consent screen set the necessary information.

OBS: In prod make sure we only use HTTPS so that we can change the publishing 
status from "Testing" to "In Production".

### 11. How to make Cloud Run apps talk to each other

Read this [link](https://cloud.google.com/run/docs/triggering/https-request#deterministic)
to understand how to make Cloud Run URL be deterministic.

They use the format:
```bash
https://[TAG---]SERVICE_NAME-PROJECT_NUMBER.REGION.run.app
```
where:
- `TAG` is the optional traffic tag for the revision that you are requesting.
- `PROJECT_NUMBER` is the Google Cloud project number.
- `SERVICE_NAME` is the name of the Cloud Run service.
- `REGION` is the name of the region, such as us-central1.

Just add a new API endpoint in the `.env_app_api.json` file, and update the api 
secrets. Lastly, update the version of the app_api and deploy it to Cloud Run.

### 12. How to backup base docker images used in the project
```bash
# create the artifact repo `docker-repo-base-images`
gcloud artifacts repositories create docker-repo-base-images \
    --repository-format=docker \
    --location=us-central1 \
    --description="Docker repository for base images"
```

```bash
docker pull <local-image-name>:<tag>
docker tag <local-image-name>:<tag> us-central1-docker.pkg.dev/$GCP_PROJECT_ID/docker-repo-base-images/<local-image-name>:<tag>
docker push us-central1-docker.pkg.dev/$GCP_PROJECT_ID/docker-repo-base-images/<local-image-name>:<tag>
```
Real example:
```bash
export DOCKER_IMG_NAME_AND_TAG="linuxserver/calibre:7.13.0"
docker pull $DOCKER_IMG_NAME_AND_TAG
docker tag $DOCKER_IMG_NAME_AND_TAG us-central1-docker.pkg.dev/$GCP_PROJECT_ID/docker-repo-base-images/$DOCKER_IMG_NAME_AND_TAG
docker push us-central1-docker.pkg.dev/$GCP_PROJECT_ID/docker-repo-base-images/$DOCKER_IMG_NAME_AND_TAG
```

You can now reference the image in the `Dockerfile` like this:
```Dockerfile
FROM us-central1-docker.pkg.dev/$GCP_PROJECT_ID/docker-repo-base-images/linuxserver/calibre:7.13.0
```

# Troubleshooting
Clean up in case of terraform destroy failure

```bash
# remove garbage if terraform fails
gcloud compute backend-buckets delete cdn --quiet && \
gcloud compute ssl-certificates delete managed-ssl-cert --quiet && \
gcloud compute addresses delete $GCP_PROJECT_ID-ip --global --quiet && \
gcloud compute security-policies delete whitelist-cloudflare-only --quiet && \
gcloud compute networks delete doodleops-vpc --quiet
```

```bash
# destroy terraform networking
terraform destroy -target=google_compute_global_forwarding_rule.default_https \
-target=google_compute_target_https_proxy.default \
-target=google_compute_managed_ssl_certificate.managed-ssl-cert \
-target=google_compute_url_map.url-map \
-target=google_compute_backend_service.app-api-backend \
-target=google_compute_backend_service.app-web-backend \
-target=google_compute_region_network_endpoint_group.app-api-neg \
-target=google_compute_region_network_endpoint_group.app-web-neg
```
 
Debugging why the DNS is not working

```bash
dig dev-api.doodleops.com
ping dev-api.doodleops.com
curl -Iv https://dev-api.doodleops.com
gcloud run services list --platform managed
gcloud compute ssl-certificates list
gcloud compute forwarding-rules list
gcloud compute ssl-certificates describe managed-ssl-cert
gcloud dns record-sets list
gcloud compute networks list
gcloud compute networks describe doodleops-vpc
```