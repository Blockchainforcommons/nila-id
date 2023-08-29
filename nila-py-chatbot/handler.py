import json
from widgets import trigger, SplitBasedOn, SendWaitForReply, MakeHttpRequest, SendMessage, SetVariables, SubFlow, Send_Reply_Split
from commit import validate,commit,packaging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

VERSION = 'dev_0.0.0'
conversation = 'https://7l3sx25tf9.execute-api.ap-south-1.amazonaws.com/stage/conversation'
generate_account = 'https://7l3sx25tf9.execute-api.ap-south-1.amazonaws.com/stage/gen_account'
Contractguarantee = 'https://7l3sx25tf9.execute-api.ap-south-1.amazonaws.com/stage/credit_guarantee'

VerifyProof = 'https://7l3sx25tf9.execute-api.ap-south-1.amazonaws.com/stage/credit_guarantee' # !!!!!!!!!!!! update
IssueStorage = 'https://bf8b-2a02-a46a-7ff7-1-18d6-163e-578c-96e9.ngrok-free.app/IssueStorage'
ProofStorage = 'https://bf8b-2a02-a46a-7ff7-1-18d6-163e-578c-96e9.ngrok-free.app/ProofStorage'
'''
    This flow is limited for demonstration purposes only.
    It presents a simple flow to get a loan (request,payback) and the wallet operability (pay,deposit,withdrawal), including registration.

'''
def texts(widget,language):
    key = widget + language
    return {
        'noUser':'Hello farmer. I am _Nila_. Thank you for reaching out. Before we can assist you we need to register your land.\n\nType *Yes* to start.\n_You need to share the locations of your fields. If you are not on your property, or have already registered. Please try again later._\n\nType *Info* to learn more about me.\n\nType *Sponsor* to register as a supply and finance partner.\n_Support your local farmers by vouching credit and give supply chain access. Sponsors will be vetted before giving access_',     
        'info': 'Sure. My name is Nila. I can assist you in your marketing and finance needs as a farmer. We give vouched loans and publish your crops on several marketplaces worldwide. As we know markets. We help you grow what is in demand in a sustainable way.\n\nAfter you registered you get:\n\n* access to our crop and investment loans.\n* offerings of your crops on our global marketplace using secure digital receipts (export documentation).\n* get a digital wallet to pay via UPI payments.\n* assistence through our multilanguage Chatbot (Tamil,Kannada,Telugu and English).',
        ## has property
        'InitRegistration':'Yes,yes,have,I have,indeed,sure,true',
        'InfoRegistration':'Info,info,information,inf,in,infoo',

        ## initial name and language
        'name': 'Great. Please tell me your full name.',
        'language': 'Ok. What language shall we speak {{widgets.setName.inbound.Body}}? I speak English, Tamil, Kannada or Telugu.',

        ## SPONSORSHIPS
        'agree_EN':'agree,yes,Yes,YES,Agree,Ok,agreed,read,complete,accept,accepted,confirm',
        'agree_TN':'agree,yes,Yes,YES,Agree,Ok,agreed,read,complete,accept,accepted,confirm',
        'deny_EN':'no,not agreed,No,NO',
        'deny_TN':'no,not agreed,No,NO',
        'sponsorship_conditions_EN':'These are the conditions upon acceptance as a sponsor:\n\n* As a sponsor you guarantee the full reimbursement of Rs. {{flow.data.amount}}/- plus interest in case {{flow.data.name}} has relinquished on his promise, _the latest within 6 weeks of the final payment date._\n\n* As a sponsor, you have the ability to extend the period, if a warehouse receipt of the full yield is deposited to the contract.\n\n** You will receive a {{flow.data.rate}}% reward for your guarantee*. Instantly transfered to your wallet once the debtor has fully repaid the loan.',
        'sponsorship_acceptance_EN':'Please indicate the intend to sponsor {{flow.data.name}}?',

        ## PURCHASE INTEREST
        'set_amount_EN':'Hi. Thank you for using Nila. Please confirm the amount of {{flow.data.variety}} {{flow.data.crop}} you wish to buy from {{flow.data.name}}?',
        'set_amount_TN':'Hi. Thank you for using Nila. Please confirm the amount of {{flow.data.variety}} {{flow.data.crop}} you wish to buy from {{flow.data.name}}?',

        'proof_claim_EN':'Ok. Thank you. We will now proof the claim made by {{flow.data.name}}, and the amount available. Please wait…',
        'proof_claim_TN':'Ok. Thank you. We will now proof the claim made by {{flow.data.name}}, and the amount available. Please wait…',

        'http_results_EN':'{{widgets.http_results_EN.parsed.Message}}',
        'http_results_TN':'{{widgets.http_results_TN.parsed.Message}}',

        'new_proof_features_EN':'Soon Nila can verify the origin, grade, and farm methods of {{flow.data.name}}. We will be able to verify if the supply meets export standards.',
        'new_proof_features_TN':'Soon Nila can verify the origin, grade, and farm methods of {{flow.data.name}}. We will be able to verify if the supply meets export standards.',

        'confirm_interest_EN': 'Please confirm you would like to buy {{widgets.http_results_EN.parsed.amount}} quintal {{widgets.http_results_EN.parsed.crop}} for {{widgets.http_results_EN.parsed.marketprice}}/- inr from {{widgets.http_results_EN.parsed.name}}',
        'confirm_interest_TN': 'Please confirm you would like to buy {{widgets.http_results_TN.parsed.amount}} quintal {{widgets.http_results_TN.parsed.crop}} for {{widgets.http_results_TN.parsed.marketprice}}/- inr from {{widgets.http_results_TN.parsed.name}}',
        
        'purchase_accept_EN':'Great. Please wait for the buyer confirmation.',        
        'purchase_accept_TN':'Great. Please wait for the buyer confirmation.',

        'purchase_deny_EN':'Sure. no problem. Thank you for trying Nila',
        'purchase_deny_TN':'Sure. no problem. Thank you for trying Nila',

        'receive_creds_EN':'Congratulations. {{flow.data.businessName}} has created your {{flow.data.ct}} storage certificates.\n\n* Quantity: {{flow.data.quantity}} quintal\n* Grade: {{flow.data.grade}}\n\nType *confirm* to generate the proof and sell your produce.',
        'receive_creds_TN':'Congratulations. {{flow.data.businessName}} has created your {{flow.data.ct}} storage certificates.\n\n* Quantity: {{flow.data.quantity}} quintal\n* Grade: {{flow.data.grade}}\n\nType *confirm* to generate the proof and sell your produce.',

        ## STORE CROPS
        'store_credentials_EN':'Good day, Please create the storage credentials for {{widgets.getAccount.parsed.user_name}}.',
        'store_credentials_TN':'Good day, Please create the storage credentials for {{widgets.getAccount.parsed.user_name}}.',

        'store_amount_EN':'What amount (in quintal) of {{widgets.getAccount.parsed.ct}} has been delivered?',
        'store_amount_TN':'What amount (in quintal) of {{widgets.getAccount.parsed.ct}} has been delivered?',

        'store_grade_EN':'What is the grade of the {{widgets.getAccount.parsed.ct}}?',
        'store_grade_TN':'What is the grade of the {{widgets.getAccount.parsed.ct}}?',

        'store_confirm_EN':'Thank you. The amount of {{widgets.getAccount.parsed.ct}} will be added to your storage account. Please type confirm to issue the credentials and update the account.',
        'store_confirm_TN':'Thank you. The amount of {{widgets.getAccount.parsed.ct}} will be added to your storage account. Please type confirm to issue the credentials and update the account.',

        'store_success_EN':'Done. Your storage audit trail tree has been updated with the produce of {{widgets.getAccount.parsed.user_name}}. Ask if the new sales code has been received.',
        'store_success_TN':'Done. Your storage audit trail tree has been updated with the produce of {{widgets.getAccount.parsed.user_name}}. Ask if the new sales code has been received.',

        'store_deny_EN':'Unfortunately. Scan the QR again to retry to register the newly delivered produce.',
        'store_deny_TN':'Unfortunately. Scan the QR again to retry to register the newly delivered produce.',

        'send_proof_EN': 'Done. Upload or share this qr code to your favorite market platform, or local traders, and proof your products is savely stored at {{flow.data.businessName}}.',
        'send_proof_TN': 'Done. Upload or share this qr code to your favorite market platform, or local traders, and proof your products is savely stored at {{flow.data.businessName}}.',
        
        ## EXIT
        'exit_EN':'Ok',
        'exit_TN':'Ok',
        }[key]

