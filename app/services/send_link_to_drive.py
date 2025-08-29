#!/usr/bin/env python3
"""
Upload image files to Google Drive folder and get shareable links.
Uses a Google Cloud Service Account (server-side automation).
"""

import os, sys, mimetypes
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]

def authenticate_drive():
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not os.path.exists(creds_path):
        sys.exit("Set GOOGLE_APPLICATION_CREDENTIALS to your service account JSON key path.")
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)

def upload_image(service, file_path, folder_id):
    file_name = os.path.basename(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)
    media = MediaFileUpload(file_path, mimetype=mime_type or "application/octet-stream")
    file_metadata = {"name": file_name, "parents": [folder_id]}
    created = service.files().create(body=file_metadata, media_body=media, fields="id,name").execute()

    # Make public
    service.permissions().create(
        fileId=created["id"],
        body={"type": "anyone", "role": "reader"},
    ).execute()

    meta = service.files().get(fileId=created["id"], fields="webViewLink,webContentLink").execute()
    return file_name, meta["webViewLink"], meta["webContentLink"]

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python image_upload.py <FOLDER_ID> <image1> <image2> ...")
        sys.exit(1)

    folder_id = sys.argv[1]
    files = sys.argv[2:]

    drive = authenticate_drive()
    for f in files:
        if not os.path.isfile(f):
            print(f"Skipping {f} (not a file)")
            continue
        name, view_link, download_link = upload_image(drive, f, folder_id)
        print(f"{name}: {view_link}  (Direct: {download_link})")