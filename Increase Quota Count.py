from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin import auth

app = Flask(__name__)

# Initialize Firebase Admin SDK with service account credentials
cred = credentials.Certificate("serviceAccountkey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


def validate_and_extract_uid(token):
    try:
        # Verify the JWT token using Firebase Admin SDK
        decoded_token = auth.verify_id_token(token)
        # Extract the UID from the decoded token
        uid = decoded_token['uid']
        # Return the UID
        return uid
    except auth.InvalidIdTokenError:
        # Handle invalid token error
        raise Exception("Invalid token")


@app.route('/api/request', methods=['POST'])
def handle_request():
    token = request.headers.get('token')
    user_id = validate_and_extract_uid(token)
    # assuming the quota value is static 300
    # will have to get the from the plans data in the datastore if multiple plans are introduced
    max_quota = 300
    collection_ref = db.collection("customers").document(user_id).collection("subscriptions")
    # Get the first document in the collection
    docs = collection_ref.limit(1).get()
    # Check if there are any documents in the collection
    if docs:
        # Get the first document
        doc = docs[0]
        # Extract the value of the 'status' field
        status = doc.get('status')
        # Check if the user's subscription status is active
        if status == 'active':
            quota_counter_ref = db.collection('quota_counter').document(user_id)
            quota_counter_doc = quota_counter_ref.get()
            # Check if the quota counter document exists for the user
            if quota_counter_doc.exists:
                quota_data = quota_counter_doc.to_dict()
                quota = quota_data.get('quota', 0)
                # Check If quota exceeded and the subID is the same means no new plan subscription
                if quota_data['quota'] < max_quota and quota_data['subID'] == doc.id:
                    # Process the request and increment the quota count
                    quota_data['quota'] = quota + 1
                    quota_counter_ref.update(quota_data)
                    return jsonify(
                        {'message': 'Request processed successfully', 'quota_left': max_quota - quota_data['quota'],
                         'subscription': status})
                elif quota_data['subID'] != doc.id:
                    quota_data = {
                        'quota': 1,
                        'subID': str(doc.id)
                    }
                    quota_counter_ref.set(quota_data)
                    return jsonify(
                        {'message': 'Request processed successfully', 'quota_left': max_quota - quota_data['quota'],
                         'subscription': status})
                else:
                    return jsonify(
                        {'message': 'Quota Exceeded', 'quota_left': 0,
                         'subscription': status})
            # Add The Quota Data for user when user is requesting for first time
            else:
                # Initialize the quota counter for the user
                quota_data = {
                    'quota': 1,
                    'subID': str(doc.id)
                }
                quota_counter_ref.set(quota_data)
                return jsonify(
                    {'message': 'Request processed successfully', 'quota_left': max_quota - quota_data['quota'],
                     'subscription': status})
        # User subscription is not active
        else:
            quota_data = {
                'quota': 0,
                'subID': str(doc.id)
            }
            quota_counter_ref = db.collection('quota_counter').document(user_id)
            quota_counter_ref.set(quota_data)
            # User's subscription is inactive
            return jsonify({'message': 'Subscription expired. Please subscribe to access the service.'}), 403
    else:
        # User's subscription data is not found may be never initiated any payments
        return jsonify({'message': 'No subscription data found. Please subscribe to access the service.'}), 403


if __name__ == "__main__":
    app.run()
