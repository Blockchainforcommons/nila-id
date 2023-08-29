import json
import os
import boto3
import requests
import uuid
from boto3.dynamodb.conditions import Key
from twilio.twiml.voice_response import VoiceResponse
from datetime import datetime as dt
import mercantile as mc
from nav import TimeOfDay
from MODULES import loadData,ClassifyResponse,LoadWallet,decypher_AES
from connect import newWallet
from dotenv import load_dotenv

load_dotenv()


dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
client = boto3.client('dynamodb', region_name='ap-south-1')
lamb = boto3.client('lambda')
MEMBERS = dynamodb.Table('Member-q7dz4tkcefhkdhn4snv65cvkru-stage')
SPONSORS = dynamodb.Table('Sponsors')
LATLNG = dynamodb.Table('Latlng-stage')
AESTABLE = dynamodb.Table('AES-stage')

'''
    todo
        # create table, store new wallet and personal data. 
        # create rust api. params: sk,tx_data,pk ? 
        # create rust api. structures: call contract. 
        # return success

        # create scorecard sample
        # create property sample with field notes
        # move to nila phone, create templates. 
        # prepare presentation
        # record video

        CONTRACT
        # add funds function 
        # loan intent
        # loan guarantee

        optional:
        # loan repay
        # loan repackage (collateralize with crop token)
'''