def Guarantee(l):
    guarantee_attr = [
        {'key':'phone', 'value': '{{flow.data.sponsor_phone}}'},
        {'key':'pin', 'value': '{{{}widgets.{}.inbound.Body {}}}'.format('{','vouch_accept' + l,'}')},
    ]

    # split acceptance
    split_accept_var = '{{{}widgets.{}.inbound.Body | downcase {}}}'.format('{','sponsorship_acceptance' + l,'}') 
    split_invite_var = '{{{}widgets.{}.inbound.Body | downcase {}}}'.format('{','sponsor_invite' + l,'}') 
    split_accept = [
        { 'next': 'vouch_accept' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('agree',l), 'argument': split_accept_var},
        { 'next': 'vouch_deny' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('deny',l), 'argument': split_accept_var},
        ]  

    # SUBFLOW TO SPONSOR (ENGLISH ONLY) (incoming request)
    sponsor_invite,*x = Send_Reply_Split(l,'sponsor_invite' + l,'sponsorship_conditions' + l,'sponsorship_conditions' + l,'exit' + l,'{{flow.data.conversation}}',[],split_invite_var,5,'{{flow.data.url}}'),
    sponsorship_conditions,*x = Send_Reply_Split(l,'sponsorship_conditions' + l,'sponsorship_acceptance' + l,'sponsorship_acceptance' + l,'exit' + l,texts('sponsorship_conditions','_EN'),[],split_invite_var,5,''),
    sponsorship_acceptance,*x = Send_Reply_Split(l,'sponsorship_acceptance' + l,'','','exit' + l,texts('sponsorship_acceptance','_EN'),split_accept,split_accept_var,1800,''), # accept or deny button

    # accept sponsorship
    vouch_accept,*x = Send_Reply_Split(l,'vouch_accept' + l,'error','error','guarantee' + l,'Great. Please sign the guarantee with your 4 digit PIN.',[],'{{{}widgets.{}.inbound.Body{}}}'.format('{','vouch_accept' + l,'}'),360,''),
    guarantee = MakeHttpRequest('guarantee' + l,'guarantee_success' + l,'error','POST',guarantee_attr,Contractguarantee),
    guarantee_success = SendMessage('guarantee_success' + l,'','','Ok. All done. We will inform you about the process.',''), # deny sponsorship
    vouch_deny = SendMessage('vouch_deny' + l,'','','Sure no problem. Thank you for your efforts.',''),

    exit = SendMessage('exit' + l,'','',texts('exit',l),''), # exit to parent flow and start again
    change_user = SendMessage('set_user' + l,'','',texts('exit',l),''), # exit to parent flow and start again

    return *sponsor_invite,*sponsorship_conditions,*sponsorship_acceptance,*vouch_accept,*guarantee,*guarantee_success,*vouch_deny,*exit,*change_user

