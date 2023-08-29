import os
from widgets import trigger, SplitBasedOn, SendWaitForReply, MakeHttpRequest, SendMessage, SetVariables, SubFlow, Send_Reply_Split
from commit import validate,commit,packaging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from dotenv import load_dotenv

load_dotenv()

account_sid = os.getenv("ACCOUNT_SID")
auth_token = os.getenv("AUTH_TOKEN")
client = Client(account_sid, auth_token)
InitialSupplyRequest = 'https://7l3sx25tf9.execute-api.ap-south-1.amazonaws.com/stage/supply_init' # !!!!!!!!!! Update
VERSION = 'dev_0.0.0'

'''
    inrequest:
        prompt: sell crops
        validate: activity on field, crop tokens
        request: events, amount estimated, croptype
        compute: activity,credentials
        accept: pincode, storage manager scan of QR to issue credentials 
        pending: ................
    
    inmessage:
        - 
'''


def texts(widget,language):
    key = widget + language
    return {

        'agree_EN':'agree,yes,Yes,YES,Agree,Ok,agreed,read,complete,accept,accepted',
        'agree_TN':'agree,yes,Yes,YES,Agree,Ok,agreed,read,complete,accept,accepted',
        'deny_EN':'no,not agreed,No,NO',
        'deny_TN':'no,not agreed,No,NO',

        'next_EN':'next,continue',
        'next_TN':'next,continue',
        'proof_EN':'get,get proof,proof,qr',
        'proof_TN':'get,get proof,proof,qr',

        ## CLAIM CREDENTIALS
        'undetected_EN':'We are sorry. We are unable to find a cultivation on the fields you registered. Unfortunately no fix is available at this moment. Please try again later.',
        'undetected_TN':'We are sorry. We are unable to find a cultivation on the fields you registered. Unfortunately no fix is available at this moment. Please try again later.',

        'detected_EN':'{{widgets.validate.parsed.message}}',
        'detected_TN':'{{widgets.validate.parsed.message}}',

        'stored_EN':'Is the {{widgets.validate.parsed.ct}} stored in a registered warehouse or storage room?',
        'stored_TN':'Is the {{widgets.validate.parsed.ct}} stored in a registered warehouse or storage room?',

        'origin_proof_EN':'Type *get proof* to receive evidence of your cultivation. Type *next* to continue to storage handling.',
        'origin_proof_TN':'Type *get proof* to receive evidence of your cultivation. Type *next* to continue to storage handling.',

        'proof_EN': 'not yet implemented. Please type *sell* again.',
        'proof_TN': 'not yet implemented. Please type *sell* again.',

        'instore_EN':'Ok to sell your produce, Please let your storage manager scan the QR and issue the storage certificates.',
        'instore_TN':'Ok, to sell your produce, Please let your storage manager scan the QR and issue the storage certificates.',

        'outstore_EN':'Ok, find a secure place to store your crops. On delivery, let the storage manager scan the QR code and answer our questions. Type self-storage if you store the {{widgets.validate.parsed.ct}} yourself.',
        'outstore_TN':'Ok, find a secure place to store your crops. On delivery, let the storage manager scan the QR code and answer our questions. Type self-storage if you store the {{widgets.validate.parsed.ct}} yourself.',

        ## EXIT
        'exit_EN':'Ok',
        'exit_TN':'Ok',
         }[key]

