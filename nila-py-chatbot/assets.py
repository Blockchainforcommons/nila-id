import json
import os
import boto3
from datetime import datetime as dt, timedelta, timezone
import time
import uuid
from base64 import b64decode
import requests
from MODULES import loadData, decypher_AES, Find_match,FORMAT_CROP,FORMAT_DATE,format_coding_as_crop
from connect import check_if_local_state_has_asset,CompletedSearchIndex,CropTagReloop,PropAssetReloop,getAssetInfo,requestProperty,requestCropLabel,requestFarmMaster,optinFarmMasterToken,optinAppsAssets,optOutApp,getAccountAssetInfo,getAccountInfo,pending_in_local_state,SCORE_assetURL,receiveProperty
from Masteraccount import algoFaucet
from dotenv import load_dotenv

load_dotenv()

lamb = boto3.client('lambda')
s3 = boto3.client('s3')
CHTID = 38909410

'''
    CREATE + UPDATE FLOW:
        # PROPERTY
        - User sends points of each field, initiating payment and tracker method
        - Nodes find boundaries in map
            - nodes run seperator algorithm on area + squared areas if point not found
            - nodes apply for asset with property and field bounds.
        - User receives feedback from tracker method (success,some issues,no size match)
        - User send opt-in message
        - User receives asset and views property boundary.
        - User decides to edit
            - User views numbered field boundaries
            - asked to remove by number
            - asked to add area by new point
        - Nodes apply to update metatag with the new property and field boundaries

         # SCORE
         - User request score card
         - Nodes run object detection algorithm
         - Nodes detect cultivations in last 3-5 years.
         - Nodes predict crop type, yield and eos
         - Nodes apply for score card asset
         - User sends opt-in message
         - User receives and views score card

         # LABEL
         - User inputs crop type, eos(month) and variety
         - Nodes return likematch by type and predict yield and eos(day)
         - Nodes request cropasset send to user
         - User receives assets
         - User adds new input, fertilization,weeding,pesticidation
         - Nodes return likematch

    DELETE
        # PROPERTY
        - AADHAVA requests burn by asset-id
        - AADHAVA users cryptographic key to retreive pin

        # SCORE
        - IDEM as Property

        # LABEL
        - Nodes revalidate label, apply for clawback of assets
        - Nodes determine dorment assets, apply for clawback of assets
        - User request destruction of assets


    Updated Create|View Property and Score UX:
        create property invokes a response call (15 min)
        if not answered within 15 minutes, create is considered failed and money_back procedure started
        if answered, find url in local state and create image,then return user message
        optin to asset and return the image url.
    
    Edit Property and Score UX:
        use dynamic variables to update metatag, not asset
        ask for new points and add grid of points to remove..

'''
# PROP
def PropertyAssetView(event, context):
    #print(event)
    try:
        input = loadData(event)
        print('input', input)
        # load property asset metadata
        url,score = getAccountInfo(input['pk'])
        print('url:',url,'pin:', input['pin'])
        # find out if url key exists and has been updated in the last seconds
        try:
            if not url and not input['pin']:
                return {
                    "statusCode": 200,
                    "headers": { "content-type":"application/json; charset=utf-8" },
                    "body": json.dumps({ 'url' : 1, 'prop_stat': 'PENDING'}) # return names and points as in liquid template string seperated by $
                }
            elif not url and input['pin']:
                print('run receive asset...')
                # find out if the asset has already been moved to the user wallet (check app local state)
                pending_asset = check_if_local_state_has_asset(input['pk'])
                print('pending asset', pending_asset)
                # load wallet data
                ALGO,SK,PK,apps_to_optin,assets_to_optin,prop,assets = decypher_AES(input,[],[])
                print('requesting asset..')
                receiveProperty(
                    appID=117683187,
                    PK=PK, 
                    SK=SK,
                    assetID=pending_asset
                )
                print('property received completed..')
                return {
                    "statusCode": 200,
                    "headers": { "content-type":"application/json; charset=utf-8" },
                    "body": json.dumps({ 'url' : 0, 'prop_stat': 'RECEIVED'}) # return names and points as in liquid template string seperated by $
                }
            
            # return the media url and text
            bucket = 'chatbot-stage-cropcerts-10xgf6ebbroee'
            filename = 'PROP' + url.split('/')[-1]
            print('created filename', filename)
            metadata = s3.head_object(Bucket=bucket, Key=filename)
            if dt.now(timezone.utc) > metadata['LastModified'] + timedelta(minutes=1):  # check if updated in the last minute.
                media_url = 'https://{}.s3.ap-south-1.amazonaws.com/{}'.format(bucket,filename) 

        except Exception as e:
            print('e', e)
            # get plotted geometry on satmap from GEOMMAPPLOT function in chitta_sensing package
            print('invoke lambda to generate images..')
            lamb.invoke(
                FunctionName='arn:aws:lambda:ap-south-1:867185477215:function:Chitta-Sensing-stage-GEOMMAPPLOT',
                InvocationType='Event', # we dont have to wait for it. as we know the url. 
                Payload=json.dumps({'type': 'V', 'url': url}),
                LogType='Tail'
            )
            media_url = 0
        
        print('media url to send back:', media_url)
        return {
            "statusCode": 200,
            "headers": { "content-type":"application/json; charset=utf-8" },
            "body": json.dumps({ 'url' : media_url, 'prop_stat': 'UNVERIFIED' if not score else 'POSSIBLE CONFLICTS'}) # return names and points as in liquid template string seperated by $
        }
        
    except Exception as e: 
        print(e)
        print('------------------------')
        return "Error"

