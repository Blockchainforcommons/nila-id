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
InitialCreditRequest = 'https://7l3sx25tf9.execute-api.ap-south-1.amazonaws.com/stage/credit_init'
CreditRequirements = 'https://7l3sx25tf9.execute-api.ap-south-1.amazonaws.com/stage/credit_req'
ContractIntent = 'https://7l3sx25tf9.execute-api.ap-south-1.amazonaws.com/stage/credit_intent'
VERSION = 'dev_0.0.0'

'''
    inrequest:
        prompt: request a loan
        validate: sponsors in area,sufficient liquidity in pool
        request: croptype, select fields
        compute: score,amount,sponsors
        accept: pincode, send message to sponsors with scorecard.
        pending: ................

        prompt: payback loan
        validate: find loan contract
        compute: outstanding amount (base + interest)
        accept: input amount, enter pincode
        success/failure: credit contract completed, lowered outstanding amount
    
    inmessage:
        - accepted: amount deposited in user wallet
        - rejected: sponsors rejected

    inmessage:
        - updated label, planting detected.
        - updated label, harvest detected.
        - request proof of planting.
        - loan reimbursement initiated. Please pay back your loan with the interest.
        - initiate sales with automated credit repay. Send labels to buyer. (QR code)
'''


def texts(widget,language):
    key = widget + language
    return {
        ## Denial reason
        'denial_EN':'{{widgets.validate.parsed.reason}}',
        'denial_TN':'{{widgets.validate.parsed.reason}}',

        ## Approval, set crop type
        'approve_croptype_EN':'Hi {{trigger.parent.parameters.user}}, To apply for a loan. Please select the crop you are going to cultivate.',
        'approve_croptype_TN':'Hi {{trigger.parent.parameters.user}}, To apply for a loan. Please select the crop you are going to cultivate.',

        'select_fields_EN':'Ok. Then select the fields you wish to use to grow {{widgets.approve_EN.inbound.Body}}: \n\n{{widgets.validate.parsed.field_string}}',
        'select_fields_TN':'Ok. Then select the fields you wish to use to grow {{widgets.approve_TN.inbound.Body}}: \n\n{{widgets.validate.parsed.field_string}}',

        ## Approval, read offer and agree to conditions 
        'compute_results_EN':'Good news {{trigger.parent.parameters.user}}. *Nila offers you Rs. {{widgets.compute_EN.parsed.amount}}/- loan with a {{widgets.compute_EN.parsed.rate}}% rate if you can find {{widgets.compute_EN.parsed.req_vouched}}*. Please read the below conditions before accepting:',
        'compute_results_TN':'Good news {{trigger.parent.parameters.user}}. *Nila offers you Rs. {{widgets.compute_TN.parsed.amount}}/- loan with a {{widgets.compute_TN.parsed.rate}}% rate if you can find {{widgets.compute_TN.parsed.req_vouched}}*. Please read the below conditions before accepting:',
        
        'conditions_EN':'The Nila Crop loan facility offers registered farmers a credit amount to meet all expenses involved in raising a particular crop including various agronomic practices.\n\nThe loan amount (quantum) is non-negotiable and is derived from remote on-site inspection and the historical analysis of the fields reported.\n\nEach loan offer requires at least one third-party guarantee (sponsor). Loans over Rs. 1,00,000/- DPN or loan offers to underperforming score card holders require two or more third-party guarantees. Sponsors receive a share of the interest paid.\n\nIn case of the inability of the farmer to repay the loan. The total amount – including interest – will be claimed from the guarantees.\n\nRepayment period will initiate after a harvest is detected on the reported fields. The repayment period is 6 weeks, irrespective of the growth duration of the crop. Nila performs remote harvest detection every 3 to 11 days.\n\nRepayment extension:\nThe repayment period can be extended or levied by a sponsor, if the warehouse receipt (crop token) of the full yield is deposited to the contract. The extension period is dependent on the crop perishability rate and warehouse characteristics.\n\nThe rate of interest (APR) is a fixed non-compounding daily rate. Early repay therefore significantly lowers the final cost of the credit line.\n\nType _Deposit_ to transfer funds to your wallet. Type _Repay_ to monitor the outstanding loan amount with accrued interest, and (partially) repay the loan.',
        'conditions_TN':'The Nila Crop loan facility offers registered farmers a credit amount to meet all expenses involved in raising a particular crop including various agronomic practices.\n\nThe loan amount (quantum) is non-negotiable and is derived from remote on-site inspection and the historical analysis of the fields reported.\n\nEach loan offer requires at least one third-party guarantee (sponsor). Loans over Rs. 1,00,000/- DPN or loan offers to underperforming score card holders require two or more third-party guarantees. Sponsors receive a share of the interest paid.\n\nIn case of the inability of the farmer to repay the loan. The total amount – including interest – will be claimed from the guarantees.\n\nRepayment period will initiate after a harvest is detected on the reported fields. The repayment period is 6 weeks, irrespective of the growth duration of the crop. Nila performs remote harvest detection every 3 to 11 days.\n\nRepayment extension:\nThe repayment period can be extended or levied by a sponsor, if the warehouse receipt (crop token) of the full yield is deposited to the contract. The extension period is dependent on the crop perishability rate and warehouse characteristics.\n\nThe rate of interest (APR) is a fixed non-compounding daily rate. Early repay therefore significantly lowers the final cost of the credit line.\n\nType _Deposit_ to transfer funds to your wallet. Type _Repay_ to monitor the outstanding loan amount with accrued interest, and (partially) repay the loan.',

        'accept_EN':'*Please accept the repay conditions on the Rs. {{widgets.compute_EN.parsed.amount}}/- loan with {{widgets.compute_EN.parsed.rate}} percent interest.*\n\n_On a 3-month duration. The total amount due is Rs. {{widgets.compute_EN.parsed.total_base}}/-_',
        'accept_TN':'*Please accept the repay conditions on the Rs. {{widgets.compute_TN.parsed.amount}}/- loan with {{widgets.compute_TN.parsed.rate}} percent interest.*\n\n_On a 3-month duration. The total amount due is Rs. {{widgets.compute_TN.parsed.total_base}}/-_',

        'not_accepted_EN': 'Alright. No problem. Sorry to hear you have not accepted the offer. You can always try again later.',
        'not_accepted_TN': 'Alright. No problem. Sorry to hear you have not accepted the offer. You can always try again later.',

        'agree_EN':'agree,yes,Yes,YES,Agree,Ok,agreed,read,complete,accept,accepted',
        'agree_TN':'agree,yes,Yes,YES,Agree,Ok,agreed,read,complete,accept,accepted',
        'deny_EN':'no,not agreed,No,NO',
        'deny_TN':'no,not agreed,No,NO',

        'request_vouch_EN':'Thank you. Please enter your PIN to send your loan request and score card to the following parties:\n{{widgets.validate.parsed.sponsor_string}}.\n\n_Upon acceptance of the sponsors, the amount will be instantly transferred to your wallet._',
        'request_vouch_TN':'Thank you. Please enter your PIN to send your loan request and score card to the following parties:\n{{widgets.validate.parsed.sponsor_string}}.\n\n_Upon acceptance of the sponsors, the amount will be instantly transferred to your wallet._',
        
        ## END
        'end_EN':'Thank you. We have send your data to potential sponsors.',
        'end_TN':'Thank you. We have send your data to potential sponsors.',

        ## EXIT
        'exit_EN':'Ok',
        'exit_TN':'Ok',
         }[key]

