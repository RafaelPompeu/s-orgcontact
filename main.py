import os
import requests
import flask
import pyrebase
from flask_cors import CORS
from flask import Flask, render_template, jsonify
import google.oauth2.credentials as goauth2c
import google_auth_oauthlib.flow as gauthof
import googleapiclient.discovery as gacd


config = {
    "apiKey": "AIzaSyA7RHMUIk16HPR8G2jRccj6orMqwaMeE0A",
    "authDomain": "fir-orgcontact.firebaseapp.com",
    "databaseURL": "https://s-orgcontact-default-rtdb.firebaseio.com",
    "projectId": "s-orgcontact",
    "storageBucket": "s-orgcontact.appspot.com",
    "messagingSenderId": "877476976150",
    "appId": "1:877476976150:web:1a5069417db18e5f720737"
}


firebase = pyrebase.initialize_app(config)
db = firebase.database()

SCOPES = ["openid","https://www.googleapis.com/auth/contacts.readonly","https://www.googleapis.com/auth/userinfo.email"]

app = Flask(__name__)
app.secret_key = 'super-orgcontact'
CORS(app, resources={r'/*': {'origins': '*'}})

@app.route('/')
def index():
    return render_template('index.html')



@app.route('/contact', methods=['GET'])
def api_request():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')

    credentials = goauth2c.Credentials(**flask.session['credentials'])

    user_info_service = gacd.build('oauth2', 'v2', credentials=credentials)
    user_info = user_info_service.userinfo().get().execute()
    key = user_info["id"]
    picture = user_info["picture"]
    user_email = user_info["email"]
    domain = user_info["hd"]
    verified_email = user_info["verified_email"]

    if (user_info["verified_email"]):
        verified_email = "verified"
    else:
        verified_email = "error"


    connections_service = gacd.build("people", "v1", credentials=credentials)
    connections = connections_service.people().connections().list(
        resourceName='people/me',
        personFields='names,emailAddresses'
    ).execute()

    flask.session['credentials'] = credentials_to_dict(credentials)

    if (db.child("users").get().val() == None):
        db_update(key, connections["connections"])

    elif(key not in db.child("users").get().val()):
        db_update(key, connections["connections"])

    data = {}
    emails = db.child("users").child(key).get().val()["emails"]
    for email in emails:
        if email.split("@")[1] in data.keys():
            data[email.split("@")[1]].update({email})
        else:
            data[email.split("@")[1]] = {email}
    data_chat = db.child("users").child(key).get().val()["data_chat"]
    
    return render_template('contact.html', emails=data, picture=picture, id=key,
        domain=domain, email=user_email, domains=len(data), contacts=len(emails), 
        verified_email=verified_email, data_chat=data_chat)


@app.route('/authorize')
def authorize():
    flow = gauthof.Flow.from_client_secrets_file("client_secret.json", scopes=SCOPES)
    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(include_granted_scopes='true')
    flask.session['state'] = state
    return flask.redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    state = flask.session['state']
    flow = gauthof.Flow.from_client_secrets_file("client_secret.json", scopes=SCOPES, state=state)
    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    authorization_response = flask.request.url
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    flask.session['credentials'] = credentials_to_dict(credentials)

    return flask.redirect(flask.url_for('api_request'))

@app.route('/logout')
def clear_credentials():
    if 'credentials' in flask.session:
        del flask.session['credentials']
    return flask.redirect(flask.url_for('index'))


def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}



def db_update(key, connections):
    emails = []
    for i in connections:
            email = i["emailAddresses"][0]["value"]
            emails.append(email)
    data_chat = {}
    for email in emails:
        if email.split("@")[1] in data_chat.keys():
            data_chat[email.split("@")[1]] +=1
        else:
            data_chat[email.split("@")[1]] = 1

    db.child("users").child(key).update({"data_chat": str(data_chat)})
    db.child("users").child(key).update({"emails": emails})


if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'


    app.run('localhost', 8080, debug=True)