def Purchase(l):
    '''
    Trader has seen the QR and wish to buy/proof the goods.
    QR metadata: [300,phoneNmb,name,crop,variety]
    '''
    proof_attr = [
        {'key':'phone', 'value': '{{flow.data.sponsor_phone}}'}, # attributes coming from QR scan!
    ]

    split_confirm_var = '{{{}widgets.{}.inbound.Body | downcase {}}}'.format('{','confirm_interest' + l,'}') 
    split_confirm = [
        { 'next': 'purchase_accept' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('agree',l), 'argument': split_confirm_var},
        { 'next': 'purchase_deny' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('deny',l), 'argument': split_confirm_var},
        ]  

    set_amount = SendWaitForReply('purchase_set_amount' + l,'proof_claim' + l,'error','error',texts('set_amount',l),600),
    wait_proof = SendMessage('proof_claim' + l,'http_proof' + l,'',texts('proof_claim',l),''),
    http_proof = MakeHttpRequest('http_proof' + l,'guarantee_success' + l,'error','POST',proof_attr,VerifyProof),
    http_results = SendMessage('http_results' + l,'new_proof_features' + l,'',texts('http_results',l),''),
    new_proof_features = SendMessage('new_proof_features' + l,'confirm_interest' + l,'',texts('new_proof_features',l),''),
    confirm_interest,*x = Send_Reply_Split(l,'confirm_interest' + l,'','','exit' + l,texts('confirm_interest',l),split_confirm,split_confirm_var,600,''),

    purchase_accept = SendMessage('purchase_accept' + l,'','',texts('purchase_accept',l),''),
    purchase_deny = SendMessage('purchase_deny' + l,'','',texts('purchase_deny',l),''),

    return *set_amount,*wait_proof,*http_proof,*http_results,*new_proof_features,*confirm_interest,*purchase_accept,*purchase_deny

