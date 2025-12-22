import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)


class CloudinaryService:
    """Service for handling Cloudinary image uploads"""
    
    @staticmethod
    def upload_image(
        file_data: bytes,
        folder: str = "products",
        public_id: Optional[str] = None,
        overwrite: bool = True,
        resource_type: str = "image"
    ) -> Dict[str, Any]:
        """
        Upload image to Cloudinary
        
        Args:
            file_data: Image file bytes
            folder: Cloudinary folder path
            public_id: Optional custom public ID
            overwrite: Whether to overwrite existing file
            resource_type: Type of resource (image, video, etc.)
            
        Returns:
            Dictionary with upload result including url, secure_url, public_id
        """
        try:
            upload_options = {
                "folder": folder,
                "resource_type": resource_type,
                "overwrite": overwrite,
                "quality": "auto:good",
                "fetch_format": "auto"
            }
            
            if public_id:
                upload_options["public_id"] = public_id
            
            result = cloudinary.uploader.upload(
                file_data,
                **upload_options
            )
            
            return {
                "success": True,
                "url": result.get("url"),
                "secure_url": result.get("secure_url"),
                "public_id": result.get("public_id"),
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result.get("format"),
                "resource_type": result.get("resource_type")
            }
            
        except Exception as e:
            print(f"Cloudinary upload error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def upload_base64_image(
        base64_string: str,
        folder: str = "products",
        public_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload base64 encoded image to Cloudinary
        
        Args:
            base64_string: Base64 encoded image string
            folder: Cloudinary folder path
            public_id: Optional custom public ID
            
        Returns:
            Dictionary with upload result
        """
        try:
            upload_options = {
                "folder": folder,
                "overwrite": True,
                "quality": "auto:good",
                "fetch_format": "auto"
            }
            
            if public_id:
                upload_options["public_id"] = public_id
            
            result = cloudinary.uploader.upload(
                base64_string,
                **upload_options
            )
            
            return {
                "success": True,
                "url": result.get("url"),
                "secure_url": result.get("secure_url"),
                "public_id": result.get("public_id"),
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result.get("format")
            }
            
        except Exception as e:
            print(f"Cloudinary upload error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def delete_image(public_id: str) -> Dict[str, Any]:
        """
        Delete image from Cloudinary
        
        Args:
            public_id: Cloudinary public ID of the image
            
        Returns:
            Dictionary with deletion result
        """
        try:
            result = cloudinary.uploader.destroy(public_id)
            
            return {
                "success": result.get("result") == "ok",
                "result": result.get("result")
            }
            
        except Exception as e:
            print(f"Cloudinary delete error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_optimized_url(
        public_id: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        crop: str = "fill",
        quality: str = "auto:good"
    ) -> str:
        """
        Get optimized image URL with transformations
        
        Args:
            public_id: Cloudinary public ID
            width: Target width
            height: Target height
            crop: Crop mode (fill, fit, scale, etc.)
            quality: Image quality
            
        Returns:
            Optimized image URL
        """
        try:
            transformation = {
                "quality": quality,
                "fetch_format": "auto"
            }
            
            if width:
                transformation["width"] = width
            if height:
                transformation["height"] = height
            if width or height:
                transformation["crop"] = crop
            
            url = cloudinary.CloudinaryImage(public_id).build_url(**transformation)
            return url
            
        except Exception as e:
            print(f"Error building URL: {e}")
            return ""
    
    @staticmethod
    def generate_thumbnail(
        public_id: str,
        width: int = 200,
        height: int = 200
    ) -> str:
        """
        Generate thumbnail URL
        
        Args:
            public_id: Cloudinary public ID
            width: Thumbnail width
            height: Thumbnail height
            
        Returns:
            Thumbnail URL
        """
        return CloudinaryService.get_optimized_url(
            public_id,
            width=width,
            height=height,
            crop="fill"
        )


# Convenience functions
def upload_product_image(file_data: bytes, product_name: str) -> Dict[str, Any]:
    """Upload product image"""
    # Create a clean public_id from product name
    clean_name = product_name.lower().replace(" ", "_")[:50]
    return CloudinaryService.upload_image(
        file_data,
        folder="products",
        public_id=clean_name
    )


def upload_profile_image(file_data: bytes, user_id: int) -> Dict[str, Any]:
    """Upload user profile image"""
    return CloudinaryService.upload_image(
        file_data,
        folder="profiles",
        public_id=f"user_{user_id}"
    )


def upload_store_logo(file_data: bytes, seller_id: int) -> Dict[str, Any]:
    """Upload seller store logo"""
    return CloudinaryService.upload_image(
        file_data,
        folder="stores/logos",
        public_id=f"seller_{seller_id}"
    )


def upload_store_banner(file_data: bytes, seller_id: int) -> Dict[str, Any]:
    """Upload seller store banner"""
    return CloudinaryService.upload_image(
        file_data,
        folder="stores/banners",
        public_id=f"seller_{seller_id}"
    )