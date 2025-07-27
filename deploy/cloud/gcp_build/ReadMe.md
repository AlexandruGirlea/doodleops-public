# Documentation on how to setup Cloud Build


```bash
# enable the cloud build api
gcloud services enable cloudbuild.googleapis.com servicenetworking.googleapis.com iap.googleapis.com

# create a connection between github and cloud build
# create a service account (or cloud build might already have one)

gcloud projects list

#PROJECT_ID     NAME            PROJECT_NUMBER
#doodleops      doodleops_prod  321
#doodleops-dev  doodleops_dev   123

# set the project variables
export PROJECT_NAME="doodleops-dev" && \
export PROJECT_ID="123" && \
export REGION="us-central1" && \
export DEFAULT_SERVICE_ACCOUNT_EMAIL="$PROJECT_ID@cloudbuild.gserviceaccount.com"

# get the service account email for cloud build
gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --format='table(bindings.members)' --filter="bindings.role:roles/cloudbuild.builds.builder"

# build a custom service account
export SERVICE_ACCOUNT_NAME="cloud-build" && export PROJECT_NAME="doodleops-dev" && export PROJECT_ID="123" && \
export SERVICE_ACCOUNT_EMAIL="$SERVICE_ACCOUNT_NAME@$PROJECT_NAME.iam.gserviceaccount.com" && \
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME --description="Service account for Cloud Build" --display-name="Cloud Build Service Account" --project=$PROJECT_NAME && \
gcloud iam service-accounts list

# how to add roles to the service account
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/run.admin" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/secretmanager.secretAccessor" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/secretmanager.viewer" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/storage.admin" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/artifactregistry.admin" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/secretmanager.secretAccessor" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/logging.logWriter" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/iam.serviceAccountUser" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/secretmanager.secretVersionManager" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/cloudsql.client" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/redis.editor" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/compute.osAdminLogin" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/compute.viewer" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/iam.serviceAccountUser" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/compute.instanceAdmin.v1" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/compute.networkAdmin" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/compute.securityAdmin" && \
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/iap.tunnelResourceAccessor"

# get the roles for the service account
gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --format='table(bindings.role)' --filter="bindings.members:$SERVICE_ACCOUNT_EMAIL"

# build the trigger manually and add the service account

# list the triggers  
gcloud beta builds triggers list --project=doodleops-dev --region=us-central1

# this is how to describe a trigger
gcloud beta builds triggers describe dev --project=doodleops-dev --region=us-central1

gcloud compute addresses list


gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges=google-managed-services-doodleops-vpc \
    --network=doodleops-vpc \
    --project=doodleops-dev
  
# list the peering connections
gcloud services vpc-peerings list --project=doodleops-dev --network=doodleops-vpc
```

Now we need to create Cloud Build worker pool. We use the worker pool to run the builds.
```bash
# create a worker pool
gcloud builds worker-pools create doodleops-build-pool \
        --project=$PROJECT_NAME \
        --region=$REGION \
        --peered-network=projects/$PROJECT_ID/global/networks/doodleops-vpc \
        --worker-machine-type=e2-medium \
        --worker-disk-size=100

# list the worker pools
gcloud builds worker-pools list --project=doodleops-dev --region=us-central1

# In case we need to delete the worker pool
gcloud builds worker-pools delete doodleops-build-pool --project=doodleops-dev --region=us-central1

gcloud builds worker-pools create doodleops-build-pool-no-public \
        --project=$PROJECT_NAME \
        --region=$REGION \
        --peered-network=projects/$PROJECT_ID/global/networks/doodleops-vpc \
        --worker-machine-type=e2-medium \
        --worker-disk-size=100 \
        --no-public-egress
```
Create a firewall rule so that the Redis instance can be accessed by all resources on the VPC network

```bash
# list peerings for our VPC
gcloud compute networks peerings list --network doodleops-vpc

# now list the routes and make sure that the above redis peering is in the list
gcloud compute routes list --filter="network:doodleops-vpc"

# now list the firewall rules (at first we should not see any rules
gcloud compute firewall-rules list --filter="network:doodleops-vpc" --format=json

# create a rule to allow access to the redis instance from the VPC network
gcloud compute firewall-rules create allow-redis-access --network doodleops-vpc --allow tcp:6379 --destination-ranges 10.120.133.227/32\n

# now list the firewall rules and we should see the new rule
gcloud compute firewall-rules list --filter="network:doodleops-vpc" --format=json
```

# Generate `requirements.txt` file for `app_web`
Make sure to run this from inside the Web Docker Container while running locally
```bash
cd app_web
poetry export --without-hashes --format=requirements.txt > requirements.txt
```