def Store(l):
    '''
    Manager scans the QR from the farmers phone.
    QR metadata: [200,phoneNmb,name,crop,variety]
    '''
    url = '{{{}widgets.{}.parsed.url{}}}'.format('{','http_issue' + l,'}')
    issue_attr = [
        {'key':'user_phone', 'value': '{{widgets.getAccount.parsed.user_phone}}'}, # attributes coming from QR scan!
        {'key':'user_name', 'value': '{{widgets.getAccount.parsed.user_name}}'},
        {'key':'phone', 'value': '{{contact.channel.address}}'},        
        {'key':'ct', 'value': '{{widgets.getAccount.parsed.ct}}'},        
        {'key':'did', 'value': '{{widgets.getAccount.parsed.did}}'},
        {'key':'store_amount', 'value': '{{{}widgets.{}.inbound.Body{}}}'.format('{','store_amount' + l,'}')},
        {'key':'store_grade', 'value': '{{{}widgets.{}.inbound.Body{}}}'.format('{','store_grade' + l,'}')},
    ]

    split_confirm_var = '{{{}widgets.{}.inbound.Body | downcase {}}}'.format('{','store_confirm' + l,'}')     
    store_amount_var = '{{{}widgets.{}.inbound.Body | downcase {}}}'.format('{','store_amount' + l,'}')     
    split_grade_var = '{{{}widgets.{}.inbound.Body | downcase {}}}'.format('{','store_grade' + l,'}')     
    split_confirm = [
        { 'next': 'http_issue' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('agree',l), 'argument': split_confirm_var},
        { 'next': 'store_deny' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('deny',l), 'argument': split_confirm_var},
        ]  
    
    store_credentials,*x = Send_Reply_Split(l,'store_credentials' + l,'store_amount' + l,'store_amount' + l,'store_amount' + l,texts('store_credentials',l),[],store_amount_var,5,''),

    set_amount,*x = Send_Reply_Split(l,'store_amount' + l,'store_grade' + l,'store_grade' + l,'store_grade' + l,texts('store_amount',l),[],store_amount_var,600,''),
    set_grade,*x = Send_Reply_Split(l,'store_grade' + l,'store_confirm' + l,'store_confirm' + l,'store_confirm' + l,texts('store_grade',l),[],split_grade_var,600,''),

    store_confirm,*x = Send_Reply_Split(l,'store_confirm' + l,'','','exit' + l,texts('store_confirm',l),split_confirm,split_confirm_var,600,''),

    http_issue = MakeHttpRequest('http_issue' + l,'store_success' + l,'error','POST',issue_attr,IssueStorage),

    store_success,*x = Send_Reply_Split(l,'store_success' + l,'','','exit' + l,texts('store_success',l),[],'None',5,url),
    store_deny = SendMessage('store_deny' + l,'','',texts('store_deny',l),''),

    return *store_credentials,*set_amount,*set_grade,*store_confirm,*http_issue,*store_success,*store_deny