def Request(l):
    '''
        initial request, communicatie validate and deny/approve - set croptype and fields, send proposal to sponsors.
    '''
    get_attr = [
        # from parent
        {'key':'l','value':'{{trigger.parent.parameters.l}}'},
        {'key':'name','value':'{{trigger.parent.parameters.user}}'},
        {'key':'wallet','value':'{{trigger.parent.parameters.wallet}}'},
        {'key':'phone', 'value': '{{trigger.parent.parameters.phone}}'},
        # from input
        {'key':'croptype','value':'{{{}widgets.{}.inbound.Body | downcase {}}}'.format('{','approve' + l,'}')},
        {'key':'pin','value':'{{{}widgets.{}.inbound.Body{}}}'.format('{','sponsors' + l,'}')},
        {'key':'selected_fields','value':'{{{}widgets.{}.inbound.Body | downcase {}}}'.format('{','select_fields' + l,'}')},
        {'key':'all_fields','value':'{{widgets.validate.parsed.fields}}'},
        {'key':'area','value':'{{widgets.validate.parsed.area}}'},
        {'key':'sponsors','value':'{{widgets.validate.parsed.sponsors}}'},
        {'key':'amount','value':'{{{}widgets.{}.parsed.amount{}}}'.format('{','compute' + l,'}')},
        {'key':'rate','value':'{{{}widgets.{}.parsed.rate{}}}'.format('{','compute' + l,'}')},
    ]

    # split acceptance
    split_accept_var = '{{{}widgets.{}.inbound.Body | downcase {}}}'.format('{','accept' + l,'}') # listen if any response has been done, lowercase responds
    split_accept = [
        { 'next': 'sponsors' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('agree',l), 'argument': split_accept_var},
        { 'next': 'exit' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('deny',l), 'argument': split_accept_var},
        ]
    
    # denial and reason (no sponsors, no liquidity available)
    denial = SendMessage('denial' + l,'','',texts('denial',l)), # exit to parent flow and start again
    # approval, ask crop type.
    approve_croptype,*x = Send_Reply_Split(l,'approve' + l,'error','error','select_fields' + l,texts('approve_croptype',l),[],'{{{}widgets.{}.inbound.Body{}}}'.format('{','approve' + l,'}'),360,''),
    # approval, list and select fields
    select_fields,*x = Send_Reply_Split(l,'select_fields' + l,'error','error','compute' + l,texts('select_fields',l),[],'{{{}widgets.{}.inbound.Body{}}}'.format('{','select_fields' + l,'}'),360,''),
    
    # compute conditions
    compute = MakeHttpRequest('compute' + l,'compute_results' + l,'error','POST',get_attr,CreditRequirements),
    compute_results,*x = Send_Reply_Split(l,'compute_results' + l,'conditions' + l,'error','exit' + l,texts('compute_results',l),[],'{{{}widgets.{}.inbound.Body{}}}'.format('{','compute_results' + l,'}'),5,''),
    conditions,*x = Send_Reply_Split(l,'conditions' + l,'accept' + l,'error','exit' + l,texts('conditions',l),[],'{{{}widgets.{}.inbound.Body{}}}'.format('{','conditions' + l,'}'),5,''),
    # acceptance to conditions
    accept,*x = Send_Reply_Split(l,'accept' + l,'not_accepted' + l,'error','exit' + l,texts('accept',l),split_accept,split_accept_var,1800,''),
    # list sponsors in the area. acceptance to contact sponsors.
    sponsors,*x = Send_Reply_Split(l,'sponsors' + l,'error','error','send_to_sponsors' + l,texts('request_vouch',l),[],'{{{}widgets.{}.inbound.Body{}}}'.format('{','sponsors' + l,'}'),360,''),
    # finalize request
    send_to_sponsors = MakeHttpRequest('send_to_sponsors' + l,'end' + l,'error','POST',get_attr,ContractIntent),
    end = SendMessage('end' + l,'','',texts('end',l)), # exit to parent flow and start again
    not_accepted = SendMessage('not_accepted' + l,'','',texts('not_accepted',l)), # exit to parent flow and start again

    exit = SendMessage('exit' + l,'','',texts('exit',l)), # exit to parent flow and start again
    change_user = SendMessage('set_user' + l,'','',texts('exit',l)), # exit to parent flow and start again

    return *denial,*approve_croptype,*select_fields,*compute,*compute_results,*conditions,*accept,*sponsors,*send_to_sponsors,*exit,*change_user,*end,*not_accepted