def PropertyAssetEdit(event, context):
    #print(event)
    # MAKE SURE YOU REMOVE THE OLD IMAGE IN THE BUCKET!    
    # SEND OLD ASSET TO BURN (SEND TO CREATOR ADDRESS)
    try:
        input = loadData(event)
        # load property asset metadata
        url = getAccountInfo(input['pk'])
        print(url)
        # get plotted geometry on satmap from GEOMMAPPLOT function in chitta_sensing package
        lamb.invoke(
            FunctionName='arn:aws:lambda:ap-south-1:867185477215:function:Chitta-Sensing-stage-GEOMMAPPLOT',
            InvocationType='Event', # we dont have to wait for it. as we know the url. 
            Payload=json.dumps({'type': 'E', 'url': url}),
            LogType='Tail'
        )
        # return the media url and text
        bucket = 'chatbot-stage-cropcerts-10xgf6ebbroee'
        filename = 'PROP' + '-E-' + url.split('/')[-1]
        media_url = 'https://{}.s3.ap-south-1.amazonaws.com/{}'.format(bucket,filename) 
        return {
            "statusCode": 200,
            "headers": { "content-type":"application/json; charset=utf-8" },
            "body": json.dumps({ 'url' : media_url }) # return names and points as in liquid template string seperated by $
        }
        
    except Exception as e: 
        print(e)
        print('------------------------')
        return "Error"

def PropertyAssetCreate(event, context):
    '''
        flows:
            - reset a specific field before asset create
            - retry request, check if the tx has been made
            - request, invoke response method and send deposit
    '''
    appIDs = [117683187]
    assetIDs = [] # no assets involved
    print(event)
    try:
        input = loadData(event)
        print(input)

        # RESET SPECIFIC FIELD
        if 'list-responds' in input and input['list_responds'].lower() not in ['ok','done','completed','finish','finished','continue','cont','continu','continues','con','c']:
            # first lowercase each fieldname
            points = input['points'].split('$')# string is seperated with $ sign.
            names = input['names'].split('$')# string is seperated with $ sign.
            print('names', names)
            names = [{ 'name' :name.lower()} for name in names]
            # match words, sort by highest rank
            r = [Find_match(word.lower(),names,'','') for word in input['list_responds'].split(' ')]
            print('r', r)
            r.sort(key=lambda x: x[1], reverse=True)
            print('sorted r', r)
            if r[0][1] > 50:
                w = r[0][0]['name']
                print('w', w)
                clean_names = [n['name'] for n in names]
                print('clean naames', clean_names)
                # found match
                index = clean_names.index(w) if w in clean_names else -1
                points.pop(index)
                names.pop(index)
                print('names,points','$'.join([n['name'] for n in names]),'$'.join(points))
                return {
                    "statusCode": 200,
                    "headers": { "content-type":"application/json; charset=utf-8" },
                    "body": json.dumps({ 'points' : '$'.join(points),'names':'$'.join([n['name'] for n in names]), 'removed_name': w }) # return names and points as in liquid template string seperated by $
                }     
        elif 'retry' in input and input['retry']:
            print('CHECK IF SUCCESSFULL')
            # RETRY LOOP, IN CASE THE TXN HAS COMPLETED WITHIN THE TWILIO OPEN REQUEST TIME
            # check address txn in last round has completed.
            trues = PropAssetReloop(input['pk'])
            return {
                    "statusCode": 200,
                    "headers": { "content-type":"application/json; charset=utf-8" },
                    "body": 1 if trues > 1 else 0
                }
        
        # REQUEST ASSET (user signaled completion)
        else:
            points = input['points'].split('$')# string is seperated with $ sign.
            names = input['names'].split('$')# string is seperated with $ sign.
            ALGO,SK,PK,apps_to_optin,assets_to_optin,prop,assets = decypher_AES(input,appIDs,assetIDs)
            print('data from wallet check: ',ALGO,SK,PK,apps_to_optin,assets_to_optin)

            # filter size out of string
            estimated_size = [int(s) for s in input['size'].split(' ') if s.isnumeric()]
            print('estimated_size', estimated_size)

            # REQUIREMENT CHECK (OPTIN)
            optinAppsAssets(sender=PK,SK=SK,app_indexes=appIDs,asset_indexes=assetIDs) if apps_to_optin + assets_to_optin else print('no need to optin')

            # REQUEST ALGO FROM FAUCET IF INSUFFICIENT
            algoFaucet(PK) if ALGO < 1000 else None

            # make sure points are floats in a tuple.
            points = [(float(p.split(',')[0]),float(p.split(',')[1])) for p in points]
            print(points)

            # initiate RequestCompleted to monitor if the property asset has been minted - only open for 15 minutes..
            lamb.invoke(
                    FunctionName='arn:aws:lambda:ap-south-1:867185477215:function:chitta-chatbot-stage-PropertyAssetResponse',
                    InvocationType='Event',
                    Payload=json.dumps({'app': appIDs[0], 'pk': PK, 'phoneNumber': input['phoneNumber'],'l': input['l']}), 
                    LogType='Tail'
            )
            
            # REQUEST PROPERTY (deposit CHT with note describing points,names,size..)
            status = requestProperty(
                appID=appIDs[0],
                PK=PK,
                SK=SK,
                amount=2,
                CHT=CHTID,
                size=int(estimated_size[0]) if estimated_size else 0,
                coordinates=points,
                names=names,
                params={'id': uuid.uuid4().hex}
            )

            print('status', status)
            # RETURN AND CLOSE REQUEST. ADD MESSAGE QUEUE WITH PIN AS UX REQUIRE REQUEST OF ASSET AFTER CREATION
            if status: return {"statusCode": 200,"headers": { "content-type":"application/json; charset=utf-8" },"body": 1}
            else: return {"statusCode": 200,"headers": { "content-type":"application/json; charset=utf-8" },"body": 0}
        
    except Exception as e: 
        print('--------ERROR---------\n',e)
        return {"statusCode": 200,"headers": { "content-type":"application/json; charset=utf-8" },"body": 2}

