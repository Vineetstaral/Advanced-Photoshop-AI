import streamlit as st
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import requests
import uuid
import os
import re
from dotenv import load_dotenv

# Load environment
load_dotenv()
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "dadte3zyj"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "181162474429649"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "3bp3ircop1nGbrvAWgrdZDwVY28"),
    secure=True
)

def parse_compound_command(text):
    """Handle commands with multiple operations"""
    commands = re.split(r"\s+and\s+|\s*,\s*", text.lower())
    operations = []
    
    for cmd in commands:
        params = {"operation": None}
        
        if any(word in cmd for word in ["extend", "expand", "widen"]):
            params["operation"] = "extend"
            params["size"] = 500
            if "square" in cmd:
                params["aspect_ratio"] = "1:1"
            elif "portrait" in cmd:
                params["aspect_ratio"] = "4:5"
            elif "landscape" in cmd:
                params["aspect_ratio"] = "16:9"
            else:
                params["aspect_ratio"] = "1:1"
                
        elif any(word in cmd for word in ["remove", "delete", "erase"]):
            params["operation"] = "remove"
            params["item"] = re.search(r"(remove|delete|erase)\s+(the\s+)?(.+?)(\s|$)", cmd).group(3)
            
        elif any(word in cmd for word in ["recolor", "color", "change color"]):
            params["operation"] = "recolor"
            match = re.search(r"(recolor|color)\s+(the\s+)?(.+?)\s+(to|as)\s+(.+)", cmd)
            params["item"] = match.group(3) if match else None
            params["color"] = match.group(5).replace(" ", "") if match else None
            
        elif any(word in cmd for word in ["replace", "swap"]):
            params["operation"] = "replace"
            match = re.search(r"(replace|swap)\s+(the\s+)?(.+?)\s+(with|for)\s+(.+)", cmd)
            params["item"] = match.group(3) if match else None
            params["replacement"] = match.group(5) if match else None
            
        if params["operation"]:
            operations.append(params)
    
    return operations

def process_compound_command(uploaded_file, operations):
    """Execute multiple Cloudinary transformations sequentially"""
    if not operations:
        return None
        
    # First upload
    public_id = f"cmd-{uuid.uuid4().hex}"
    upload_result = cloudinary.uploader.upload(uploaded_file, public_id=public_id)
    current_url = upload_result["secure_url"]
    
    # Apply each transformation
    transformations = []
    for op in operations:
        if op["operation"] == "extend":
            transformations.extend([
                {"aspect_ratio": op["aspect_ratio"], "background": "gen_fill", "crop": "pad", "width": op["size"]}
            ])
        elif op["operation"] == "remove":
            transformations.append({
                "effect": f"gen_remove:prompt_{op['item']};multiple_true"
            })
        elif op["operation"] == "recolor":
            transformations.append({
                "effect": f"gen_recolor:prompt_{op['item']};to-color_{op['color']}"
            })
        elif op["operation"] == "replace":
            transformations.append({
                "effect": f"gen_replace:from_{op['item']};to_{op['replacement']}"
            })
    
    # Generate final URL with all transformations
    result_url, _ = cloudinary_url(
        public_id,
        transformation=transformations
    )
    
    return result_url

# Streamlit UI
st.title(" Advanced Image Editor")
uploaded_file = st.file_uploader("Upload image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    st.image(uploaded_file, caption="Original Image", use_container_width=True)
    st.markdown("---")
    
    command = st.text_area("What would you like to do?", 
                         placeholder="Example: 'Recolor walls to beige and extend to square'")
    
    if st.button("Process Command"):
        if command:
            operations = parse_compound_command(command)
            
            if not operations:
                st.error("Couldn't understand command. Try:")
                st.code("""
                - "Remove the person and extend to landscape"
                - "Recolor the car red and remove background"
                - "Replace the hat with a helmet and recolor it blue"
                """)
            else:
                with st.spinner(f"Processing {len(operations)} commands..."):
                    result_url = process_compound_command(uploaded_file.getvalue(), operations)
                    
                    if result_url:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.image(uploaded_file, caption="Original", use_container_width=True)
                        with col2:
                            st.image(result_url, caption="Final Result", use_container_width=True)
                        
                        st.download_button(
                            "Download Result",
                            data=requests.get(result_url).content,
                            file_name=f"multi_edit_{uploaded_file.name}"
                        )

if not uploaded_file:
    st.markdown("---")
    st.subheader("Try compound commands like:")
    st.code("""
    # Combined operations
    "Recolor walls to beige and extend to square"
    "Remove the background and replace sky with sunset"
    
    # Single operations
    "Make the dress pink"
    "Extend to portrait format"
    """)