def Credit():
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
        print('CREDIT FLOW')
        setParent_var = [
            { 'next': 'denial_EN', 'friendly_name': 'lang', 'type': 'equal_to', 'value': 'DENY_EN', 'argument': '{{widgets.validate.parsed.res}}' + '_' + '{{trigger.parent.parameters.l}}'}, 
            { 'next': 'denial_TN', 'friendly_name': 'lang', 'type': 'equal_to', 'value': 'DENY_TN', 'argument': '{{widgets.validate.parsed.res}}' + '_' + '{{trigger.parent.parameters.l}}'},
            { 'next': 'approve_EN', 'friendly_name': 'lang', 'type': 'equal_to', 'value': 'APPROVE_EN', 'argument': '{{widgets.validate.parsed.res}}' + '_' + '{{trigger.parent.parameters.l}}'}, 
            { 'next': 'approve_TN', 'friendly_name': 'lang', 'type': 'equal_to', 'value': 'APPROVE_TN', 'argument': '{{widgets.validate.parsed.res}}' + '_' + '{{trigger.parent.parameters.l}}'},
        ]

        flow = { "states": [ 
                trigger('Trigger','validate','error','validate','validate'), # trigger, SUBFLOW connected  

                # SUBFLOW TO REQUEST CREDIT (incoming message)
                # validate request
                MakeHttpRequest('validate','readValidate','error','POST',get_attr,InitialCreditRequest),
                # split to language, result and follow-up of request
                SplitBasedOn('readValidate','error',setParent_var), 

                # miscellaneous not language specific
                SendMessage('error','','','Ues, Sorry something has gone wrong. Please try again.'),
                SendMessage('leave_silently','','',''),

                # this is never called, just makes sure the widgets are duplicated during json builder.
                *Request('_EN'),
                *Request('_TN'),
                ]
        } 

        jsonDump = packaging(flow)
        validate(jsonDump,'nila_subflow_credit',VERSION)
        commit(jsonDump,'FW3e2dcb9602ebf7f298e0ce6bbb459bac',VERSION)
    
    except TwilioRestException as e: 
        print(e.details)
        print('----------THIS IS AN ERROR --------------')
        return "Error"

if __name__ == "__main__":
   Credit()