def PropertyAssetResponse(event,context):
    message_success = {
        'English': 'Good news. Enter your pin to receive your digital property.',
        'Tamil': 'Good news. Enter your pin to receive your digital property.',
        'Kannada': 'Good news. Enter your pin to receive your digital property.',
    }
    message_failure = {
        'English': 'Sorry to say but the network has not been able to find a property on the location that is similar to the reported size. Try again, it is often good to add more points. Check if your GPS after every step.',
        'Tamil': 'Sorry to say but the network has not been able to find a property on the location that is similar to the reported size. To try again, it is often good to add more points. Check if your GPS after every step.',
        'Kannada': 'Sorry to say but the network has not been able to find a property on the location that is similar to the reported size. To try again, it is often good to add more points. Check if your GPS after every step.',
    }
        
    from twilio.rest import Client
    account_sid = os.getenv("ACCOUNT_SID")
    auth_token = os.getenv("AUTH_TOKEN")
    TWILCLIENT = Client(account_sid, auth_token)
    '''
        Listen to the applications local state, is there a prop asset pending, create view images and return message to collect asset
    '''
    print('event', event)
    time_left_untill_kill = 40000 # sleep time + 10 sec.
    remaining = context.get_remaining_time_in_millis()

    while True : 
        local_state = pending_in_local_state(event['pk'],event['app'],b'score_id')
        print('remaining time:', remaining)
        if local_state:
            '''
            - we found a new asset
            - get the url param from the asset in local state
            - we create the edit and view state images
            - we return a message to collect the asset
            '''
            # url params
            url = getAssetInfo(local_state)['url']
            # get plotted geometry on satmap from a API
            lamb.invoke(
                FunctionName='arn:aws:lambda:ap-south-1:867185477215:function:Chitta-Sensing-stage-GEOMMAPPLOT',
                InvocationType='Event', # we dont have to wait for it. as we know the url. 
                Payload=json.dumps({'url': url}),
                LogType='Tail'
            )
            # send the message to collect the asset (MANDATORY)
            TWILCLIENT.messages.create(
                to="whatsapp:{}".format(event['phoneNumber']), 
                from_="whatsapp:+13478481380",
                body=message_success[event['l']]
            )
        else:
            if remaining < time_left_untill_kill:
                print('break', remaining < time_left_untill_kill)
                break
            else:
                print('no break', remaining < time_left_untill_kill)
                time.sleep(30)

    # TIME IS UP AND WE HAVE NOT RECEIVED ANY PROPERTY ASSET.
    TWILCLIENT.messages.create(
        to="whatsapp:{}".format(event['phoneNumber']), 
        from_="whatsapp:+13478481380",
        body=message_failure[event['l']]
    )
    print('return None. End invocation...')
    return

# SCORE
def ScoreAssetView(event, context):
    #print(event)
    try:
        input = loadData(event)
        print(input)
        # find the asset and look for the metadata url.
        url,amount = SCORE_assetURL(input['pk'])
        print(url,amount)
        if amount == 0: # return pending if amount is zero
            return {
            "statusCode": 200,
            "headers": { "content-type":"application/json; charset=utf-8" },
            "body": json.dumps({ 'status' : 'pending' })
        }
        else:
            request = json.loads(requests.get(url).content)
            # parse the url data for the API

            return {
            "statusCode": 200,
            "headers": { "content-type":"application/json; charset=utf-8" },
            "body": json.dumps({ 'status' : 'available' })
        }
        
    except Exception as e:
        print(e)
        return {
            "statusCode": 200,
            "headers": { "content-type":"application/json; charset=utf-8" },
            "body": json.dumps({ 'status' : 'failure' })
        }

