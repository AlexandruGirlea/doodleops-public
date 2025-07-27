#!/bin/bash

# Function to display usage information
usage() {
  echo "Usage: $0 <docker_hub_tags_url> [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]"
  echo ""
  echo "Arguments:"
  echo "  <docker_hub_tags_url>      Docker Hub tags URL (e.g., https://hub.docker.com/r/linuxserver/python/tags)"
  echo ""
  echo "Options:"
  echo "  --start-date YYYY-MM-DD     Filter tags updated on or after this date"
  echo "  --end-date YYYY-MM-DD       Filter tags updated on or before this date"
  echo "  -h, --help                  Display this help message"
  exit 1
}

# Initialize variables
START_DATE=""
END_DATE=""

# Parse command-line arguments
if [ $# -lt 1 ]; then
  usage
fi

# Extract positional arguments
URL="$1"
shift

# Parse options
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --start-date)
      START_DATE="$2"
      shift
      shift
      ;;
    --end-date)
      END_DATE="$2"
      shift
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

# Function to parse namespace and repository from the URL
parse_url() {
  # Example URL: https://hub.docker.com/r/linuxserver/calibre/tags
  # Extract 'linuxserver' as NAMESPACE and 'calibre' as REPOSITORY
  if [[ "$URL" =~ https?://hub\.docker\.com/r/([^/]+)/([^/]+)/tags ]]; then
    NAMESPACE="${BASH_REMATCH[1]}"
    REPOSITORY="${BASH_REMATCH[2]}"
  else
    echo "Invalid Docker Hub tags URL."
    exit 1
  fi
}

# Call the parse_url function
parse_url

PAGE_SIZE=100
NEXT_URL="https://registry.hub.docker.com/v2/repositories/${NAMESPACE}/${REPOSITORY}/tags?page_size=${PAGE_SIZE}"

# Function to compare dates
# Returns 0 if date1 <= date2, 1 otherwise
date_le() {
  [[ "$1" < "$2" || "$1" == "$2" ]]
}

# Returns 0 if date1 >= date2, 1 otherwise
date_ge() {
  [[ "$1" > "$2" || "$1" == "$2" ]]
}

while [ -n "$NEXT_URL" ] && [ "$NEXT_URL" != "null" ]; do
  RESPONSE=$(curl -s "$NEXT_URL")

  # Check if curl was successful
  if [ $? -ne 0 ]; then
    echo "Failed to fetch data from $NEXT_URL"
    exit 1
  fi

  # Extract and filter tag names with dates
  echo "$RESPONSE" | jq -r --arg start "$START_DATE" --arg end "$END_DATE" '
    .results[]
    | {
        name: .name,
        last_updated: .last_updated
      }
    | select(
        ($start == "" or (.last_updated[:10] >= $start)) and
        ($end == "" or (.last_updated[:10] <= $end))
      )
    | .name
  '

  # Get the next page URL
  NEXT_URL=$(echo "$RESPONSE" | jq -r '.next')
done
