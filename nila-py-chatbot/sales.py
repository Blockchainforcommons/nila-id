import json
import os
import boto3
import requests
from requests.auth import HTTPBasicAuth
import qrcode
from PIL import Image
from boto3.dynamodb.conditions import Key
from twilio.twiml.voice_response import VoiceResponse
from datetime import datetime as dt
import time
from nav import TimeOfDay
from MODULES import loadData
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

account_sid = os.getenv("ACCOUNT_SID")
auth_token = os.getenv("AUTH_TOKEN")

dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
lamb = boto3.client('lambda')
s3 = boto3.client('s3')
DecentralizedID = dynamodb.Table('DID')
AESTABLE = dynamodb.Table('AES-stage')
TWILCLIENT = Client(account_sid, auth_token)

issueNodeURI = 'https://8726-2a02-a46a-7ff7-1-18d6-163e-578c-96e9.ngrok-free.app'
proofNodeURI = 'https://fbae-2a02-a46a-7ff7-1-7109-a94f-21e6-e7d6.ngrok-free.app'

def InitialSupplyRequest(event,context):
    #print(event)
    '''
    user signals the intent to sell his produce

        - get remote sensing data and fetch events and activity:
                - harvest event detectable?
                - estimate crop type
                - estimate fields and size of cultivation
                - estimate yield
                - other
        - lookup or create identity in issue node 
        - request issuance of cultivation certificates
        - return attributes
    '''
    try:
        input = loadData(event)
        #print('input', input)
        phone = input['phone'].split(':')[1]
        print(phone)
        # secondary api to request remote sensing data from chitta-sensing stack
        try:
            resp = lamb.invoke(
                FunctionName='arn:aws:lambda:ap-south-1:867185477215:function:Chitta-Sensing-stage-GETLABEL',
                InvocationType='RequestResponse',
                Payload=json.dumps({
                    'phone': input['phone'].split(':')[1], 
                    'pk': json.loads(input['wallet'])['pk'],
                    }),
                LogType='Tail'
            )
            label = json.loads(json.loads(resp['Payload'].read())['body'])
            print('field activity label:',label)
            ct = label['ct']
            # create message to user
            if dt.strptime(label['hrvst'],'%m/%d/%Y') < dt.now():
                # harvest event happened
                message = 'Great. We found you harvested {} quintal {} and we created the product credentials. Please answer the following questions.'.format(label['yield'],ct)
            else:
                # harvest event upcoming
                message = 'Sure. Did you harvest your crops? If not, be rest assured, we created the certificates and minted the tokens based on our estimates.'.format(label['yield'],ct)

        except:
            # no active or recently active cultivation detected. Return 'UNDETECTED'
            return {
                "statusCode": 200,
                "headers": { "content-type":"application/json; charset=utf-8" },
                "body": json.dumps({ 
                    'l': input['l'],
                    'res': 'UNDETECTED'
                })
            }

        # find the DID of the user 
        # IMPROVEMENT: generate the DID from the eth key 
        # lookup DID in storage
        did = DecentralizedID.query(KeyConditionExpression=Key("phoneNumber").eq(phone), ProjectionExpression="did")['Items']
        print('did', did)
        if len(did) == 0:
            print('create new identity and store')
            identity = requests.post(f'{issueNodeURI}/v1/identities', 
                    data=json.dumps({
                        "didMetadata": {
                        "method": "polygonid",
                        "blockchain": "polygon",
                        "network": "mumbai"
                    }}),
                    auth=HTTPBasicAuth('user-issuer','password-issuer'))
            identity = json.loads(identity.text)
            user_DID = identity['identifier']
            # store the new identity 
            DecentralizedID.put_item(
                Item={
                    "phoneNumber": phone,
                    "did": did,
                    "state": json.dumps(identity['state'])
                })
        else:
            user_DID= did[0]['did']

        # create a new claim, 
        issuer_DID = 'did:polygonid:polygon:mumbai:2qLh2QHAX7bG98SNBVJnhQUbFnLCB8VJ1uscBJvaPN'
        claim = requests.post(f'{issueNodeURI}/v1/{issuer_DID}/claims',
                          data=json.dumps({
                                "credentialSchema":"https://raw.githubusercontent.com/iden3/claim-schema-vocab/main/schemas/json/KYCAgeCredential-v3.json",
                                "type": "KYCAgeCredential",
                                "credentialSubject": {
                                    "id": user_DID,
                                    "birthday": 19960424,
                                    "documentType": 2
                                },
                                "expiration": 1680532130
                          }),
                          auth=HTTPBasicAuth('user-issuer','password-issuer'))

        # initiate issue credential of the data supplied by the chitta-sensing stack
        #x = requests.get(f'{issueNodeURI}/v1/identities', auth=HTTPBasicAuth('user-issuer','password-issuer'))
        print('claim id',claim.text)
        id = json.loads(claim.text)['id']
        # create and store QR image for the storage manager to scan and verify/issue new certs
        link = f'https://wa.me/13478481380?text=issue%20{ct}%20storage%20certificates%20for{phone}&did={user_DID}&nid={id}' # attributes used by WABA to initiate Zero Knowledge proofs
        print('link', link)
        
        # QR links have been approved by META
        qr = qrcode.make(link)
        qr.save("/tmp/qr.png")
        type(qr)
        # From png to jpg
        resave = Image.open(r'/tmp/qr.png')
        resave.save("/tmp/qr.jpg")
        print('resaved to jpg')

        filename = id.split('-')[-1] # naming based on claim id
        bucket = 'chatbot-stage-cropcerts-10xgf6ebbroee'
        with open("/tmp/qr.jpg", "rb") as f:
            s3.upload_fileobj(f, bucket, filename,ExtraArgs={'ACL': 'public-read', 'ContentType': 'image/jpg'})
        os.remove("/tmp/qr.jpg")

        return {
                "statusCode": 200,
                "headers": { "content-type":"application/json; charset=utf-8" },
                "body": json.dumps({ 
                    'l': input['l'],
                    'res': 'DETECTED',
                    'nila_claim_id' : id, 
                    'nila_issuer_DID': issuer_DID,
                    'ct': label['ct'],
                    'hrvst': label['hrvst'],
                    'fields': label['fields'],
                    'size': label['size'],
                    'yield': label['yield'],
                    'other': label['other'],     
                    'message': message,
                    'qr_link': 'https://{}.s3.ap-south-1.amazonaws.com/{}'.format(bucket,filename)            
                    }) # return validation result
            }

    except Exception as e: 
        print(e)
        print('------------------------')
        return "Error"