def Claim(l):
    '''
        initial request to generate VCs
    '''

    url = '{{widgets.validate.parsed.qr_link}}'
    # split acceptance
    split_stored_var = '{{{}widgets.{}.inbound.Body | downcase {}}}'.format('{','stored' + l,'}') # listen if any response has been done, lowercase responds
    split_stored = [
        { 'next': 'instore' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('agree',l), 'argument': split_stored_var},
        { 'next': 'exit' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('deny',l), 'argument': split_stored_var},
        ]

    split_proof_var = '{{{}widgets.{}.inbound.Body | downcase {}}}'.format('{','genProof' + l,'}')
    split_proof = [
        { 'next': 'stored' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('next',l), 'argument': split_proof_var},
        { 'next': 'proof' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('proof',l), 'argument': split_proof_var},
        ]  
    
    # denial and reason (no sponsors, no liquidity available)
    undetected = SendMessage('undetected' + l,'','',texts('undetected',l),''), # will be implemented soon

    detected = SendWaitForReply('detected' + l,'genProof' + l,'genProof' + l,'genProof' + l,texts('detected',l),5),

    # approval, ask storage conditions after harvest
    genProof,*x = Send_Reply_Split(l,'genProof' + l,'error','error','exit' + l,texts('origin_proof',l),split_proof,split_proof_var,360,''),

    # approval, ask storage conditions after harvest  
    stored,*x = Send_Reply_Split(l,'stored' + l,'error','error','exit' + l,texts('stored',l),split_stored,split_stored_var,360,''),

    proof = SendMessage('proof' + l,'','',texts('proof',l),url),

    instore = SendMessage('instore' + l,'','',texts('instore',l),url),
    outstore = SendMessage('outstore' + l,'','',texts('outstore',l),url),

    exit = SendMessage('exit' + l,'','',texts('exit',l),''), # exit to parent flow and start again
    change_user = SendMessage('set_user' + l,'','',texts('exit',l),''), # exit to parent flow and start again

    return *undetected,*detected,*stored,*instore,*outstore,*exit,*change_user,*genProof,*proof

def Supply():
    get_attr = [
        {'key':'l','value':'{{trigger.parent.parameters.l}}'},
        {'key':'service','value':'{{trigger.parent.parameters.service}}'},
        {'key':'username','value':'{{trigger.parent.parameters.username}}'},
        {'key':'phone', 'value': '{{trigger.parent.parameters.phone}}'},
        {'key':'pk','value':'{{trigger.parent.parameters.pk}}'},
        {'key':'phone','value':'{{trigger.parent.parameters.phone}}'}, # phone of friend or self
        {'key':'status','value':'{{trigger.parent.parameters.status}}'},
        {'key':'response','value':'{{trigger.parent.parameters.response}}'},
        {'key':'f_list_string','value':'{{trigger.parent.parameters.f_list_string}}'},
        {'key':'f_list','value':'{{trigger.parent.parameters.f_list}}'},
        {'key':'offline_mode','value':'{{trigger.parent.parameters.offline_mode}}'},
        {'key':'wallet','value':'{{trigger.parent.parameters.wallet}}'},
    ]

    try:
        print('SUPPLY FLOW')
        setParent_var = [
            { 'next': 'detected_EN', 'friendly_name': 'lang', 'type': 'equal_to', 'value': 'DETECTED_EN', 'argument': '{{widgets.validate.parsed.res}}' + '_' + '{{trigger.parent.parameters.l}}'}, 
            { 'next': 'detected_TN', 'friendly_name': 'lang', 'type': 'equal_to', 'value': 'DETECTED_TN', 'argument': '{{widgets.validate.parsed.res}}' + '_' + '{{trigger.parent.parameters.l}}'},
            { 'next': 'undetected_EN', 'friendly_name': 'lang', 'type': 'equal_to', 'value': 'UNDETECTED_EN', 'argument': '{{widgets.validate.parsed.res}}' + '_' + '{{trigger.parent.parameters.l}}'}, 
            { 'next': 'undetected_TN', 'friendly_name': 'lang', 'type': 'equal_to', 'value': 'UNDETECTED_TN', 'argument': '{{widgets.validate.parsed.res}}' + '_' + '{{trigger.parent.parameters.l}}'},
        ]

        flow = { "states": [ 
                trigger('Trigger','validate','error','validate','validate'), # trigger, SUBFLOW connected  

                # SUBFLOW TO REQUEST CREDIT (incoming message)
                # validate request
                MakeHttpRequest('validate','readValidate','error','POST',get_attr,InitialSupplyRequest),
                # split to language, result and follow-up of request
                SplitBasedOn('readValidate','error',setParent_var), 

                # miscellaneous not language specific
                SendMessage('error','','','Ues, Sorry something has gone wrong. Please try again.',''),
                SendMessage('leave_silently','','','',''),

                # this is never called, just makes sure the widgets are duplicated during json builder.
                *Claim('_EN'),
                *Claim('_TN'),
                ]
        } 

        jsonDump = packaging(flow)
        validate(jsonDump,'nila_subflow_supply',VERSION)
        commit(jsonDump,'FW4882221bb99f71c530d964dbb1b817dd',VERSION)
    
    except TwilioRestException as e: 
        print(e)
        print('----------THIS IS AN ERROR --------------')
        return "Error"

if __name__ == "__main__":
   Supply()