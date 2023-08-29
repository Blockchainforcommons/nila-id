import json
import re
import urllib
import difflib
import boto3
import base64
import binascii
from datetime import datetime as dt
from boto3.dynamodb.conditions import Key
from algosdk.v2client import algod
from algosdk import encoding
from Cryptodome.Cipher import AES
from connect import getLabelTxns

# Setup HTTP client w/guest key provided by PureStake
algod_token = 'dFrf6mnFriaPIAzsbB70g3qZlWuXGeGO6z2nxCRw'
algod_address = 'https://testnet-algorand.api.purestake.io/ps2'
purestake_token = {'X-Api-key': algod_token}
algodclient = algod.AlgodClient(algod_token, algod_address, headers=purestake_token)
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
MEMBERS = dynamodb.Table('Member-q7dz4tkcefhkdhn4snv65cvkru-stage')
AESTABLE = dynamodb.Table('AES-stage')

## rank responses
PROP = ['register','prop','property','fields','borders','field','land','cadastreal','bordering','0']
SCORE = ['score', 'score card', 'performance','1']
CREDIT = ['loan','loans','credit','crop loan','borrow','borrowing','finance','futures','2']
SUPPLY = ['supply','sale','sell','market','store','deliver','storage','3']
LABEL = ['crop label','planting','plant','cultivation','label','labels','market','registration','storage','warehouse','receipts','receipt','ticket','3']
SOIL = ['soil','properties','nutrients','phosporous','nitrate','ph','salt','4']
CERTIFICATION = [ 'organic', 'traditional', 'certification','cert','5','certificate','certificates']
PRICING = ['prices', 'price', 'mandi','pricing','6']
MUTUAL = ['mutual', 'insurance', 'hedge','ins','mut','7']
CARBON = ['carbon','credit','credits','sustainable','erosion','8']
GRADE = ['9','grade']
WEATHER = ['10','weather']
FIELDVISIT = ['11','visit']
info = ['info','inf','tell','chitta','chita','inform','explain','know','more','menu']
greetings = ['hi','hello','hey','yo','hey','hi!','morning','afternoon','evening']
confirm = ['ok','sure','okay','fine']
pay = ['pay','transfer','send']
deposit = ['CHT','deposit','depos']
help = ['help','helpdesk','assistence','person','human','assist','help?']
WALLET = ['wallet','account','balance','amount']
appreciation = ['thank','thanks','praise','gratitude','appreciated','grateful']
question = ['when','what','how']
rewards = ['rewards','reward','bonus','gifts','gift','rwards','rewadrs']
close = ['exit','close','end','stop','finish','fin']
offline = ['offline','off','no internet','offline mode']
ADVICE = ['advice','suggestions','suggestion','solution','solutions','potential']
PROFILE = ['profile','setting','settings']
SUBSIDY = ['subsidy','government']
FRIEND = ['friend','neighbor','friends']

def trans_mispel(response):
    PADDY = ['paddy','padd','pady','pad','paddt','paddr']
    GROUNDNUT = ['groundnut','grndnut','grnut','grnt','grounnt']
    SUGARCANE = ['sugarcane','sugar','cane','sgrcane']
    BANANA = ['banana','banan','banna','bnana']
    MILLETS = ['millets','millts','millet','milts']
    # format the response, remove punctuations 
    response = re.sub(r'[^\w\s]', '', response)
    if any(x == response for x in PADDY):
        return 'PADDY'
    if any(x == response for x in GROUNDNUT):
        return 'GROUNDNUT'
    if any(x == response for x in SUGARCANE):
        return 'SUGARCANE'
    if any(x == response for x in BANANA):
        return 'BANANA'
    if any(x == response for x in MILLETS):
        return 'MILLETS'
    else:
        return ''