def claimType(ct,user_DID,input):
    expiration = int(time.time() + 60*60*24*365) # expiration depending on croptype
    return json.dumps({
              "credentialSchema":"ipfs://QmWVCoJhnZCoA1VbdoJ3QF6xvi7XWGwdYo25x3xpXKKrf8",
                "type": "StoragePaddy",
                "credentialSubject": {
                    "id": user_DID,
                    "grade": input['store_grade'],
                    "quantity": float(input['store_amount']),
                },
                "expiration": expiration,
                "signatureProof": False,
                "mtProof": True,
        })

e = {'resource': '/supply_storage', 'path': '/supply_storage', 'httpMethod': 'POST', 'headers': {'Accept': '*/*', 'CloudFront-Forwarded-Proto': 'https', 'CloudFront-Is-Desktop-Viewer': 'true', 'CloudFront-Is-Mobile-Viewer': 'false', 'CloudFront-Is-SmartTV-Viewer': 'false', 'CloudFront-Is-Tablet-Viewer': 'false', 'CloudFront-Viewer-ASN': '14618', 'CloudFront-Viewer-Country': 'US', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'Host': '7l3sx25tf9.execute-api.ap-south-1.amazonaws.com', 'I-Twilio-Idempotency-Token': 'a634ff1f-304d-4137-8582-3f937cf07090', 'User-Agent': 'TwilioProxy/1.1', 'Via': '1.1 e004b21574888e2383bc40e183527f92.cloudfront.net (CloudFront)', 'X-Amz-Cf-Id': 'JN-YTMKrvL1ghxo7ETuvVFBpFV6nBsd2E1aTfJ6_gI5YUGF2TGYdZg==', 'X-Amzn-Trace-Id': 'Root=1-64e76fad-1e2024020e0e21496fff7e30', 'X-Forwarded-For': '174.129.119.192, 130.176.134.131', 'X-Forwarded-Port': '443', 'X-Forwarded-Proto': 'https', 'X-Home-Region': 'us1', 'X-Twilio-Signature': 'FF9IVbhWh8sd7jAHNk4oVOk4LCE='}, 'multiValueHeaders': {'Accept': ['*/*'], 'CloudFront-Forwarded-Proto': ['https'], 'CloudFront-Is-Desktop-Viewer': ['true'], 'CloudFront-Is-Mobile-Viewer': ['false'], 'CloudFront-Is-SmartTV-Viewer': ['false'], 'CloudFront-Is-Tablet-Viewer': ['false'], 'CloudFront-Viewer-ASN': ['14618'], 'CloudFront-Viewer-Country': ['US'], 'Content-Type': ['application/x-www-form-urlencoded; charset=UTF-8'], 'Host': ['7l3sx25tf9.execute-api.ap-south-1.amazonaws.com'], 'I-Twilio-Idempotency-Token': ['a634ff1f-304d-4137-8582-3f937cf07090'], 'User-Agent': ['TwilioProxy/1.1'], 'Via': ['1.1 e004b21574888e2383bc40e183527f92.cloudfront.net (CloudFront)'], 'X-Amz-Cf-Id': ['JN-YTMKrvL1ghxo7ETuvVFBpFV6nBsd2E1aTfJ6_gI5YUGF2TGYdZg=='], 'X-Amzn-Trace-Id': ['Root=1-64e76fad-1e2024020e0e21496fff7e30'], 'X-Forwarded-For': ['174.129.119.192, 130.176.134.131'], 'X-Forwarded-Port': ['443'], 'X-Forwarded-Proto': ['https'], 'X-Home-Region': ['us1'], 'X-Twilio-Signature': ['FF9IVbhWh8sd7jAHNk4oVOk4LCE=']}, 'queryStringParameters': None, 'multiValueQueryStringParameters': None, 'pathParameters': None, 'stageVariables': None, 'requestContext': {'resourceId': 'ntrn04', 'resourcePath': '/supply_storage', 'httpMethod': 'POST', 'extendedRequestId': 'KK5jIE-aBcwFm4w=', 'requestTime': '24/Aug/2023:14:56:45 +0000', 'path': '/stage/supply_storage', 'accountId': '867185477215', 'protocol': 'HTTP/1.1', 'stage': 'stage', 'domainPrefix': '7l3sx25tf9', 'requestTimeEpoch': 1692889005377, 'requestId': '14f45b18-ebf3-4bb6-bc80-9ddfd3f6640e', 'identity': {'cognitoIdentityPoolId': None, 'accountId': None, 'cognitoIdentityId': None, 'caller': None, 'sourceIp': '174.129.119.192', 'principalOrgId': None, 'accessKey': None, 'cognitoAuthenticationType': None, 'cognitoAuthenticationProvider': None, 'userArn': None, 'userAgent': 'TwilioProxy/1.1', 'user': None}, 'domainName': '7l3sx25tf9.execute-api.ap-south-1.amazonaws.com', 'apiId': '7l3sx25tf9'}, 'body': 'ct=paddy&store_grade=2&user_name=Carst%20Abma&store_amount=15&user_phone=%2B31627257049&did=did%3Apolygonid%3Apolygon%3Amumbai%3A2qLhgrN1nGUMZXCwmeLFVxEPAR8ko5TXZseG445W5b', 'isBase64Encoded': False}

