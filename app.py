from flask import Flask, jsonify, request
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, storage
import json
import time
import requests
import io
import os
import base64
from PIL import Image, PngImagePlugin

app = Flask(__name__)
CORS(app)
URL = 'https://0bff50ad9fbd018484.gradio.live'

# Load environment variables
PROJECT_ID = os.environ.get('PROJECT_ID')
PRIVATE_KEY_ID = os.environ.get('PRIVATE_KEY_ID')
PRIVATE_KEY = os.environ.get('PRIVATE_KEY').replace('\\n', '\n')
CLIENT_EMAIL = os.environ.get('CLIENT_EMAIL')
CLIENT_ID = os.environ.get('CLIENT_ID')
AUTH_URI = os.environ.get('AUTH_URI')
TOKEN_URI = os.environ.get('TOKEN_URI')
AUTH_PROVIDER_CERT_URL = os.environ.get('AUTH_PROVIDER_CERT_URL')
CLIENT_CERT_URL = os.environ.get('CLIENT_CERT_URL')

# Create the credentials object
cred = credentials.Certificate({
    "type": "service_account",
    "project_id": PROJECT_ID,
    "private_key_id": PRIVATE_KEY_ID,
    "private_key": PRIVATE_KEY,
    "client_email": CLIENT_EMAIL,
    "client_id": CLIENT_ID,
    "auth_uri": AUTH_URI,
    "token_uri": TOKEN_URI,
    "auth_provider_x509_cert_url": AUTH_PROVIDER_CERT_URL,
    "client_x509_cert_url": CLIENT_CERT_URL
})

firebase_admin.initialize_app(
    cred, {'storageBucket': 'storyboard-739ee.appspot.com'})


def upload_to_firebase(file_name):
    bucket = storage.bucket()
    blob = bucket.blob(file_name)
    blob.upload_from_filename(file_name)
    blob.make_public()
    return blob.public_url



@app.route('/regenerate_image', methods=['POST'])
def regenerate_image():
    prompt_response = request.json.get('prompt')
    img_url_response = request.json.get('imgurl')
    instruct_response = request.json.get('instruction')
    drawing_style = request.json.get('style')
    is_option = request.json.get('is_option')
    sett = request.json.get('sett')
    if is_option=="no":
        if drawing_style == "Pen Sketch":
            prompt = 'vvvsketch, ' + prompt_response + ' <lora:vvvsketch:1>'
        else:
            prompt = 'watercolor (medium), ' + prompt_response + ' <lora:nanase_v1:1>'
        payload={
            "prompt": prompt,
            "width": 1344,
            "height": 786,
            "sampler_name": "Euler a",
            "steps": 40,
            "cfg_scale": 7
        }
        response = requests.post(url=f'{URL}/sdapi/v1/txt2img', json=payload)
        r = response.json()
    else:
        if sett=="Select Background":
            img_response = requests.get(img_url_response, stream=True)
            with open("input.png", 'wb') as file:
                for chunk in img_response.iter_content(chunk_size=8192):
                    file.write(chunk)
            if drawing_style == "Pen Sketch":
                prompt = 'vvvsketch, ' + prompt_response + ' <lora:vvvsketch:1>'
            else:
                prompt = 'watercolor (medium), ' + prompt_response + ' <lora:nanase_v1:1>'

            with open('./input.png', 'rb') as file:
                image_data = file.read()
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            print(encoded_image)
            payload={
                "init_images": [encoded_image],
                "prompt": prompt,
                "width": 1344,
                "height": 786,
                "sampler_name": "Euler a",
                "steps": 40,
                "cfg_scale": 7
            }
            response = requests.post(url=f'{URL}/sdapi/v1/img2img', json=payload)
            r = response.json()
        else:

            prompt_add= prompt_response + ' ' + instruct_response

            if drawing_style == "Pen Sketch":
                prompts = 'vvvsketch, ' + prompt_add +' <lora:vvvsketch:1>'
            else:
                prompts = 'watercolor (medium), ' + prompt_add +' <lora:nanase_v1:1>'
            payload={
                "prompt": prompts,
                "width": 1344,
                "height": 786,
                "sampler_name": "Euler a",
                "steps": 40,
                "cfg_scale": 7
            }
            response = requests.post(url=f'{URL}/sdapi/v1/txt2img', json=payload)
            r = response.json()
    for i in r['images']:
        image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
        png_payload = {"image": "data:image/png;base64," + i}
        response2 = requests.post(url=f'{URL}/sdapi/v1/png-info', json=png_payload)
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("parameters", response2.json().get("info"))
        file_name = f'output_{int(time.time())}.png'
        image.save(file_name, pnginfo=pnginfo)
        image_url = upload_to_firebase(file_name)
    return jsonify({"image_urls": image_url})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
