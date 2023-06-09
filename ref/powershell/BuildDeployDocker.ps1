# This script will build and deploy the Docker container to the account specified in .env

# Notes and caveats:
    # Docker must be installed on the system and have been run manually to store credentials
    # This script does not handle secrets!

    # This will build/deploy whatever branch and state manually set in Git

    # The .env file for this script cannot have '=' in the values, and the values should not be surrounded in quotes

## Wait for Docker service to start (if the machine has just rebooted)
Write-Host "Waiting for Docker service..."
$proc = Start-Process -PassThru -Wait docker info
if ( $proc.ExitCode -eq 0 ) {

    Write-Host "Docker service ready"

    ## Initialize vars
    # Get the installation path from the current path (2x parent, then 'getyour' directory)
    $DockerDir = $(Join-Path $(Split-Path $(Split-Path $pwd)) "getyour")

    ## Set environment variables from the .env file
    Get-Content $(Join-Path $pwd ".env") | ForEach-Object {
        $name, $value = $_.split('=')
        Set-Content env:\$name $value
    }

    ## Run the Docker build and push
    Write-Host "`nBuilding..."
    docker build -t "$($env:DOCKER_ACCOUNT)/$($env:DOCKER_REPO):$($env:BUILD_TAG)" $DockerDir

    Write-Host "`nPushing to Docker hub..."
    docker push "$($env:DOCKER_ACCOUNT)/$($env:DOCKER_REPO):$($env:BUILD_TAG)"

    Read-Host -Prompt "Script complete. Press any key to exit"

}
else {

    Read-Host -Prompt "Docker service did not start properly; script aborted. Press any key to exit"
}