def Proof(l):
    proof_url = '{{{}widgets.{}.body{}}}'.format('{','create_proof' + l,'}') 

    split_confirm_var = '{{{}widgets.{}.inbound.Body | downcase {}}}'.format('{','store_grade' + l,'}')     
    split_confirm = [
        { 'next': 'create_proof' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('agree',l), 'argument': split_confirm_var},
        { 'next': 'exit' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('deny',l), 'argument': split_confirm_var},
        ]  
    
    proof_attr = [
        {'key':'issuerDID', 'value': '{{flow.data.issuerDID}}'}, # attributes coming from QR scan!
        {'key':'credentialRequest', 'value': '{{flow.data.credentialRequest}}'},       
        {'key':'credential', 'value': '{{flow.data.credential}}'},   
        {'key':'phone', 'value': '{{contact.channel.address}}'},      
        {'key':'ct', 'value':'{{flow.data.ct}}'},
        {'key':'issuerDID', 'value':'{{flow.data.issuerDID}}'},
        {'key':'aadhar', 'value':'123456789012'},
        {'key':'idW', 'value':'{{flow.data.idW}}'},
        {'key':'txID', 'value':'{{flow.data.txID}}'},
    ]
    receive_creds,*x = Send_Reply_Split(l,'receive_creds' + l,'create_proof' + l,'create_proof' + l,'create_proof' + l,texts('receive_creds',l),split_confirm,split_confirm_var,600,''),

    create_proof = MakeHttpRequest('create_proof' + l,'send_proof' + l,'error','POST',proof_attr,ProofStorage),
    send_proof = SendMessage('send_proof' + l,'','',texts('send_proof',l),proof_url),

    return *receive_creds,*create_proof,*send_proof