def ScoreAssetCreate(event, context):
    #print(event)    
    appIDs = [109074583]
    assetIDs = [] # no assets involved
    '''
        flows:
            state = C:
            - redo a specific field before asset create
            - asset create
            otherwise:
            - asset receive and view
            - asset destroy and create (update)
    '''
    try:
        input = loadData(event)
        print(input)
        # find SK. 
        ALGO,SK,PK,apps_to_optin,assets_to_optin,prop = decypher_AES(input,appIDs,assetIDs)
        print('data from wallet check: ',ALGO,SK,PK,apps_to_optin,assets_to_optin,prop)

        # REQUEST ALGO FROM FAUCET IF INSUFFICIENT
        algoFaucet(PK) if ALGO < 1000 else None
        
        try:
            # REQUEST PROPERTY (deposit CHT with note describing points,names,size..)
            stat = requestFarmMaster(
                appID=appIDs[0],
                PK=PK,
                SK=SK,
                algoAmount=400_000,
                CHTAmount=6,
                CHTID=CHTID,
                PropertyAssetID=prop[0], # temp add prop asset as CHT (ONLY DEV)
            )
            print('status', stat)
            
            # OPTIN TO NEWLY CREATED SCORE ASSET (ARC-19 TYPE)
            optin = optinFarmMasterToken(
                assetID=pending_in_local_state(PK,appIDs[0],b'score_id'),
                PK=PK,
                SK=SK
            )
            print('optin', optin)

            if stat and optin:
                # SUCCESS
                return {
                    "statusCode": 200,
                    "headers": { "content-type":"application/json; charset=utf-8" },
                    "body": 1
                }
            else: 
                # PROP ISSUE
                return {
                "statusCode": 200,
                "headers": { "content-type":"application/json; charset=utf-8" },
                "body": 0
                }
        except Exception as e:
            print(e)
            # TECH ISSUE
            return {
                "statusCode": 200,
                "headers": { "content-type":"application/json; charset=utf-8" },
                "body": 2
            }
    except: 
        # PINCODE INCORRECT
        return {
                "statusCode": 200,
                "headers": { "content-type":"application/json; charset=utf-8" },
                "body": 3
            }

# LABEL
def FormatData(event, context):
    #print(event)
    try:
        input = loadData(event)
        print(input)
        CODING,CROP = FORMAT_CROP(input['crop'])
        print(CODING,CROP)
        DATE,ACTION = FORMAT_DATE(input['EOS'])
        print(DATE,ACTION)
        return {
            "statusCode": 200,
            "headers": { "content-type":"application/json; charset=utf-8" },
            "body": json.dumps({ 'action' : ACTION, 'crop': CROP, 'crop_codex': CODING, 'date': DATE.strftime("%d%B%Y") })
        }
    except Exception as e:
        print(e)
        return {
            "statusCode": 200,
            "headers": { "content-type":"application/json; charset=utf-8" },
            "body": json.dumps({ 'action' : 'failure', 'crop': '', 'crop_codex': '', 'date': '' })
        }

def GradeRequest(event, context):
    print(event)

def LabelRequest(event, context):
    #print(event)
    appIDs = [119275134]
    try:
        input = loadData(event)
        print(input)
        date_to_timestamp = int(dt.strptime(input['date'], '%d%B%Y').strftime("%s"))
        if 'pk' in input:
                print('CHECK IF SUCCESSFULL')
                # RETRY LOOP, IN CASE THE TXN HAS COMPLETED WITHIN THE TWILIO OPEN REQUEST TIME
                # check address txn in last round has completed.
                trues = CropTagReloop(input['pk'])
                return {
                        "statusCode": 200,
                        "headers": { "content-type":"application/json; charset=utf-8" },
                        "body": json.dumps({ "status": 1 if trues > 1 else 0 })
                    }
        else:
            print('REQUEST CROPLABEL')
            assetIDs = [int(input['crop_codex'])] # asset involved
            # find SK. 
            ALGO,SK,PK,apps_to_optin,assets_to_optin,prop,assets = decypher_AES(input,appIDs,assetIDs)
            print('data from wallet check: ',ALGO,SK,PK,apps_to_optin,assets_to_optin,prop)

            # find asset_balance of the commodity
            balance = [v[1] for k,v in assets.items() if v[0] == int(input['crop_codex'])]
            amnt = balance[0] if balance else 0
            print('balance', balance)

            # REQUEST ALGO FROM FAUCET IF INSUFFICIENT
            algoFaucet(PK) if ALGO < 1000 else None

            # OPTIN TO THE ASSETS/APPS REQUIRED
            try:
                optinAppsAssets(PK,SK,apps_to_optin,assets_to_optin) if apps_to_optin or assets_to_optin else None
            except:
                pass

            # initiate RequestCompleted to monitor if the token deposit has been made - only open for 15 minutes..
            lamb.invoke(
                    FunctionName='arn:aws:lambda:ap-south-1:867185477215:function:chitta-chatbot-stage-LabelResponse',
                    InvocationType='Event',
                    Payload=json.dumps({'date': input['date'],'prop_url': prop[2],'w_phone_friend': input['phone'],'w_name_friend': input['username'],'w_phone_user': input['phone_user'],'app': appIDs[0], 'pk': PK, 'asset_amnt': amnt, 'asset_id': assetIDs[0], 'variety': input['variety']}), # hasOptedIn = [id,amnt] or empty if 0 amnt
                    LogType='Tail'
            )

            # send crop tag request
            requestCropLabel(
                appID=appIDs[0],
                PK=PK,
                SK=SK,
                algoAmount=1000,
                CHTAmount=1,
                CHTID=38909410,
                direct=1,
                params={'crop_codex': input['crop_codex'], 'variety': input['variety'], 'eos': date_to_timestamp, 'grade': input['grade'], 'id': uuid.uuid4().hex, 'type': 3} # add random id to make sure algorand doesnt add same signature to repetitive txns
            )

            print('lambda completed') 
            return {
                    "statusCode": 200,
                    "headers": { "content-type":"application/json; charset=utf-8" },
                    "body": json.dumps({ "status": 1 })
                }
    except Exception as e:
        print(e)
        return {
            "statusCode": 200,
            "headers": { "content-type":"application/json; charset=utf-8" },
            "body": json.dumps({ "status": 0 })
        }

