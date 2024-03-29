from storages.backends.azure_storage import AzureStorage

class AzureMediaStorage(AzureStorage):
    location = ''
    file_overwrite = False