def StorageManagerIssuer(event,context):
    print('event', event)
    '''
    storage manager creates a credential about amount, grade and variety and includes the 
    VC in the merkle hash with some reference id to the storage location.

        - receives the DID of the user (farmer)
        - recovers the seed of the issuer he owns
        - creates the certificate
        - adds the certificate to the chain (type merkletree)
        - returns the certificate id in WABA message

        - user confirms, generates proof (standarized)
        - receives proof QR to share.

        - verifier scans QR, goes to 3th party url that verifies Zkproof
        - verfier receives result.


    '''
    try:
        input = loadData(event)
        user_phone = input['user_phone']
        user_DID = 'did:iden3:polygon:mumbai:wzwAyDLHL6Nhtj3TnFfUnP7osASXb9hS8BTfa2zeo' # input['did']
        ct = input['ct']
        print('input', input)

        # find certificate of nila issuer
        #issuer_DID = 'did:polygonid:polygon:mumbai:2qLh2QHAX7bG98SNBVJnhQUbFnLCB8VJ1uscBJvaPN'  # storage manager ISSUER
        #claims_by_issuer = requests.get(f'{issueNodeURI}/v1/{issuer_DID}/claims', auth=HTTPBasicAuth('user-issuer','password-issuer'))
        #user_claims = []
        #for claim in json.loads(claims_by_issuer.text):
        #    if claim['credentialSubject']['id'] == user_DID and claim['type'][1] == 'KYCAgeCredential':
        #        user_claims.append([claim['id'].split('/')[-1],claim['issuanceDate'],claim])
        # sort claims by issuancedata, pick last one issued.
        #user_claims.sort(key=lambda x: x[1], reverse=True)
        #print('nila_claim_id', user_claims[0])

        # create a new claim, 
        issuer_DID = 'did:polygonid:polygon:mumbai:2qLh2QHAX7bG98SNBVJnhQUbFnLCB8VJ1uscBJvaPN'  # storage manager ISSUER
        # load claim based on croptype (ct)
        claim = requests.post(f'{issueNodeURI}/v1/{issuer_DID}/claims',
                          data=claimType(ct,user_DID,input),
                          auth=HTTPBasicAuth('user-issuer','password-issuer'))
        id = json.loads(claim.text)['id']
        print('claim.text', claim.text)

        # merkle tree type credentials have to publish issuer state
        #!!!!!!!!!!!
        testclaim = {
                'id': 'urn:ae98a97e-fff5-41ea-82c3-a20330db19e6',
                '@context': [
                    'https://www.w3.org/2018/credentials/v1',
                    'https://schema.iden3.io/core/jsonld/iden3proofs.jsonld',
                    'https://raw.githubusercontent.com/iden3/claim-schema-vocab/main/schemas/json-ld/kyc-v3.json-ld'
                ],
                'type': [ 'VerifiableCredential', 'KYCAgeCredential' ],
                'credentialSubject': {
                    'id': 'did:iden3:polygon:mumbai:x3xjTtTaxq8UDqMmpVgux4RN6WWk5MBo1NuLB77FT',
                    'birthday': 19960424,
                    'documentType': 99,
                    'type': 'KYCAgeCredential'
                },
                'issuer': 'did:iden3:polygon:mumbai:wyr5G3HYFntu9EJSA4VQRpR5DxbJdbAmPo4Txtctj',
                'expirationDate': '2361-03-21T19:14:48.000Z',
                'issuanceDate': '2023-08-25T15:19:10.674Z',
                'credentialSchema': {
                    'id': 'https://raw.githubusercontent.com/iden3/claim-schema-vocab/main/schemas/json/KYCAgeCredential-v3.json',
                    'type': 'JsonSchema2023'
                },
                'credentialStatus': {
                    'id': 'https://rhs-staging.polygonid.me',
                    'revocationNonce': 5504,
                    'type': 'Iden3ReverseSparseMerkleTreeProof'
                },
                'proof': [
                    {
                        'type': 'BJJSignature2021',
                        'issuerData': {'id': 'did:polygonid:polygon:mumbai:2qLh2QHAX7bG98SNBVJnhQUbFnLCB8VJ1uscBJvaPN', 'state': {'claimsTreeRoot': 'c14430c66f7096cdf5e660ce7facb355fecfc62a57b8ef3623d45eb2f26a7f15', 'value': 'ca53e93777b5247acabb1742fed5aab3872c4778de4cde78055cdf7613a88629'}},
                        'coreClaim': 'c9b2370371b7fa8b3dab2a5ba81b68382a0000000000000000000000000000000112be2998a20ed451935259298abf9bdf74938fb15f6798db9985c70c020e0021383e360e2bc8f4f0a33e4a56d0bf0a22b52fdb0be3169fcac43acee072310900000000000000000000000000000000000000000000000000000000000000008015000000000000281cdcdf0200000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000',
                        'signature': '195b045e053f410a928755033b153aaa2e1484a14699a0a085cd4fd663c82a0a1893eea64bf0d8a49bac9048119c627f10fe717145d6bf7ca2e0413169c7e305'
                        }
                ]
                }

        # send credential and userdid to get proof
        proof = requests.post(f'{proofNodeURI}/generateProof_Sig',
                             data=json.dumps({
                                 "user_DID": user_DID,
                                 "credential": testclaim #user_claims[0]
                             }),
                            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                             )
        print('proof', proof.text)
        return
        # claims are not accepted by user to remove UX limitations of PolygonID

        # 

        # create proof based on the claim.



        # create and store QR image for the storage manager to scan and verify/issue new certs
        link = f'https://wa.me/13478481380?text=purchase%20{ct}s%20of{user_phone}&did={user_DID}&nid={id}' # attributes used by WABA to initiate Zero Knowledge proofs
        print('link', link)

        # QR links have been approved by META
        qr = qrcode.make(link)
        qr.save("/tmp/qr.png")
        type(qr)
        # From png to jpg
        resave = Image.open(r'/tmp/qr.png')
        resave.save("/tmp/qr.jpg")
        print('resaved to jpg')

        filename = id.split('-')[-1] # naming based on claim id
        bucket = 'chatbot-stage-cropcerts-10xgf6ebbroee'
        with open("/tmp/qr.jpg", "rb") as f:
            s3.upload_fileobj(f, bucket, filename,ExtraArgs={'ACL': 'public-read', 'ContentType': 'image/jpg'})
        os.remove("/tmp/qr.jpg")

        # unlike polygonID demos, verifier queries are limited to a preset list of zero-knowledge proofs that the verifier can evaluate. 
        # to verifiers it has to be clear who is the issuer.



        # verifier does not have to be Nila-linked, hence we need a flexible enough method to show available claims.


        # unlike polygon id demos, that are one-to-one, Nila is a one-to-many solution. 
        # Which means that verifiers receive a list of proofs they can choose from, without any contextual data except the issuer (Nila & storage)

        # the challenge in the food chain are not the accountability of major players such as Amazon or walmart, instead its connecting the millions of small producers and storages of
        # perishable and whole-food products. A lot of valuable food is going to waste, due to the loss of propinquity. Some estimates are that in India this can count up to 1/3 of the total produced is wasted due to 
        # transport and accountability issues. 

        # this is extremely powerful, because it allow global players to touch the many million local storage and handlers. They can verify and trust, without
        # any personal or company data revealed the individual produce origin, quantity, quality and perishability.


        # send user the new trade link QR.
        wa_user_phone = 'whatsapp:{}'.format(user_phone)
        TWILCLIENT.messages.create(
            to=wa_user_phone, 
            from_="whatsapp:+13478481380",
            body="Done. This is the new sales code. It allows potential buyers to verify origin,storage and growth conditions. Make sure you send it to your local traders or digital marketing platforms.",
            media_url='https://{}.s3.ap-south-1.amazonaws.com/{}'.format(bucket,filename)
        )

        return {
                "statusCode": 200,
                "headers": { "content-type":"application/json; charset=utf-8" },
                "body": json.dumps({ 
                    'status': 'success',                  
                    })
            }

    except Exception as e: 
        print(e)
        print('------------------------')
        return "Error"