def Format_numeric_date(d):
    JAN = ['january','jan']
    FEB = ['february','feb']
    MAR = ['march','mar','mrc']
    APR = ['april','apr']
    MAY = ['may','may']
    JUN = ['june','jun']
    JUL = ['july','jul']
    AUG = ['august','aug']
    SEP = ['september','sep','sept']
    OCT = ['october','oct']
    NOV = ['november','nov']
    DEC = ['december','dec']
    # format the response, remove punctuations 
    response = re.sub(r'[^\w\s]', '', d.lower())
    if any(x == response for x in JAN):
        return 1
    if any(x == response for x in FEB):
        return 2
    if any(x == response for x in MAR):
        return 3
    if any(x == response for x in APR):
        return 4
    if any(x == response for x in MAY):
        return 5
    if any(x == response for x in JUN):
        return 6
    if any(x == response for x in JUL):
        return 7
    if any(x == response for x in AUG):
        return 8
    if any(x == response for x in SEP):
        return 9
    if any(x == response for x in OCT):
        return 10
    if any(x == response for x in NOV):
        return 11
    if any(x == response for x in DEC):
        return 12
    else:
        return 0

format_coding_as_crop = {
    14038534:'Paddy',
    14038537:'Groundnut',
    22179923:'Sugarcane',
    22181339:'Banana',
    22180015:'Millets',
}

format_crop_as_coding = {
    'PADDY':14038534,
    'GROUNDNUT':14038537,
    'SUGARCANE':22179923,
    'BANANA':22181339,
    'MILLETS':22180015,
}

def format_responds(response):
    # format the response, remove punctuations 
    response = re.sub(r'[^\w\s]', '', response)
    # SERVICES THAT REQUIRE A SUBFLOW
    if any(x == response for x in PROP):
        return 'PROP'
    if any(x == response for x in SCORE):
        return 'SCORE'
    if any(x == response for x in CREDIT):
        return 'CREDIT'
    if any(x == response for x in SUPPLY):
        return 'SUPPLY'
    if any(x == response for x in LABEL):
        return 'LABEL'
    if any(x == response for x in SOIL):
        return 'SOIL'
    if any(x == response for x in CERTIFICATION):
        return 'CERTIFICATION'
    if any(x == response for x in MUTUAL):
        return 'MUTUAL'
    if any(x == response for x in CARBON):
        return 'CARBON'
    if any(x == response for x in GRADE):
        return 'GRADE'
    if any(x == response for x in FIELDVISIT):
        return 'FIELDVISIT'
    if any(x == response for x in greetings):
        return 'greetings'
    if any(x == response for x in ADVICE):
        return 'ADVICE'
    if any(x == response for x in SUBSIDY):
        return 'SUBSIDY'
    if any(x == response for x in FRIEND):
        return 'FRIEND'
    # SERVICES WITH A SINGLE MESSAGE RESPONSE
    if any(x == response for x in PROFILE):
        return 'PROFILE'
    if any(x == response for x in WALLET):
        return 'WALLET'
    if any(x == response for x in PRICING):
        return 'pricing'
    if any(x == response for x in info):
        return 'info'
    if any(x == response for x in help):
        return 'help'
    if any(x == response for x in WEATHER):
        return 'weather'
    if any(x == response for x in rewards):
        return 'REWARDS'
    if any(x == response for x in appreciation):
        return 'appreciation'
    if any(x == response for x in question):
        return 'question'
    if any(x == response for x in close):
        return 'close'
    if any(x == response for x in confirm):
        return 'confirm'
    if any(x == response for x in offline):
        return 'offline'
    if any(x == response for x in pay):  # pay and deposit direct to same subflow, which then seperates based on service name
        return 'PAY'
    if any(x == response for x in deposit): # pay and deposit direct to same subflow, which then seperates based on service name
        return 'DEPOSIT'
    else:
        return ''

def decrypt_AES_GCM(encryptedMsg, secretKey):  
    (ciphertext, nonce, authTag) = encryptedMsg   
    aesCipher = AES.new(secretKey, AES.MODE_GCM, nonce)    
    plaintext = aesCipher.decrypt_and_verify(ciphertext, authTag)    
    return plaintext

