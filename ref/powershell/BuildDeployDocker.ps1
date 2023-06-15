# This script will build and deploy the Docker container to the account specified in .env

# Notes and caveats:
    # Docker must be installed on the system and have been run manually to store credentials
    # This script does not handle secrets!

    # This will build/deploy whatever branch and state manually set in Git

    # The .env file for this script cannot have '=' in the values, and the values should not be surrounded in quotes

## Initialize vars
# Get the installation path from the current path (2x parent, then 'getyour' directory)
$DockerDir = $(Join-Path $(Split-Path $(Split-Path $pwd)) "getyour")

## Set environment variables from the .env file
Get-Content $(Join-Path $pwd ".env") | ForEach-Object {
    $name, $value = $_.split('=')
    Set-Content env:\$name $value
}

## Run the Docker build and push
docker build -t "$($env:DOCKER_ACCOUNT)/$($env:DOCKER_REPO):$($env:BUILD_TAG)" $DockerDir
docker push "$($env:DOCKER_ACCOUNT)/$($env:DOCKER_REPO):$($env:BUILD_TAG)"