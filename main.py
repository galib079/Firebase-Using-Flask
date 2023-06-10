from flask import Flask
import firebase_admin
from firebase_admin import credentials, firestore
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# Initialize Firebase Admin SDK with service account credentials
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

#  scheduler for background tasks
scheduler = BackgroundScheduler()

#  threshold for the maximum number of request allowed
THRESHOLD = 5


@app.route("/request")
def user_click():
    # reference to the document that stores the request count
    # for our purspose we need to create a reference at request_data --> {uid} --> request_count
    doc_ref = db.collection("request_data").document("request_count")
    doc = doc_ref.get()

    # If the document exists, retrieve the current request count
    if doc.exists:
        count = doc.to_dict().get("count", 0)

        # Check if the click count has reached the threshold
        if count >= THRESHOLD:
            return "You Have Reached Your Daily Threshold."
        else:
            count += 1
    else:
        # If the document doesn't exist, set the initial click count to 1
        count = 1

    # Update the click count in the document
    doc_ref.set({"count": count})
    return f"request count: {count}"


# Function to reset the request count
def reset_click_count():
    doc_ref = db.collection("request_data").document("request_count")
    doc_ref.set({"count": 0})


# Schedule the reset_click_count function to run every 1 minutes
# For Our purpose we need to shcedule this for 24 hours
# This can also be done with celery package which requires redis server running in background

scheduler.add_job(reset_click_count, "interval", minutes=1)
scheduler.start()


# Just and example to show something at '/' endpoint
@app.route("/")
def get_document():
    doc_ref = db.collection("my_collection").document("my_document")
    doc = doc_ref.get()

    # If the document exists, return its contents
    if doc.exists:
        return doc.to_dict()
    else:
        return "Document not found"


if __name__ == "__main__":
    app.run()