def Master():
    
    var_initial = [
        # STATE:
        {'key':'response','value':'{{trigger.message.Body}}'}, # the initial response
        {'key':'user','value':""}, # the active user name
        {'key':'status','value':""}, # the account status (registered,unregistered,pending)
        {'key':'wallet','value':""}, # the wallet data of the active user 
        {'key':'l','value':'EN'}, # language of the chatbot
    ]

    attr_getAccount = [
        { 'key' : "phoneNumber", 'value': '{{contact.channel.address}}'},
        { 'key' :'response','value':'{{trigger.message.Body}}'}, # the initial response
    ]

    var_init_update = [
        # STATE:
        {'key':'name','value':'{{widgets.setName.inbound.Body}}'}, # the active user name
        {'key':'status','value':'unreg'}, # the account status (registered,unregistered,sponsor)
        {'key':'wallet','value':'none'}, # the wallet data of the active user 
        {'key':'l','value':'{{widgets.setLanguage.inbound.Body}}'}, # language of the chatbot
        {'key':'service','value':'0'}, # service to initiate if the user input is clear
        {'key':'class','value':'PROP'}, # classified response
    ]

    var_update = [
        # STATE:
        {'key':'user','value':'{{widgets.getAccount.parsed.name}}'}, # the active user name
        {'key':'status','value':'{{widgets.getAccount.parsed.status}}'}, # the account status (registered,unregistered,pending)
        {'key':'wallet','value':'{{widgets.getAccount.parsed.wallet}}'}, # the wallet data of the active user 
        {'key':'l','value':'{{widgets.getAccount.parsed.language}}'}, # language of the chatbot
        {'key':'service','value':'{{widgets.getAccount.parsed.service}}'}, # service to initiate if the user input is clear
        {'key':'class','value':'{{widgets.getAccount.parsed.class}}'},
    ]

    ## responses
    response = [
        ## registration
        { 'next': 'reg', 'friendly_name': 'registration', 'type': 'equal_to', 'value': '0', 'argument': '{{flow.variables.service}}'},
        ## wallet operations
        { 'next': 'wal', 'friendly_name': 'wallet operations', 'type': 'equal_to', 'value': '1', 'argument': '{{flow.variables.service}}'},
        ## credit operations
        { 'next': 'cred', 'friendly_name': 'credit operations', 'type': 'equal_to', 'value': '2', 'argument': '{{flow.variables.service}}'},
        ## sales and supply-chain operations
        { 'next': 'sale', 'friendly_name': 'supply operations', 'type': 'equal_to', 'value': '3', 'argument': '{{flow.variables.service}}'}, # parse qr metadata

        ## !!!!!!!!! TEST QR SCANS
        { 'next': 'store_credentials_EN', 'friendly_name': 'issue credentials by storage manager', 'type': 'equal_to', 'value': '200', 'argument': '{{flow.data.service}}'}, # !!!!!! language, parse qr metadata
        { 'next': 'purchase_set_amount_EN', 'friendly_name': 'trader interested to buy', 'type': 'equal_to', 'value': '300', 'argument': '{{flow.data.service}}'}, # !!!!!! language, parse qr metadata
        
        ## other
        { 'next': 'other', 'friendly_name': 'other', 'type': 'equal_to', 'value': '99', 'argument': '{{flow.variables.service}}'},
    ]
    
    # split REST API calls by service id   
    inRequest_response = [
        { 'next': 'sponsor_invite_EN', 'friendly_name': 'accept sponsorship', 'type': 'equal_to', 'value': '100', 'argument': '{{flow.data.id}}'},
        { 'next': 'receive_creds_EN', 'friendly_name': 'create proof', 'type': 'equal_to', 'value': '300', 'argument': '{{flow.data.id}}'},
        # inrequest coming from a QR code scan
    ]

    ## no user
    nouser_response = [
        ## registration
        { 'next': 'setName', 'friendly_name': 'registration', 'type': 'matches_any_of', 'value': texts('InitRegistration',''), 'argument': '{{widgets.noUser.inbound.Body}}'},
       ## info
        { 'next': 'info', 'friendly_name': 'registration', 'type': 'matches_any_of', 'value': texts('InfoRegistration',''), 'argument': '{{widgets.noUser.inbound.Body}}'},
       ]

    subflow_params = [
        ## specific subflow params
        {'key':'phone', 'value': '{{contact.channel.address}}'},
        {'key':'class','value':'{{flow.variables.class}}'},
        {'key':'response','value':'{{flow.variables.response}}'},
        {'key':'offline_mode','value':'{{flow.variables.offline_mode}}'},
        ## base params
        {'key':'user','value':'{{flow.variables.user}}'},
        {'key':'status','value':'{{flow.variables.status}}'},
        {'key':'wallet','value':'{{flow.variables.wallet}}'},
        {'key':'l','value':'{{flow.variables.l}}'},
    ]
    
    try:
        print('MASTER FLOW')
        flow = { "states": [ 
                trigger('Trigger','trigger_vars','','inRequest','inRequest'), # trigger, initial responds; service, user or service+user or undefined               
                SetVariables('trigger_vars','getAccount',var_initial),

                # inRequest message. Split to type
                SplitBasedOn('inRequest','error',inRequest_response), 

                # set variables
                MakeHttpRequest('getAccount','set_vars','noUser','POST',attr_getAccount,conversation), #getUserParams
                SetVariables('set_vars','readResponse' ,var_update),
                SplitBasedOn('readResponse','error',response), 

                # miscellaneous 
                SendMessage('error','','','Ues, Sorry something has gone wrong. Please try again.',''),
                SendMessage('leave_silently','','','',''),
                SendMessage('info','','',texts('info',''),''), 
                SendMessage('other','','','{{widgets.getAccount.parsed.conversation}}',''), 
                SendWaitForReply('noUser','noUserResponse','error','error',texts('noUser',''),1800),
                SplitBasedOn('noUserResponse','error',nouser_response), 

                # Set name and language if unknown user
                SendWaitForReply('setName','setLanguage','error','error',texts('name',''),1800),
                SendWaitForReply('setLanguage','set_init_vars','error','error',texts('language',''),1800),
                SetVariables('set_init_vars','genAccount' ,var_init_update),
                MakeHttpRequest('genAccount','reg','error','POST',attr_getAccount,generate_account), #genAccount
                
                *Guarantee('_EN'),
                *Purchase('_EN'),
                *Store('_EN'),
                *Proof('_EN'),

                # Execute subflow
                *SubFlow('cred','FW3e2dcb9602ebf7f298e0ce6bbb459bac',subflow_params),
                *SubFlow('wal','FW3fb896f6dc93f172640f27e1d1e72dc7',subflow_params),
                *SubFlow('reg','FW3a373f0f82aabe0033e6c6be2abc22ac',subflow_params),
                *SubFlow('sale','FW4882221bb99f71c530d964dbb1b817dd',subflow_params),
                ]
        } 

        jsonDump = packaging(flow)
        validate(jsonDump,'nila_master',VERSION)
        commit(jsonDump,'FW1327ad94088d2b26f52988905062b4c6',VERSION)

    
    except TwilioRestException as e: 
        print(e.details)
        print('------------------------')
        return "Error"

if __name__ == "__main__":
   Master()