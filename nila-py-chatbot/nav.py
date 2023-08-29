import json
import boto3
import time
import uuid
from boto3.dynamodb.conditions import Key
from twilio.twiml.voice_response import VoiceResponse
import datetime as dt
from MODULES import loadData,ClassifyResponse,LoadWallet
from connect import newWallet

dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
client = boto3.client('dynamodb', region_name='ap-south-1')
MEMBERS = dynamodb.Table('Member-q7dz4tkcefhkdhn4snv65cvkru-stage')
DecentralizedID = dynamodb.Table('DID')
LATLNG = dynamodb.Table('Latlng-stage')
AESTABLE = dynamodb.Table('AES-stage')

def TimeOfDay(x,l):
    if (x > 5) and (x <= 12 ):
        return 'Good morning'
    elif (x > 12) and (x <= 18):
        return 'Good afternoon'
    elif (x > 18) and (x <= 21) :
        return 'Good evening'
    elif (x > 21) or (x <= 5):
        return'Good night'
    
def Webhook(event,context):
    print(event, context)
    # inspect the event for geo data
    if 'Latitude' in event and 'Longitude' in event:
        # store lat & lng with MessageSid
        LATLNG.put_item( Item={'msid' : event['MessageSid'], 'lat': event['Latitude'], 'lng': event['Longitude']})

    # continue with the flow.
    response = VoiceResponse()
    response.redirect('https://webhooks.twilio.com/v1/Accounts/AC1753552456c3570307c7a8fa2ec5bce0/Flows/FW1327ad94088d2b26f52988905062b4c6')
    print('response', str(response))
    return str(response)

def GenerateAccount(event,context):
    '''
        store account in Members table, create wallet and return PIN.
    '''
    # load params
    print('event', event)
    input = loadData(event)
    print('input', input)
    phone = input['phoneNumber'].split(':')[1]
    print('phone', phone)

    # create wallet
    PK = newWallet(phone,AESTABLE)
    wallet = {
        'pin': 0000,
        'pk': PK 
    }
    # store user in table
    dateTimeEpoch = int(time.time()*1000)    
    dateTime = str(dt.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    MEMBERS.put_item(
            Item={
                'phoneNumber' : phone,
                '__typename': '',
                'id' : uuid.uuid4().hex,
                'createdAt' : dateTime,
                'fiG' : '',
                'language' : input['language'],
                'name' : input['name'],
                'org' : '',
                'pk' : PK,
                'representative': {'name': '', 'phone': '', 'pk': ''},
                'representativeOff': [],
                'status': 0, 
                'subscriptionDate': dateTimeEpoch,
                'updatedAt' : dateTime,
            }
    )   

    return {
        "statusCode": 200,
        "headers": { "content-type":"application/json; charset=utf-8" },
        "body": json.dumps(wallet)
    }
    
def InMessageGetParams(event, context):
    print(event)
    parse_language = {
    'English': 'EN',
    'Tamil': 'TN',
    'தமிழ் (Tamil)': 'TN',
    'தமிழ் (Tamil) ': 'TN'
}

    # load the user data & understand initial request
    try:
        input = loadData(event)
        phone = input['phoneNumber'][9:] # parse phonenumber from whatsapp:+number
        status = ''
        service = ''
        print('inp', input)

        # CHECK IF RESPONSE IS A SALES EVENT
        resp = input['response'].split(' ')
        if resp[0] == 'issue':
            print('resp', resp)
            # RETURN STORAGE MANAGER FLOW.
            user_phone = '+' + resp[-1] # add + to last item in list
            print('user phone', user_phone)
            # SECURITY BREACH !!!
            # find name of user
            attr_names = {'#n': 'name','#l': 'language'} 
            fiG,org,pk,name,language,f_list = MEMBERS.query(KeyConditionExpression=Key("phoneNumber").eq(user_phone), ExpressionAttributeNames=attr_names, ProjectionExpression="#n,org,pk,#l,fiG,representativeOff")['Items'][0].values()
            # find DID of user (farmer)
            did = DecentralizedID.query(KeyConditionExpression=Key("phoneNumber").eq(user_phone), ProjectionExpression="did")['Items']    
            print('did', did)
            if len(did) == 1:
                # find name and produce
                return {
                    "statusCode": 200,
                    "headers": { "content-type":"application/json; charset=utf-8" },
                    "body": json.dumps({
                        'service': 200,
                        'ct': resp[1],
                        'did': did[0]['did'],
                        'user_name': name,
                        'user_phone': user_phone
                    })
            }
        elif input['response'].split(' ')[0] == 'proof':
            # RETURN SALES EXCHANGE FLOW
            return {
                "statusCode": '200',
                "headers": { "content-type":"application/json; charset=utf-8" },
                "body": json.dumps({
                    'service': '300'
                })
            }
        else:
            # GET USER DATA
            attr_names = {'#n': 'name','#l': 'language'} 
            fiG,org,pk,name,language,f_list = MEMBERS.query(KeyConditionExpression=Key("phoneNumber").eq(phone), ExpressionAttributeNames=attr_names, ProjectionExpression="#n,org,pk,#l,fiG,representativeOff")['Items'][0].values()
            print(org,pk,name,language,fiG,f_list)
            parsed_language = parse_language[language]
            print('parsed language', parsed_language)

            # CLASSIFY THE RESPONSE
            response = ClassifyResponse(input['response'].lower(),f_list,phone,name)
            print('response:', response)

            # LOAD WALLET
            wallet = LoadWallet(response,pk,phone)

            # SET PROFILE STATUS (unreg,reg,pending)
            status = 'unreg' if not wallet['PROP'] else 'reg' if wallet['SCORE'] else 'pending'

            # SET SERVICE (SUBFLOW)
            if not pk or any([resp in ['PROP','PROFILE','SCORE'] for resp in response['class']]):
                service = '0'
                conv = ''
                _class = response['class'][0]
            elif any([resp in ['PAY','DEPOSIT','REWARDS'] for resp in response['class']]):
                service = '1'
                conv = ''
                _class = response['class'][0]
            elif any([resp in ['CREDIT'] for resp in response['class']]):
                service = '2' 
                conv = ''
                _class = response['class'][0]
            elif any([resp in ['SALE','SELL','SUPPLY'] for resp in response['class']]):
                service = '3' 
                conv = f'Hi {name.split(" ")[0]}. Ok great. Wait one second so we take a look at your most recent field data.'
                _class = response['class'][0]
            elif any([resp in ['greetings','help','info'] for resp in response['class']]):
                service = '99' 
                conv = f'Hi {name.split(" ")[0]}. It is good to hear from you. What can I do?\n\n* Request a crop loan.\n* Send or Deposit funds.\n* Sell or store my crops.\n* Update my digital property.\n'
                _class = response['class'][0]
            else:
                service = '99'       
                conv = 'Ues sorry. could you rephrase the question?' 
                _class = response['class'][0]

            User = { 
                'username':         response['user']['name'] , 
                'service':          service, 
                'class':            _class,
                'conversation':     conv,
                'status':           status if status else input['status'],
                'wallet':           json.dumps(wallet), 
                'name':             name,
                'phone':            response['user']['phone'],
                'language':         parsed_language,
                'pk':               wallet['pk'],
                'experience':       'expert' if wallet['SCORE'] else 'beginner' 
                }  
            
            print('data being returned: ', User)  
            return {
                "statusCode": 200,
                "headers": { "content-type":"application/json; charset=utf-8" },
                "body": json.dumps(User)
            }

    except Exception as e: 
        print(e)
        print('------------------------')
        return "Error"