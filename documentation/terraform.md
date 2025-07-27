### General commands
```bash
# the resources are created in the reverse order as printed in the plan
terraform plan

# view what is going to be deployed
terraform graph

# copy the above output and paste into this website to visualize the graph
http://www.webgraphviz.com/

# we can save the plan like this
terraform plan --out plan.tfplan

# and display it like this
terraform show plan.tfplan
terraform show -json plan.tfplan

# apply the plan
terraform apply
terraform destroy

# list all resources
terraform state list

# destroy only a single/multiple resources
terraform destroy -target RESOURCE_TYPE.NAME -target RESOURCE_TYPE2.NAME

# we can use the console to print out some variables
terraform console

# get the latest modules
terraform get -update

# The terraform fmt command automatically updates configurations
terraform fmt

# The terraform validate command validates the configuration files in a directory
terraform validate

# Inspect the current state
terraform show
```