def LabelView(event,context):
    #print(event)
    try:
        input = loadData(event)
        LABEL = json.loads(json.loads(input['wallet'])["LABEL"])
        print(input)
        crop = format_coding_as_crop[LABEL[1]]
        user = input['user']
        first_name = user.split(' ')[0]
        variety = LABEL[5]
        delta = (dt.fromtimestamp(LABEL[4]) - dt.now()).days
        print('days untill harvest:', delta)
        coded = 0 if delta > 35 else 1 if delta > 0 else 2 if delta > -21 else 3

        label_view_texts = {
            'EN': f'{first_name} has a {crop} label. To create another label, type _new_. To add a record or grade the {crop} label, type _grade_ or the activity, such as _use pesticide_, _weed_ or _fertilize_.',
            'TN': f'{first_name} has a {crop} label. To create another label, type _new_. To add a record or grade the {crop} label, type _grade_ or the activity, such as _use pesticide_, _weed_ or _fertilize_.',
        }

        return {
            "statusCode": 200,
            "headers": { "content-type":"application/json; charset=utf-8" },
            "body": json.dumps({ "labels_string": label_view_texts[input['l']], 'grade': coded})
        }

    except Exception as e:
        label_view_texts = {
            'EN': 'Ues sorry we couldnt find any labels. Type _new_ to generate a new label',
            'TN': 'Ues sorry we couldnt find any labels. Type _new_ to generate a new label',
        }
        print(e)
        return {
            "statusCode": 200,
            "headers": { "content-type":"application/json; charset=utf-8" },
            "body": json.dumps({ "labels_string": label_view_texts[input['l']], "grade": 0 })
        }