e = {'resource': '/credit_pin', 'path': '/credit_pin', 'httpMethod': 'POST', 'headers': {'Accept': '*/*', 'CloudFront-Forwarded-Proto': 'https', 'CloudFront-Is-Desktop-Viewer': 'true', 'CloudFront-Is-Mobile-Viewer': 'false', 'CloudFront-Is-SmartTV-Viewer': 'false', 'CloudFront-Is-Tablet-Viewer': 'false', 'CloudFront-Viewer-ASN': '14618', 'CloudFront-Viewer-Country': 'US', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'Host': 'w7ajuwh21b.execute-api.ap-south-1.amazonaws.com', 'I-Twilio-Idempotency-Token': 'a9cfbd7f-e95f-4f0e-8d30-d42bb82819e3', 'User-Agent': 'TwilioProxy/1.1', 'Via': '1.1 a170450d5cd56debfea916e005590e76.cloudfront.net (CloudFront)', 'X-Amz-Cf-Id': 'YnzzX-B03Pfm5cj66P1sm_s9IzaetliA3k4uQglBrfNcK6_JyOqp6Q==', 'X-Amzn-Trace-Id': 'Root=1-64baac72-581cf20173f05e137ee1ce09', 'X-Forwarded-For': '3.88.127.145, 15.158.60.52', 'X-Forwarded-Port': '443', 'X-Forwarded-Proto': 'https', 'X-Home-Region': 'us1', 'X-Twilio-Signature': 'pl/gVGXQihHP9BASu1v6z/08iUM='}, 'multiValueHeaders': {'Accept': ['*/*'], 'CloudFront-Forwarded-Proto': ['https'], 'CloudFront-Is-Desktop-Viewer': ['true'], 'CloudFront-Is-Mobile-Viewer': ['false'], 'CloudFront-Is-SmartTV-Viewer': ['false'], 'CloudFront-Is-Tablet-Viewer': ['false'], 'CloudFront-Viewer-ASN': ['14618'], 'CloudFront-Viewer-Country': ['US'], 'Content-Type': ['application/x-www-form-urlencoded; charset=UTF-8'], 'Host': ['w7ajuwh21b.execute-api.ap-south-1.amazonaws.com'], 'I-Twilio-Idempotency-Token': ['a9cfbd7f-e95f-4f0e-8d30-d42bb82819e3'], 'User-Agent': ['TwilioProxy/1.1'], 'Via': ['1.1 a170450d5cd56debfea916e005590e76.cloudfront.net (CloudFront)'], 'X-Amz-Cf-Id': ['YnzzX-B03Pfm5cj66P1sm_s9IzaetliA3k4uQglBrfNcK6_JyOqp6Q=='], 'X-Amzn-Trace-Id': ['Root=1-64baac72-581cf20173f05e137ee1ce09'], 'X-Forwarded-For': ['3.88.127.145, 15.158.60.52'], 'X-Forwarded-Port': ['443'], 'X-Forwarded-Proto': ['https'], 'X-Home-Region': ['us1'], 'X-Twilio-Signature': ['pl/gVGXQihHP9BASu1v6z/08iUM=']}, 'queryStringParameters': None, 'multiValueQueryStringParameters': None, 'pathParameters': None, 'stageVariables': None, 'requestContext': {'resourceId': '7o5wbh', 'resourcePath': '/credit_pin', 'httpMethod': 'POST', 'extendedRequestId': 'Ia_h-HbCBcwFuhA=', 'requestTime': '21/Jul/2023:16:04:02 +0000', 'path': '/stage/credit_pin', 'accountId': '867185477215', 'protocol': 'HTTP/1.1', 'stage': 'stage', 'domainPrefix': 'w7ajuwh21b', 'requestTimeEpoch': 1689955442703, 'requestId': '54e8c91c-f0d0-4352-8f73-aa917018e266', 'identity': {'cognitoIdentityPoolId': None, 'accountId': None, 'cognitoIdentityId': None, 'caller': None, 'sourceIp': '3.88.127.145', 'principalOrgId': None, 'accessKey': None, 'cognitoAuthenticationType': None, 'cognitoAuthenticationProvider': None, 'userArn': None, 'userAgent': 'TwilioProxy/1.1', 'user': None}, 'domainName': 'w7ajuwh21b.execute-api.ap-south-1.amazonaws.com', 'apiId': 'w7ajuwh21b'}, 'body': 'area=-10060.430690078065&all_fields=%5B%22P3%22%2C%20%22P6%22%2C%20%22P8%22%2C%20%22P4%22%2C%20%22P1%22%2C%20%22P7%22%2C%20%22P5%22%2C%20%22P2%22%5D&amount=100000&wallet=%7B%22cht%22%3A%2027%2C%20%22algo%22%3A%201145.0%2C%20%22PROP%22%3A%20%5B117878703%2C%201%2C%20%22https%3A%2F%2Fgateway.pinata.cloud%2Fipfs%2FQmdGXsTvx6KQ3Xfx11sZhx9Z1GzrGh7rbnqTiEpPV8PZKc%22%5D%2C%20%22SCORE%22%3A%20false%2C%20%22LABEL%22%3A%20false%2C%20%22inr%22%3A%202700%2C%20%22asset_string%22%3A%20%22%20-%20Millets%20%3A%200%2C%20-%20chitta-property%20%3A%201%22%2C%20%22app_string%22%3A%20%22None%22%2C%20%22pk%22%3A%20%22OR2CGJNLF6PYF53QFOESNY7LGDOF2FULUJ3OBOKAEBSPXJ47DLALS45QNM%22%7D&pin=592&phone=whatsapp%3A%2B31627257049&rate=5&sponsors=%5B%7B%22business_name%22%3A%20%22Arani%20Food%20Export%22%2C%20%22name%22%3A%20%22mr.%20Carst%20Abma%22%2C%20%22phonenumber%22%3A%20%22%2B31627257049%22%7D%2C%20%7B%22business_name%22%3A%20%22Magarantham%20Ltd%20FPO%22%2C%20%22name%22%3A%20%22mr.%20Anandan%20Pandurangan%22%2C%20%22phonenumber%22%3A%20%22%2B316272570490%22%7D%5D&name=Carst%20Abma&l=EN&selected_fields=p2%2Cp5%2Cp8%2Cp1%2Cp4%2Cp3%2Cp6%2Cp7&croptype=paddy', 'isBase64Encoded': False}

