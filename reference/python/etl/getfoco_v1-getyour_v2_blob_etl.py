"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

# -*- coding: utf-8 -*-
"""
Created on Sat May 27 11:05:07 2023

@author: local_temp
"""

import os
import re
import shutil
from pathlib import Path
from subprocess import PIPE, Popen

from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from rich.progress import Progress

# Enter a generic database profile to use for porting
profile = "getfoco_prod"
print(f"Beginning blob transfer for '{profile}'")

load_dotenv()

# Transfer blobs from source to local drive, removing 'media/' from their name
# and any leading zeros after 'user_' in the process
# Then transfer back to the storage account

if "_dev" in profile:
    storageAccountName = "devgetfocofilestore"
    STORAGEACCOUNT_SAS = os.getenv("DEVFILESTORE_SAS")
elif "_stage" in profile:
    storageAccountName = "stagegetfocofilestore"
    STORAGEACCOUNT_SAS = os.getenv("STAGEFILESTORE_SAS")
else:
    storageAccountName = "getfocofilestore"
    STORAGEACCOUNT_SAS = os.getenv("PRODFILESTORE_SAS")
containerName = "applicantfiles"

# Define AzCopy parameters
azCopyExe = r"c:\azure\azcopy\azcopy.exe"
localDirectory = Path(r"C:\fileshare_transfer\get_foco")

# Connect to blob storage
blob_service_client = BlobServiceClient(
    account_url=f"https://{storageAccountName}.blob.core.usgovcloudapi.net",
    credential=STORAGEACCOUNT_SAS,
)
container_client = blob_service_client.get_container_client(
    container=containerName,
)

# Loop through all blobs, using AzCopy to download
blobList = list(container_client.list_blobs())
with Progress() as progress:
    downloadTask = progress.add_task(
        "[bright_cyan]Downloading blobs...",
        total=len(blobList),
    )

    for idxitm, blobitm in enumerate(blobList):
        # Remove 'media/' and its parent "directory"
        newName = blobitm.name.replace("/media/", "")
        # Replace any leading zeros on the username with blank
        newName = re.sub("(user_)0*?([^0*])", r"\1\2", newName)

        process = Popen(
            [
                azCopyExe,
                "copy",
                f"https://{storageAccountName}.blob.core.usgovcloudapi.net/{containerName}/{blobitm.name}{STORAGEACCOUNT_SAS}",
                str(localDirectory.joinpath(newName)),
            ],
            stdout=PIPE,
            stderr=PIPE,
        )
        stdout, stderr = process.communicate()

        # Raise exception if stderr is anything but empty binary string
        if stderr != b"":
            raise Exception("File download error: {}".format(stderr))
        # Raise exception if job not completed
        if (
            re.sub(
                rb".*?\s(\w*)\n\n", rb"\1", stdout[stdout.index(b"Final Job Status") :]
            ).lower()
            != b"completed"
        ):
            logFilePath = re.findall(rb"Log file is located at:\s(.*?)\n\n", stdout)[0]
            raise Exception(
                "Final job status not completed: {smry}\n\nSee log file at\n{logl}\n for additional details".format(
                    smry=stdout[
                        re.search(rb"Job.*?summary", stdout).span()[0] :
                    ].decode(),
                    logl=logFilePath.decode(),
                )
            )

        progress.update(downloadTask, advance=1)

## Once all items have been downloaded, go back through and delete the remote
## blobs (they will be stored in soft delete for 30 days)

# Verify the same number of local files as blobs (AzCopy verifies during copy,
# so even just this is overkill)
assert len(
    [f for dp, dn, filenames in os.walk(localDirectory) for f in filenames]
) == len(blobList)

with Progress() as progress:
    deleteTask = progress.add_task(
        "[bright_cyan]Deleting remote blobs...",
        total=len(blobList),
    )

    for idxitm, blobitm in enumerate(blobList):
        container_client.delete_blob(blobitm)

        progress.update(deleteTask, advance=1)

## Once all items have been deleted, upload them to same blob storage with
## new name and delete them locally
uploadList = os.listdir(localDirectory)

with Progress() as progress:
    uploadTask = progress.add_task(
        "[bright_cyan]Uploading blobs...",
        total=len(uploadList),
    )

    for idxitm, uplitm in enumerate(uploadList):
        uplPath = localDirectory.joinpath(uplitm)
        # Copy from local directory to target blob storage (recursively).
        # Ref https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azcopy-blobs-upload
        process = Popen(
            [
                azCopyExe,
                "copy",
                str(uplPath),
                f"https://{storageAccountName}.blob.core.usgovcloudapi.net/{containerName}{STORAGEACCOUNT_SAS}",
                "--recursive",
            ],
            stdout=PIPE,
            stderr=PIPE,
        )
        stdout, stderr = process.communicate()

        # Raise exception if stderr is anything but empty binary string
        if stderr != b"":
            raise Exception("File upload error: {}".format(stderr))
        # Raise exception if job not completed
        if (
            re.sub(
                rb".*?\s(\w*)\n\n", rb"\1", stdout[stdout.index(b"Final Job Status") :]
            ).lower()
            != b"completed"
        ):
            logFilePath = re.findall(rb"Log file is located at:\s(.*?)\n\n", stdout)[0]
            raise Exception(
                "Final job status not completed: {smry}\n\nSee log file at\n{logl}\n for additional details".format(
                    smry=stdout[
                        re.search(rb"Job.*?summary", stdout).span()[0] :
                    ].decode(),
                    logl=logFilePath.decode(),
                )
            )

        # If successful, delete uplPath from local disk
        # But don't delete if '_prod' is in profile
        if "_prod" not in profile:
            if uplPath.is_dir():
                shutil.rmtree(uplPath)
            else:
                uplPath.unlink()

        progress.update(uploadTask, advance=1)

print("BLOB ETL COMPLETE")
print(
    "Note that for PROD: the getfocofilestore soft delete was changed to 30 days; mark a reminder to verify the files can be permanently deleted for 30 days from when this was run and also to change the 'soft delete' setting back to the default 7 days"
)