def LabelResponse(event, context):
    from MODULES_imagery import GenerateCertificate
    from twilio.rest import Client

    account_sid = os.getenv("ACCOUNT_SID")
    auth_token = os.getenv("AUTH_TOKEN")
    TWILCLIENT = Client(account_sid, auth_token)
    print('event', event)
    # monitors for 15 min if tokens have been deposited to the users account, initiated after a deposit has been made.. 
    # if so it updates the user by sending a message with node data (yield, eos, etc.)
    # it then kills itself.
    time_left_untill_kill = 40000 # sleep time + 10 sec.
    phone = event['w_phone_user'] if 'w_phone_friend' in event else event['w_phone_friend']
    name = event['w_name_friend'] + 's' if 'w_name_friend' in event and event['w_name_friend'] else 'your'
    PK = event['pk']
    asset_id = event['asset_id']
    kill_method = False # add kill switch when a token change has been detected.

    while not kill_method: 
        remaining = context.get_remaining_time_in_millis()
        print('remaining', remaining)
        # output in miliseconds. 
        if remaining > time_left_untill_kill: # add 15 sec to run once more if almost finalized. 
            current_amnt = getAccountAssetInfo(PK,asset_id)[0]
            prev_amnt = event['asset_amnt']
            print('cur',current_amnt,'\n','prev',prev_amnt)
            start = time.process_time()
            if current_amnt > prev_amnt:
                try:
                    print('found increased balance of asset ', asset_id)
                    # find the note of the transaction that pytdeposited the asset
                    txs = CompletedSearchIndex(PK)
                    #txs = {'current-round': 25138745, 'next-token': 'MpZ_AQAAAAAJAAAA', 'transactions': [{'application-transaction': {'accounts': ['3ZF65HW7TDFXK4NFZKG7YAD4Y3VMTYFEK2JH6ZL577B2WBNDEYHUKLAAE4'], 'application-args': ['cmVzcG9uc2U=', 'AAAAAADWNgY=', 'AAAAAAAAADI=', 'AAAAAGPDQgA=', 'WzE2NjY5NzUxNDcsIDE0MDM4NTM0LCAxMDAxLCA1MCwgMTY3Mzc0MDgwMCwgIlBvbm5pIiwgMCwgInUiXQ=='], 'application-id': 119275134, 'foreign-apps': [], 'foreign-assets': [38909410, 14038534], 'global-state-schema': {'num-byte-slice': 0, 'num-uint': 0}, 'local-state-schema': {'num-byte-slice': 0, 'num-uint': 0}, 'on-completion': 'noop'}, 'close-rewards': 0, 'closing-amount': 0, 'confirmed-round': 25138742, 'fee': 1000, 'first-valid': 25138735, 'genesis-hash': 'SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=', 'genesis-id': 'testnet-v1.0', 'id': 'OCLXBBRJ3H22PH3GR64NBMOQQHM4BD5K4BD2LRR6MTUPVG2S6O3Q', 'inner-txns': [{'asset-transfer-transaction': {'amount': 50, 'asset-id': 14038534, 'close-amount': 0, 'receiver': '3ZF65HW7TDFXK4NFZKG7YAD4Y3VMTYFEK2JH6ZL577B2WBNDEYHUKLAAE4'}, 'close-rewards': 0, 'closing-amount': 0, 'confirmed-round': 25138742, 'fee': 1000, 'first-valid': 25138735, 'intra-round-offset': 1, 'last-valid': 25139735, 'note': 'WzE2NjY5NzUxMzMsIDE0MDM4NTM0LCAxMDAxLCA1MCwgMTY3Mzc0MDgwMCwgIlBvbm5pIiwgMCwgInUiXQ==', 'receiver-rewards': 0, 'round-time': 1666975150, 'sender': 'XCU2JGG2A243KDOF3F7ZJNNJRZJXIQ2XWUAUSL35A5F2RVCXBD22KDIKRU', 'sender-rewards': 0, 'tx-type': 'axfer'}], 'intra-round-offset': 1, 'last-valid': 25139735, 'local-state-delta': [{'address': '3ZF65HW7TDFXK4NFZKG7YAD4Y3VMTYFEK2JH6ZL577B2WBNDEYHUKLAAE4', 'delta': [{'key': 'cmVzcG9uc2U=', 'value': {'action': 2, 'uint': 2}}]}], 'note': 'WzE2NjY5NzUxNDcsIDE0MDM4NTM0LCAxMDAxLCA1MCwgMTY3Mzc0MDgwMCwgIlBvbm5pIiwgMCwgInUiXQ==', 'receiver-rewards': 0, 'round-time': 1666975150, 'sender': '7JZ7WMHBEGS32NW3QBR6T5BTWGEZ76JE7R4RFEKMSRC3EF2P4D6CRXFWGI', 'sender-rewards': 0, 'signature': {'sig': 'p5YNoGujP+WZuWammjeoafv0tacytD7YwgoUB7wwhmS1ZxtBE4qUm/jflpK93rgaK2QvwmxWzRS4zZnZYk/xDg=='}, 'tx-type': 'appl'}, {'application-transaction': {'accounts': ['3ZF65HW7TDFXK4NFZKG7YAD4Y3VMTYFEK2JH6ZL577B2WBNDEYHUKLAAE4'], 'application-args': ['cmVzcG9uc2U=', 'AAAAAADWNgY=', 'AAAAAAAAADI=', 'AAAAAGPDQgA=', 'WzE2NjY5NzUxMzMsIDE0MDM4NTM0LCAxMDAxLCA1MCwgMTY3Mzc0MDgwMCwgIlBvbm5pIiwgMCwgInUiXQ=='], 'application-id': 119275134, 'foreign-apps': [], 'foreign-assets': [38909410, 14038534], 'global-state-schema': {'num-byte-slice': 0, 'num-uint': 0}, 'local-state-schema': {'num-byte-slice': 0, 'num-uint': 0}, 'on-completion': 'noop'}, 'close-rewards': 0, 'closing-amount': 0, 'confirmed-round': 25138738, 'fee': 1000, 'first-valid': 25138735, 'genesis-hash': 'SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=', 'genesis-id': 'testnet-v1.0', 'id': 'YQS52NUBWAKL77OSJHJ2NJPSRP5UZCHEZX7VEISWARC5QK5ZTVTA', 'intra-round-offset': 9, 'last-valid': 25139735, 'local-state-delta': [{'address': '3ZF65HW7TDFXK4NFZKG7YAD4Y3VMTYFEK2JH6ZL577B2WBNDEYHUKLAAE4', 'delta': [{'key': 'YWRkcmVzc2Vz', 'value': {'action': 1, 'bytes': '+nP7MOEhpb0224Bj6fQzsYmf+ST8eRKRTJRFshdP4Pw=', 'uint': 0}}, {'key': 'Y3Q=', 'value': {'action': 1, 'bytes': 'AAAAAADWNgY=', 'uint': 0}}, {'key': 'ZGVzY3JpcHRpb24=', 'value': {'action': 1, 'bytes': 'WzE2NjY5NzUxMzMsIDE0MDM4NTM0LCAxMDAxLCA1MCwgMTY3Mzc0MDgwMCwgIlBvbm5pIiwgMCwgInUiXQ==', 'uint': 0}}, {'key': 'ZW9z', 'value': {'action': 1, 'bytes': 'AAAAAGPDQgA=', 'uint': 0}}, {'key': 'cmVzcG9uc2U=', 'value': {'action': 2, 'uint': 1}}, {'key': 'eWxk', 'value': {'action': 1, 'bytes': 'AAAAAAAAADI=', 'uint': 0}}]}], 'note': 'WzE2NjY5NzUxMzMsIDE0MDM4NTM0LCAxMDAxLCA1MCwgMTY3Mzc0MDgwMCwgIlBvbm5pIiwgMCwgInUiXQ==', 'receiver-rewards': 0, 'round-time': 1666975136, 'sender': '7JZ7WMHBEGS32NW3QBR6T5BTWGEZ76JE7R4RFEKMSRC3EF2P4D6CRXFWGI', 'sender-rewards': 0, 'signature': {'sig': '2EJRxDdrD/iox6NFbnLPZO8IETUH+EYrxtUYzeeDEob2HdZ9Vb/NlfnZiOCCXEvtU0KAD7QuQmi/bzxjCx/mDw=='}, 'tx-type': 'appl'}]}
                    for tx in txs['transactions']:
                        if 'note' in tx and 'application-transaction' in tx:
                            # read note
                            decodedNote = json.loads(b64decode(tx['note']).decode("utf-8"))
                            ct = format_coding_as_crop[decodedNote[1]]
                            yld = decodedNote[3]
                            date = dt.fromtimestamp(decodedNote[4]).strftime("%d %B, %Y")
                            print(int(decodedNote[4]) - dt.now().timestamp())
                            far_from_harvest = True if int(decodedNote[4]) - dt.now().timestamp() > 1814400 else False
                            print(ct,yld,date,far_from_harvest)
                            id = tx['id']
                            break # take note that we return the first note found (prob the one we need..)
                        
                    # generate the certificate
                    txn_url = 'https://testnet.algoexplorer.io/tx/{}'.format(id)
                    print(current_amnt,prev_amnt,date,event['variety'],txn_url,event['prop_url'])
                    amnt = current_amnt - prev_amnt
                    print('amnt', amnt)
                    print('input for gencert', type(ct),type(amnt),type(date),type(event['variety']),type(txn_url),type(event['prop_url']),type(event['pk']))
                    url = GenerateCertificate(ct,amnt,date,event['variety'],txn_url,event['prop_url'],event['pk'])
                    print('url', url)
                    # update user on the responds
                    kill_method = True
                    TWILCLIENT.messages.create(
                        to=phone, 
                        from_="whatsapp:+13478481380",
                        body="Congratulations with {} new {} label. Type _loan_ or _insurance_ to use the label as contract guarantee. Type _info about labels_ to learn more about opportunities and risks.".format(name,ct.lower()),
                        media_url=url
                    )
                    return
                except Exception as e:
                    print('something has gone wrong.')
                    print(e)
                    # update user on the responds
                    kill_method = True # force lambda to close..
                    TWILCLIENT.messages.create(
                        to=phone, 
                        from_="whatsapp:+13478481380",
                        body="Hi. We are sorry to say that something has gone wrong. This is probably from our side. Our apologies. Please try again."
                    )
                    return
            else:
                end = time.process_time()
                diff = end - start
                print('time to sleep:', 60 - diff)
                time.sleep(30 - diff)
        else:
            loop = 0
            # TIME IS UP AND WE HAVE NOT RECEIVED ANY LABEL.
            # give feedback about possible reasons of failure..
            ct = format_coding_as_crop[event['asset_id']]
            far_from_harvest = True if int(dt.strptime(event['date'],"%d%B%Y").strftime('%s')) - dt.now().timestamp() > 1814400 else False
            reason_of_failure = 'As you are early in the season, try again in a few weeks.' if far_from_harvest else 'This could be due to incorrect property borders. Ask your FPO for help.'
            # update user on the responds
            if loop < 1:
                TWILCLIENT.messages.create(
                    to=phone, 
                    from_="whatsapp:+13478481380",
                    body="Hi. Unfortunately we have found no evidence of a {} cultivation in the fields of {}. {}".format(ct.lower(),name[:-1],reason_of_failure)
                )
            print('return None. End invocation...')
            return