def InitialCreditRequest(event,context):
    #print(event)
    '''
    validate location and liquidity. Return approve/denial

        - fetch location in prop nft, find vetted partners
        - list field names
        - fetch liquidity in contract
    '''
    try:
        input = loadData(event)
        print('input', input)
        # contract liquidity call
        liq = True
        # load prop token metadata
        url = json.loads(input['wallet'])['PROP'][2]
        request = json.loads(requests.get(url).content)
        # find sponsors in the area by tile xy coordinates
        POINTS = [f['coordinate'] for f in request['properties']['names_by_coordinate']]
        list_all_tiles = [mc.tile(float(point[1]),float(point[0]), 15) for point in POINTS]
        most_freq_tile = max(set(list_all_tiles))
        tile_string = str(most_freq_tile.x)[:4] + str(most_freq_tile.y)[:4]
        # lookup sponsors by xy coordinates
        attr_names = {'#n': 'name','#bn': 'business_name','#ph': 'phonenumber'} 
        sp = SPONSORS.query(KeyConditionExpression=Key("tile").eq(int(tile_string)), ExpressionAttributeNames=attr_names, ProjectionExpression="#n,#bn,#ph,pk")['Items']
        print('sp', sp)
        loc = True if len(sp) > 0 else False
        if liq and loc:
            res = 'APPROVE' # DENY or APPROVE
            reason = ''
            sponsors = sp        
            sponsors_string = ''.join(['\n * {} - {}'.format(s['business_name'],s['name']) for s in sp])
            fields = [f['name'] for f in request['properties']['names_by_coordinate']]
            fields_string = ''.join([' * {}\n'.format(f) for f in fields])
            print('field string', fields_string)
            return {
                "statusCode": 200,
                "headers": { "content-type":"application/json; charset=utf-8" },
                "body": json.dumps({ 'res' : res, 'reason': reason, 'sponsors' : json.dumps(sponsors), 'sponsor_string': sponsors_string, 'fields': json.dumps(fields), 'field_string': fields_string, 'area': request['properties']['area'] }) # return validation result
            }
        else:
            res = 'DENY'
            reason = '_insufficient liquidity in the protocol_ Please try again later.' if not liq else '_no vetted sponsors in your area._ Please ask your local cooperative, trader or banking institution to register as a Nila supply and finance partner.'
            return {
                "statusCode": 200,
                "headers": { "content-type":"application/json; charset=utf-8" },
                "body": json.dumps({ 'res' : res, 'reason': reason }) # return validation result and reason if denied
            }

    except Exception as e: 
        print(e)
        print('------------------------')
        return "Error"

