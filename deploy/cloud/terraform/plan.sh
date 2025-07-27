# Function to check if the directory exists and has Terraform configuration files
check_dir() {
    if [ ! -d "$1" ] || [ -z "$(ls $1/*.tf 2> /dev/null)" ]; then
        echo "The specified path does not exist or contains no Terraform files."
        exit 1
    fi
}

# Function to initialize Terraform in the specified directory
init_terraform() {
    terraform -chdir=$1 init
    terraform -chdir=$1 get
}

# Function to run Terraform plan
plan_terraform() {
    terraform -chdir=$1 plan
}

# Check if user has provided a Terraform directory path
if [[ -z "$1" ]]; then
    echo ""
    echo "You have not provided a Terraform path."
    echo "SYNTAX = ./plan.sh <PATH>"
    echo "EXAMPLE = ./plan.sh dev"
    echo ""
    exit 1
fi

# Main script execution
check_dir $1
init_terraform $1
plan_terraform $1