#e = {'app': 109074583, 'pk': '3ZF65HW7TDFXK4NFZKG7YAD4Y3VMTYFEK2JH6ZL577B2WBNDEYHUKLAAE4', 'phoneNumber': '+31627257049'}
e = {'resource': '/asset_create', 'path': '/asset_create', 'httpMethod': 'POST', 'headers': {'Accept': '*/*', 'CloudFront-Forwarded-Proto': 'https', 'CloudFront-Is-Desktop-Viewer': 'true', 'CloudFront-Is-Mobile-Viewer': 'false', 'CloudFront-Is-SmartTV-Viewer': 'false', 'CloudFront-Is-Tablet-Viewer': 'false', 'CloudFront-Viewer-ASN': '14618', 'CloudFront-Viewer-Country': 'US', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'Host': 'qieasxwyji.execute-api.ap-south-1.amazonaws.com', 'I-Twilio-Idempotency-Token': 'ac640058-ad37-4c69-82b5-109ade6309b2', 'User-Agent': 'TwilioProxy/1.1', 'Via': '1.1 35306eb26a83034d2e583f34ce922c08.cloudfront.net (CloudFront)', 'X-Amz-Cf-Id': 'MH86rEY0f8jg1RD-OcoW3p63eVJ_cPug5ndofo1ymsdrBF3u9RiIYA==', 'X-Amzn-Trace-Id': 'Root=1-63fba562-2e102fd958dbfc0e705cccaa', 'X-Forwarded-For': '44.211.206.186, 15.158.41.23', 'X-Forwarded-Port': '443', 'X-Forwarded-Proto': 'https', 'X-Home-Region': 'us1', 'X-Twilio-Signature': '6kSc6AC8BzmJLGD3zOnoh7+jkyc='}, 'multiValueHeaders': {'Accept': ['*/*'], 'CloudFront-Forwarded-Proto': ['https'], 'CloudFront-Is-Desktop-Viewer': ['true'], 'CloudFront-Is-Mobile-Viewer': ['false'], 'CloudFront-Is-SmartTV-Viewer': ['false'], 'CloudFront-Is-Tablet-Viewer': ['false'], 'CloudFront-Viewer-ASN': ['14618'], 'CloudFront-Viewer-Country': ['US'], 'Content-Type': ['application/x-www-form-urlencoded; charset=UTF-8'], 'Host': ['qieasxwyji.execute-api.ap-south-1.amazonaws.com'], 'I-Twilio-Idempotency-Token': ['ac640058-ad37-4c69-82b5-109ade6309b2'], 'User-Agent': ['TwilioProxy/1.1'], 'Via': ['1.1 35306eb26a83034d2e583f34ce922c08.cloudfront.net (CloudFront)'], 'X-Amz-Cf-Id': ['MH86rEY0f8jg1RD-OcoW3p63eVJ_cPug5ndofo1ymsdrBF3u9RiIYA=='], 'X-Amzn-Trace-Id': ['Root=1-63fba562-2e102fd958dbfc0e705cccaa'], 'X-Forwarded-For': ['44.211.206.186, 15.158.41.23'], 'X-Forwarded-Port': ['443'], 'X-Forwarded-Proto': ['https'], 'X-Home-Region': ['us1'], 'X-Twilio-Signature': ['6kSc6AC8BzmJLGD3zOnoh7+jkyc=']}, 'queryStringParameters': None, 'multiValueQueryStringParameters': None, 'pathParameters': None, 'stageVariables': None, 'requestContext': {'resourceId': 'ftzc6k', 'resourcePath': '/asset_create', 'httpMethod': 'POST', 'extendedRequestId': 'A9bHYF2YBcwFaUw=', 'requestTime': '26/Feb/2023:18:30:58 +0000', 'path': '/stage/asset_create', 'accountId': '867185477215', 'protocol': 'HTTP/1.1', 'stage': 'stage', 'domainPrefix': 'qieasxwyji', 'requestTimeEpoch': 1677436258191, 'requestId': 'b2c5e100-f4ff-4b6a-8033-f13b0da27e38', 'identity': {'cognitoIdentityPoolId': None, 'accountId': None, 'cognitoIdentityId': None, 'caller': None, 'sourceIp': '44.211.206.186', 'principalOrgId': None, 'accessKey': None, 'cognitoAuthenticationType': None, 'cognitoAuthenticationProvider': None, 'userArn': None, 'userAgent': 'TwilioProxy/1.1', 'user': None}, 'domainName': 'qieasxwyji.execute-api.ap-south-1.amazonaws.com', 'apiId': 'qieasxwyji'}, 'body': 'names=WestGrid-1%24EastGrid-1%24EastGrid-2&pin=7025&size=1&org=MullaiFPO&phone=%2B919840480142&phoneNumber=%2B31627257049&count=OFFLINE&pk=LKLE35MKLUVJVYFLBRTFQH33VB6N3E6Q7TANB2XQ5HNWIKL4PXXAUMHF24&list_responds=continue&l=English&points=12.5426483%2C79.3215438%2412.5423852%2C79.3223328%2412.5422194%2C79.3221211&status=C', 'isBase64Encoded': False}

PropertyAssetCreate(e,'')
