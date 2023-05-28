# -*- coding: utf-8 -*-
"""
Created on Sat May 27 11:05:07 2023

@author: local_temp
"""

import os
import shutil
from dotenv import load_dotenv
from subprocess import Popen, PIPE
from pathlib import Path
import re
from azure.storage.blob import BlobServiceClient
from rich.progress import Progress
from typer import prompt

raise Warning("This script uses the newest version of azure-storage-blob; recommend using a separate venv than Get-Your")

genericProfile = prompt('Enter a generic database profile to use for porting')   

load_dotenv()

azCopyExe = r'c:\azure\azcopy\azcopy.exe'

# Transfer blobs from source to 'transfer', removing 'media/' from their name
# and any leading zeros after 'user_' in the process
# Then transfer back to the 'permanent' account
intermediaryAccountName = 'tempgetfocostore'
intermediaryContainerName = 'filetransfer'
INTERMEDIARYACCOUNT_SAS = os.getenv("TRANSERFILESTORE_SAS")

if '_dev' in genericProfile:            
    permanentAccountName = 'devgetfocofilestore'
    PERMANENTACCOUNT_SAS = os.getenv("DEVFILESTORE_SAS")
else:
    permanentAccountName = 'getfocofilestore'
    PERMANENTACCOUNT_SAS = os.getenv("PRODFILESTORE_SAS")
permanentContainerName = 'applicantfiles'

# Define AzCopy parameters
azCopyExe = r'c:\azure\azcopy\azcopy.exe'
localDirectory = Path(r'B:\get_foco\fileshare_transfer')

# Connect to 'permanent' blob storage
perm_blob_service_client = BlobServiceClient(
    account_url=f'https://{permanentAccountName}.blob.core.usgovcloudapi.net',
    credential=PERMANENTACCOUNT_SAS,
    )
perm_container_client = perm_blob_service_client.get_container_client(
    container=permanentContainerName,
    )

# Loop through all blobs, using AzCopy to download
blobList = list(perm_container_client.list_blobs())
with Progress() as progress:

    downloadTask = progress.add_task(
        "[bright_cyan]Downloading blobs...",
        total=len(blobList),
        )

    for idxitm,blobitm in enumerate(blobList):
        
        # Remove 'media/' and its parent "directory"
        newName = blobitm.name.replace('/media/','')
        # Replace any leading zeros on the username with blank
        newName = re.sub('(user_)0*?([^0*])', r'\1\2', newName)
    
        process = Popen(
            [
                azCopyExe,
                'copy',
                f"https://{permanentAccountName}.blob.core.usgovcloudapi.net/{permanentContainerName}/{blobitm.name}{PERMANENTACCOUNT_SAS}",
                str(localDirectory.joinpath(newName)),
                ],
            stdout=PIPE,
            stderr=PIPE,
            )
        stdout, stderr = process.communicate()
        
        # Raise exception if stderr is anything but empty binary string
        if stderr != b'':
            raise Exception("File download error: {}".format(stderr))
        # Raise exception if job not completed
        if re.sub(rb'.*?\s(\w*)\n\n', rb'\1', stdout[stdout.index(b'Final Job Status'):]).lower() != b'completed':
            logFilePath = re.findall(rb'Log file is located at:\s(.*?)\n\n', stdout)[0]
            raise Exception(
                "Final job status not completed: {smry}\n\nSee log file at\n{logl}\n for additional details".format(
                    smry=stdout[re.search(rb'Job.*?summary', stdout).span()[0]:].decode(),
                    logl=logFilePath.decode(),
                    )
                )
            
        progress.update(downloadTask, advance=1)
        
        if idxitm >= 2:
            break
        
## Once all items have been downloaded, upload them to same blob storage with
# new name and delete them locally
uploadList = os.listdir(localDirectory)

with Progress() as progress:

    uploadTask = progress.add_task(
        "[bright_cyan]Uploading blobs...",
        total=len(uploadList),
        )

    for uplitm in uploadList:
        
        uplPath = localDirectory.joinpath(uplitm)
        # Copy from local directory to target blob storage (recursively).
        # Ref https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azcopy-blobs-upload
        process = Popen(
            [
             azCopyExe,
             'copy',
             str(uplPath),
             f"https://{permanentAccountName}.blob.core.usgovcloudapi.net/{permanentContainerName}{PERMANENTACCOUNT_SAS}",
             '--recursive',
             ],
            stdout=PIPE,
            stderr=PIPE,
            )
        stdout, stderr = process.communicate()
        
        # Raise exception if stderr is anything but empty binary string
        if stderr != b'':
            raise Exception("File upload error: {}".format(stderr))
        # Raise exception if job not completed
        if re.sub(rb'.*?\s(\w*)\n\n', rb'\1', stdout[stdout.index(b'Final Job Status'):]).lower() != b'completed':
            logFilePath = re.findall(rb'Log file is located at:\s(.*?)\n\n', stdout)[0]
            raise Exception(
                "Final job status not completed: {smry}\n\nSee log file at\n{logl}\n for additional details".format(
                    smry=stdout[re.search(rb'Job.*?summary', stdout).span()[0]:].decode(),
                    logl=logFilePath.decode(),
                    )
                )       
            
        # If successful, delete uplPath from local disk
        if uplPath.is_dir():
            shutil.rmtree(uplPath)
        else:
            uplPath.unlink()
            
        progress.update(uploadTask, advance=1)