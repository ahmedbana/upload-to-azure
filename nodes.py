import requests
import torch
import numpy as np
from PIL import Image
from io import BytesIO
import os
import time
import uuid

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
                "sas_token": ("STRING", {
                    "multiline": False,
                    "default": ""
                }),
                "file_name": ("STRING", {
                    "multiline": False,
                    "default": "output.png"
                }),
                "generation_id": ("STRING", {
                    "multiline": False,
                    "default": ""
                }),
                "webhook_url": ("STRING", {
                    "multiline": False,
                    "default": "https://api.bysnaps.ai/runpod-output"
                }),
                "scene_order": ("STRING", {
                    "multiline": False,
                    "default": "1"
                }),
                "type": ("STRING", {
                    "multiline": False,
                    "default": "Scene"
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("uploaded_url",)
    FUNCTION = "upload"
    CATEGORY = "cloud/azure"
    OUTPUT_NODE = True

    def upload(self, image, base_url, sas_token, file_name, generation_id, webhook_url, scene_order, type):
        try:
            # Ensure URL ends with a slash
            if not base_url.endswith('/'):
                base_url += '/'
            
            # Parse scene orders
            scene_orders = [order.strip() for order in scene_order.split(',') if order.strip()]
            
            # Handle single image or batch of images
            if len(image.shape) == 4:  # Batch of images
                images = image
                num_images = images.shape[0]
            else:  # Single image
                images = image.unsqueeze(0)
                num_images = 1
            
            # Ensure we have enough scene orders
            if len(scene_orders) < num_images:
                # Extend scene orders with default values
                scene_orders.extend([str(i) for i in range(len(scene_orders), num_images)])
            elif len(scene_orders) > num_images:
                # Truncate scene orders to match number of images
                scene_orders = scene_orders[:num_images]
            
            uploaded_urls = []
            
            # Process each image in the batch
            for i in range(num_images):
                current_image = images[i]
                current_scene_order = scene_orders[i]
                
                # Generate random filename with timestamp and generation_id
                timestamp = int(time.time())
                random_id = str(uuid.uuid4())[:8]
                
                if generation_id:
                    filename = f"{timestamp}_{generation_id}_{random_id}_{i}.png"
                else:
                    filename = f"{timestamp}_{random_id}_{i}.png"
                    
                # Ensure filename has proper extension
                if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    filename = os.path.splitext(filename)[0] + '.png'

                # Convert tensor to numpy array
                current_image = current_image.cpu().numpy()
                current_image = Image.fromarray(np.clip(255. * current_image, 0, 255).astype(np.uint8))
                
                # Prepare image data
                byte_io = BytesIO()
                current_image.save(byte_io, format='PNG')
                byte_io.seek(0)

                # Construct upload URL
                upload_url = f"{base_url}{filename}{sas_token}"

                # Set headers for blob upload
                headers = {
                    "x-ms-blob-type": "BlockBlob",
                    "Content-Type": "image/png"
                }

                # Perform upload
                response = requests.put(upload_url, headers=headers, data=byte_io.read())
                if response.status_code == 201:
                    # Send webhook notification for this image
                    webhook_payload = {
                        "status": "scene-completed",
                        "generationId": generation_id if generation_id else "default",
                        "sceneResult": {
                            "sceneOrder": current_scene_order,
                            "type": type,
                            "processedImageUrl": upload_url,
                            "sceneBlurred": "false",
                            "status": "completed"
                        }
                    }
                    
                    try:
                        webhook_response = requests.post(webhook_url, json=webhook_payload, headers={"Content-Type": "application/json"})
                        if webhook_response.status_code in [200, 201, 202]:
                            uploaded_urls.append(upload_url)
                        else:
                            uploaded_urls.append(f"✅ Upload successful: {upload_url} | ❌ Webhook failed: {webhook_response.status_code}")
                    except Exception as webhook_error:
                        uploaded_urls.append(f"✅ Upload successful: {upload_url} | ❌ Webhook error: {str(webhook_error)}")
                else:
                    uploaded_urls.append(f"❌ Upload failed: {response.status_code} - {response.text}")
            
            # Return all uploaded URLs as a single string (comma-separated)
            return (",".join(uploaded_urls),)
            
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
    "AzureBlobUploader": "SNAPS Upload Output to Azure"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']