def CreditRequirements(event,context):
    print(event)

    rate_amount_table = {
        #by croptype and total cultivated size
        'paddy': {
            1000: {1: [ 20000, 9],2: [ 20000, 8],3: [ 20000, 5],4: [ 20000, 5],5: [ 20000, 4]},
            2000: {1: [ 30000, 9],2: [ 30000, 8],3: [ 30000, 5],4: [ 30000, 5],5: [ 30000, 4]},
            3000: {1: [ 40000, 9],2: [ 40000, 8],3: [ 40000, 5],4: [ 40000, 5],5: [ 40000, 4]},
            4000: {1: [ 50000, 9],2: [ 50000, 8],3: [ 50000, 5],4: [ 50000, 5],5: [ 50000, 4]},
            5000: {1: [ 60000, 9],2: [ 60000, 8],3: [ 60000, 5],4: [ 60000, 5],5: [ 60000, 4]},
            6000: {1: [ 70000, 9],2: [ 70000, 8],3: [ 70000, 5],4: [ 70000, 5],5: [ 70000, 4]},
            7000: {1: [ 80000, 9],2: [ 80000, 8],3: [ 80000, 5],4: [ 80000, 5],5: [ 80000, 4]},
            8000: {1: [ 90000, 9],2: [ 90000, 8],3: [ 90000, 5],4: [ 90000, 5],5: [ 90000, 4]},
            9000: {1: [ 100000, 9],2: [ 100000, 8],3: [ 100000, 5],4: [ 100000, 5],5: [ 100000, 4]},
            10000: {1: [ 100000, 9],2: [ 100000, 8],3: [ 100000, 5],4: [ 100000, 5],5: [ 100000, 4]},
            11000: {1: [ 110000, 9],2: [ 110000, 8],3: [ 110000, 5],4: [ 110000, 5],5: [ 110000, 4]},
        }
    }
    '''
    calculate loan offer, return offer

        - fetch score card, estimated size, croptype 
        - match data to amnt/rate table
        - fetch liquidity in contract
    '''
    try:
        input = loadData(event)
        print('input', input)
        # read selected fields string as list
        selected = input['selected_fields'].split(',')
        # estimate size by taking all fields as similar size (up for improvement)
        size = round((len(selected) / len(json.loads(input['all_fields']))) * abs(float(input['area'])),-3)
        
        # determine score
        # DUMMY score (1 - 5, 5 being high change of success, 2 being low change of success in category (paddy,industrial farming))
        score = 3
        # find amount and rate
        table_lookup = rate_amount_table['paddy'][int(size)][score]
        # find 3month base rate
        _3month = table_lookup[0] * (table_lookup[1]/100) + table_lookup[0]
        print('_3month', _3month)
        # sponsors 
        nmb_of_sponsors = '2 sponsors' if table_lookup[0] > 100000 or table_lookup[1] < 3 else '1 sponsor'
        return {
            "statusCode": 200,
            "headers": { "content-type":"application/json; charset=utf-8" },
            "body": json.dumps({ 'amount' : table_lookup[0], 'rate': table_lookup[1], 'total_base': int(_3month), 'req_vouched': nmb_of_sponsors }) # return loan offer based on score card
        }

    except Exception as e: 
        print(e)
        print('------------------------')
        return "Error"

def Contract_intent(event,context):
    from twilio.rest import Client
    account_sid = os.getenv("ACCOUNT_SID")
    auth_token = os.getenv("AUTH_TOKEN")

    TWILCLIENT = Client(account_sid, auth_token)
    print(event)
    '''
    check pin validity
        - decipher sk with pin
        - create intent on contract - store crop,field coordinates,daily rate,loan amount
        - create media from score card
        - send messages to sponsors
    '''
    try:
        input = loadData(event)
        print('input', input)
        sponsors = json.loads(input['sponsors'])
        print('sponsors', sponsors)
        # pin liquidity of sponsors (sponsors are vetted to a certain amount that they can't surpass)

        # load wallet data.
        #FL,SK,PK,apps_to_optin,assets_to_optin,prop,assets = decypher_AES(input,[],[])
        SK = '0x03c1b740fdddbe67edae30443b969da79aa8c0d055486fe185b82f34a719c2ca'
        #print(SK)
        
        # create intent (call contract)
        resp = lamb.invoke(
            FunctionName='arn:aws:lambda:ap-south-1:867185477215:function:call-fuel-ts-stage-wallet',
            InvocationType='Event',
            Payload=json.dumps({
                'type': 100,  # 100-200 are contract calls
                'duration': 3,
                'SK': SK,
                'sponsors': input['sponsors'],
                'amount': input['amount'],
                'rate': input['rate'],
                'phone': input['phone']
                }),
            LogType='Tail'
        )
        print('response', resp['ResponseMetadata'])
        print(resp['Payload'].read())
        # create score card

        
        # send sponsor invitations
        ToD = TimeOfDay(dt.now().hour + 5.5,input['l']) #hacky to change UTC to IST.
        for sponsor in sponsors:
            body = 'NEW SPONSORSHIP REQUEST:\n\n{} {}.\n\n*{} has requested a Rs. {}/- credit line for a {} cultivation.*'.format(ToD,sponsor['name'],input['name'],input['amount'],input['croptype']),
            url = ''
            rate_sponsorship = int(input['rate']) - 3 # base rate for liquidity providers is 3%.
            if sponsor['phonenumber'] == '+31627257049': # dev only send to dev
                TWILCLIENT.studio \
                  .v2 \
                  .flows('FW1327ad94088d2b26f52988905062b4c6') \
                  .executions \
                  .create(
                    to="whatsapp:" + sponsor['phonenumber'], 
                    from_="whatsapp:+13478481380",
                    parameters={
                       'service': '100', # sponsorship inrequest code
                       'tod': ToD,
                       'sponsor_name': sponsor['name'],
                       'sponsor_phone': sponsor['phonenumber'],
                       'name': input['name'],
                       'amount': input['amount'],
                       'rate': rate_sponsorship,
                       'crop': input['croptype'],
                       'url': url,
                       'resp': resp,
                       'conversation': body
                   }
                   )

        return {
            "statusCode": 200,
            "headers": { "content-type":"application/json; charset=utf-8" },
            "body": json.dumps({ 'success' : 1 }) # return loan offer based on score card
        }
        
    except Exception as e: 
        print(e)
        print('------------------------')
        return "Error"

