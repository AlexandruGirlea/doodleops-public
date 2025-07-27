# Function to check if the directory exists and has Terraform configuration files
check_dir() {
    if [ ! -d "$1" ] || [ -z "$(ls $1/*.tf 2> /dev/null)" ]; then
        echo "The specified path does not exist or contains no Terraform files."
        exit 1
    fi
}

# Function to initialize Terraform in the common directory
init_common() {
    if [ -d "common" ] && [ -n "$(ls common/*.tf 2> /dev/null)" ]; then
        terraform -chdir=common init
    else
        echo "Common directory does not exist or contains no Terraform files. Skipping..."
    fi
}

# Main function to apply Terraform configuration
apply_terraform() {
    terraform -chdir=$1 get
    terraform -chdir=$1 apply -auto-approve
}

# Check if user has provided a Terraform directory path
if [[ -z "$1" ]]; then
    echo ""
    echo "You have not provided a Terraform path."
    echo "SYNTAX = ./apply.sh <PATH>"
    echo "EXAMPLE = ./apply.sh dev"
    echo ""
    exit 1
fi

# Main script execution
check_dir $1
init_common
apply_terraform $1