def decypher_AES(input,app_id,asset_ids):
    phone = input['phone'][9:] if input['phone'].startswith('whatsapp') else input['phone']
    secretkey = int(input['pin']) * int(phone[1:])
    # find the AES keys
    keys = AESTABLE.query(KeyConditionExpression=Key("phone").eq(phone), ProjectionExpression= "phone, SK_cipher, K_cipher")
    print('keys', keys)
    # get passcode from PIN and AES K Keys
    encryptedMsg = tuple([bytes(c) for c in keys['Items'][0]['K_cipher']])
    binary_secretkey = binascii.hexlify(bytes(str(secretkey)[:12], 'ascii'))
    passcode = binascii.hexlify(decrypt_AES_GCM(encryptedMsg, binary_secretkey))

    # get Secret key from passcode and AES SK Keys
    encryptedMsg_SK = tuple([bytes(c) for c in keys['Items'][0]['SK_cipher']])
    SK = decrypt_AES_GCM(encryptedMsg_SK, passcode)
    PK = encoding.encode_address(base64.b64decode(SK)[32 :])

    # check if the users is opted-in to the asset requested.
    algo,cht,property,scorecard,label,inr,assets,apps = checkBalanceForStatus(PK,True) # pk, advanced toggle (incl opted-in apps)

    # return a list of apps or assets to optin to
    OPT_app = [] if any([app in apps for app in app_id]) else app_id
    OPT_asset = [] if not asset_ids or any([asset in [v[0] for k,v in assets.items()] for asset in asset_ids]) else asset_ids #assets shape is eg. {'Paddy': [14038534, 800]}
    return algo,SK,PK,OPT_app,OPT_asset,property,assets

def loadData(event):
    # split attributes
    body = [x.split('=') for x in  urllib.parse.unquote(event['body']).split('&')]
    obj = {}
    for param in body:  
        obj[param[0]] = param[1]
    return obj
    
def checkBalanceForStatus(pk,advanced):
    '''
        to speed up the method, some calls in the chatbot have advanced = False, which returns apps = []
        however to request assets, we need to know if the user has to still opt-in. Therefore advanced class is required.

    '''
    # amount of Algo:
    account_info = algodclient.account_info(pk)
    algo = account_info.get('amount')/1000
    cht = [aid['amount'] for aid in account_info['assets'] if aid['asset-id'] == 38909410]
    inr = cht[0] * 100 if len(cht) > 0 else 0
    commodities = [aid['amount'] for aid in account_info['assets'] if aid['asset-id'] != 38909410]
    assets = {}
    apps = {}
    print('collect asset info')
    for com in account_info['assets']:
        info = algodclient.asset_info(com['asset-id'])
        assets = {**assets,**{ info['params']['name']: [com['asset-id'],com['amount']] }}
    print('collect app info')
    if advanced:
        for app in account_info['apps-local-state']:
            info = algodclient.application_info(app['id'])
            apps = {**apps,**{ info['id']: info['params']['creator'] }}  # MISSING NAME OF APPLICATION in application
    print('collect property info')
    property = assets['chitta-property'] if 'chitta-property' in assets else False
    # append prop url to the list
    print('prop params', algodclient.asset_info(property[0])['params'])
    prop_url = algodclient.asset_info(property[0])['params']['url'] if property else ''
    property.append(prop_url) if property else None
    scorecard = assets['chitta-farm-master'] if 'chitta-farm-master' in assets else False # CHECK IF THE SCORE CARD IS UP-TO-DATE
    label = getLabelTxns(pk) # CHECK IS THE REGISTERED EOS DATE IS IN THE FUTURE..
    cht = assets['Chits'] if 'Chits' in assets else [38909410,0]
    return algo,cht,property,scorecard,label,inr,assets,apps if advanced else []

def Status(pk): 
    try:
        if pk != '0':
            #print('pk', pk, 'phonenumber', phonenumber, 'f', f)
            algo,cht,property,scorecard,label,inr,assets,apps = checkBalanceForStatus(pk,False) # pk, advanced untoggled (excl opted-in apps)
            assets.pop('Chits') if 'Chits' in assets else None
            asset_string = ','.join([' - {} : {}'.format(k,v[1]) for k,v in assets.items()])
            app_string = ',' #.join(['{}'.format(k) for k,v in apps.items()]) #apps SKIP APPS TO MAKE THIS CALL FASTER..
            
            #get the pk and phone from the event, collect and return the available status data
            #* total balance
            #* available commodities ? how ? 
            #* active applications, e.g. insurance, credit, futures, market sale, etc.
            return { 
                'cht':cht[1],
                'algo':algo,
                'PROP':property,
                'SCORE':scorecard,
                'LABEL':label,
                'inr':inr,
                'asset_string': asset_string if asset_string != ',' else 'None',
                'app_string':app_string if app_string != ',' else 'None',
                'pk': pk
            }
        else:
            print('this user does not have a wallet')
            return     

    except Exception as e: 
        print(e)
        print('------------------------')
        return "Error"

