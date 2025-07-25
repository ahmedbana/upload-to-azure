import requests
import torch
import numpy as np
from PIL import Image
from io import BytesIO
import os

class AzureBlobUploader:
    def __init__(self):
        pass
        
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "base_url": ("STRING", {
                    "multiline": False,
                    "default": "https://snapsai.blob.core.windows.net/output/previews/"
                }),
                "destination_blob_name": ("STRING", {
                    "multiline": False,
                    "default": "output.png"
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "upload"
    CATEGORY = "cloud/azure"
    OUTPUT_NODE = True

    SAS_TOKEN = (
        "?sv=2023-01-03"
        "&st=2025-06-11T18%3A33%3A09Z"
        "&se=2030-06-12T18%3A33%3A00Z"
        "&sr=c"
        "&sp=rwl"
        "&sig=P9sMV6EeS5bMqt0%2B8bCDzipFMv8oKg0YQSm76nM9KVM%3D"
    )

    def upload(self, image, base_url, destination_blob_name):
        try:
            # Ensure URL ends with a slash
            if not base_url.endswith('/'):
                base_url += '/'
                
            # Ensure filename has proper extension
            if not destination_blob_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                destination_blob_name = os.path.splitext(destination_blob_name)[0] + '.png'

            # Convert tensor to numpy array
            if len(image.shape) == 4:  # Batch of images
                image = image[0]  # Take first image in batch
            
            image = image.cpu().numpy()
            image = Image.fromarray(np.clip(255. * image, 0, 255).astype(np.uint8))
            
            # Prepare image data
            byte_io = BytesIO()
            image.save(byte_io, format='PNG')
            byte_io.seek(0)

            # Construct upload URL
            upload_url = f"{base_url}{destination_blob_name}{self.SAS_TOKEN}"

            # Set headers for blob upload
            headers = {
                "x-ms-blob-type": "BlockBlob",
                "Content-Type": "image/png"
            }

            # Perform upload
            response = requests.put(upload_url, headers=headers, data=byte_io.read())
            if response.status_code == 201:
                return (f"{upload_url}",)
            else:
                return (f"❌ Upload failed: {response.status_code} - {response.text}",)
        except Exception as e:
            return (f"❌ Upload error: {str(e)}",)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

# Node export
NODE_CLASS_MAPPINGS = {
    "AzureBlobUploader": AzureBlobUploader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AzureBlobUploader": "Azure Blob Uploader"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']