def Contract_guarantee(event, context):
    from twilio.rest import Client

    account_sid = os.getenv("ACCOUNT_SID")
    auth_token = os.getenv("AUTH_TOKEN")
    TWILCLIENT = Client(account_sid, auth_token)
    print(event)
    '''
        - check pin validity
        - decipher sk with pin
        - sign predicate byteroot
        - inform (send message) borrower and sponsor 
    '''
    try:
        input = loadData(event)
        print('input', input)
        
        # load wallet data.
        ALGO,SK,PK,apps_to_optin,assets_to_optin,prop,assets = decypher_AES(input,[],[])
        #print(SK)
        
        # create guarantee (call contract)
        resp = lamb.invoke(
            FunctionName='arn:aws:lambda:ap-south-1:867185477215:function:call-fuel-ts-stage-wallet',
            InvocationType='Event',
            Payload=json.dumps({
                'type': 101,  # 100-200 are contract calls
                'predicate': input['resp'],
                'SK': SK,
                'phone': input['phone'],
                'borrower': input['borrower_phone']
                }),
            LogType='Tail'
        )

        '''
        # send update to invitations
        ToD = TimeOfDay(dt.now().hour + 5.5,input['l']) #hacky to change UTC to IST.
        for sponsor in sponsors:
            body = 'NEW SPONSORSHIP REQUEST:\n\n{} {}.\n\n*{} has requested a Rs. {}/- credit line for a {} cultivation.*'.format(ToD,sponsor['name'],input['name'],input['amount'],input['croptype']),
            url = ''
            rate_sponsorship = int(input['rate']) - 3 # base rate for liquidity providers is 3%.
            if sponsor['phonenumber'] == '+31627257049': # dev only send to dev
                TWILCLIENT.studio \
                  .v2 \
                  .flows('FW1327ad94088d2b26f52988905062b4c6') \
                  .executions \
                  .create(
                    to="whatsapp:" + sponsor['phonenumber'], 
                    from_="whatsapp:+13478481380",
                    parameters={
                       'service': '100', # sponsorship inrequest code
                       'tod': ToD,
                       'sponsor_name': sponsor['name'],
                       'sponsor_phone': sponsor['phonenumber'],
                       'name': input['name'],
                       'amount': input['amount'],
                       'rate': rate_sponsorship,
                       'crop': input['croptype'],
                       'url': url,
                       'resp': resp,
                       'conversation': body
                   }
                   )
        '''

        return {
            "statusCode": 200,
            "headers": { "content-type":"application/json; charset=utf-8" },
            "body": json.dumps({ 'success' : 1 }) # return loan offer based on score card
        }
        
    except Exception as e: 
        print(e)
        print('------------------------')
        return "Error"

'''
if __name__ == "__main__":
   Contract_intent(e,'')
'''