def FORMAT_CROP(inp):
    # translate and/or check for misspeling.
    crop = trans_mispel(inp)
    # coded crop type
    coded = format_crop_as_coding[crop]
    return coded,crop 

def FORMAT_DATE(inp):
    print('form date', inp)
    # output month as number
    mm = str(inp) if inp.isnumeric() else Format_numeric_date(inp)
    nn = int(dt.now().strftime("%m"))
    # guess year
    yy = int(dt.now().strftime("%Y")) - 1 if mm - 9 > nn else int(dt.now().strftime("%Y")) + 1 if nn - 9 > mm else int(dt.now().strftime("%Y"))
    # set month as datetime
    d = dt.strptime('15' + str(mm) + str(yy), "%d%m%Y")
    delta = (d - dt.now()).days
    # codex
    #    0 = eos in future, no grading
    #    1 = eos near future, grading
    #    2 = eos near past, grading
    #    3 = eos extended past, no grading, close
    coded = 0 if delta > 35 else 1 if delta > 0 else 2 if delta > -21 else 3
    return d,coded

def Find_match(a,b,phone,name):
    if any([ a.lower() == c for c in ['myself','me','i','my self','my','mi self','mi'] + name.split(' ')]): # add notations of self or name
        return { 'name': 'you', 'phone': phone, 'self': True},100
    else:
        # this algorithm will compare each character in response and friends list, returning the most similar friend in the list.
        index_of_most_likely_response = 0
        similarity = 0
        for i,sample in enumerate(b):
            seq = difflib.SequenceMatcher(None,a.lower(),sample['name'].lower())
            d = seq.ratio()*100
            if d > similarity:
                similarity = d
                index_of_most_likely_response = i
        return b[index_of_most_likely_response],similarity # we pass the highest similarity with the index of the friend

def Find_numerical_match(a,b,phone,name):
    if int(a) == 1:
        return { 'name': 'you', 'phone': phone, 'self': True} 
    else:
        return json.loads(a)[int(b) - 2]

def LoadWallet(resp,pk,phone):
    if resp['user']['phone']:
        # GET friend data from back-end
        f_pk = MEMBERS.query(KeyConditionExpression=Key("phoneNumber").eq(resp['user']['phone']), ProjectionExpression="pk")['Items'][0]['pk']
        # use friends pk to load wallet
        wallet = Status(f_pk)
        print('WALLET', wallet)
    else:
        # use user pk to load wallet
        wallet = Status(pk)
        print('WALLET', wallet)
    return wallet

def ClassifyResponse(resp,f_list,phone,name):
    # split the response in words
    user = { 'name': '', 'phone': ''}
    cat = []
    adit = ''
    output = ''
    for word in resp.split(' '):
        if word.isnumeric():
            # WE ASSUME NUMBER IS FOR SERVICE NOTATION, !this could confuse, as maybe user remembers number of friend..
            output = format_responds(word) if not cat else cat # got ya service
            # add each word class to list
            cat.append(output)
        elif format_responds(word):
            output = format_responds(word) # got ya service
            # add each word class to list
            cat.append(output)
            # set service = output, if not INFO, or info is already put.
        elif word.lower() in ['add','list','update','remove','my','new']:
            adit = word
        else:
            u,match_rate = Find_match(word,f_list,phone,name) if f_list else (0,0)
            if match_rate > 40:
                user = u
    # recheck responses with more then 1 class
    cat = ['unclear'] if len(cat) < 1 else cat

    print(' output:', cat, 'additive:', adit )
    return {'class': cat, 'user': user, 'additive': adit}