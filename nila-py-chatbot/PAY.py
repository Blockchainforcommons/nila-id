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
pay_send = 'https://qieasxwyji.execute-api.ap-south-1.amazonaws.com/stage/pay_send'
pay_confirm = 'https://qieasxwyji.execute-api.ap-south-1.amazonaws.com/stage/pay_confirm'
VERSION = 'dev_0.0.0'

def texts(widget,language):
    key = widget + language
    return {
        ## LEAVE SILENTLY
        'leave_almost_silently_EN':'Ok',
        'leave_almost_silently_TN':'Ok',

        ## REWARDS ONLY
        'deposit_EN':'Thank you. Depositing funds is disabled. If you want to add CHT to pay for services, type _collect rewards_.',
        'deposit_TN':'Thank you. Depositing funds is disabled. If you want to add CHT to pay for services, type _collect rewards_.',

        ## EXIT SUBFLOW
        'exit_EN':'Ok',
        'exit_TN':'Ok',
        
        ## AMOUNT
        'amount_EN':'Ok. Lets make a UPI transfer. Please enter the amount in rupees',
        'amount_TN':'Ok. Lets make a UPI transfer. Please enter the amount in rupees',

        ## Write or scan UPI
        'upi_EN':'Enter the UPI you like to transfer {{widgets.PAY_EN.inbound.Body}} rupees to. Click _scan_ to open a QR scanner.',
        'upi_TN':'Enter the UPI you like to transfer {{widgets.PAY_TN.inbound.Body}} rupees to. Click _scan_ to open a QR scanner.',

        ## ENTER PIN
        'enter_pin_EN': 'Ok. Please give your 4 digit pincode.',
        'enter_pin_TN': 'Ok. Please give your 4 digit pincode.',

        ## SUCCESS
        'success_EN': 'Please wait for payment confirmation..',
        'success_TN': 'Please wait for payment confirmation..',

        ## INSUFFICIENT BALANCE, PLEASE TOPUP ( GO TO DEPOSIT )
        'fail_amnt_EN': 'Ues. Your balance is insufficient to pay {{widgets.PAY_EN.inbound.Body}} rupees. Please deposit additional funds.',
        'fail_amnt_TN': 'Ues. Your balance is insufficient to pay {{widgets.PAY_EN.inbound.Body}} rupees. Please deposit additional funds.',

        ## WRONG UPI
        'fail_upi_EN': 'Ues. We have not been able to verify the UPI. Please try again.',
        'fail_upi_TN': 'Ues. We have not been able to verify the UPI. Please try again.',

        ## WRONG PIN
        'fail_pin_EN': 'Ues. The pincode you gave does not match any wallet keys. Please try again.',
        'fail_pin_TN': 'Ues. The pincode you gave does not match any wallet keys. Please try again.',

        ## UNABLE TO SEND TRANSACTION. CONNECTION FAILURE
        'fail_tx_EN': 'Ues, We cant connect or you already send the amount. Please wait or try again.',
        'fail_tx_TN':'Ues, We cant connect or you already send the amount. Please wait or try again.',
        }[key]

def Send(l):
    # HTTPS ADD PAYSEND ATTRIBUTES
    attr_post = [
        {'key':'service','value':'{{trigger.parent.parameters.service}}'},
        {'key':'l','value':'{{trigger.parent.parameters.l}}'},
        {'key':'username','value':'{{trigger.parent.parameters.username}}'},
        {'key':'phone', 'value': '{{trigger.parent.parameters.phone}}'},
        {'key':'org','value':'{{trigger.parent.parameters.org}}'},
        {'key':'pk','value':'{{trigger.parent.parameters.pk}}'},
        {'key':'wallet','value':'{{trigger.parent.parameters.wallet}}'},
        {'key':'amnt','value':'{{{}widgets.{}.inbound.Body{}}}'.format('{','PAY' + l,'}')},
        {'key':'upi','value':'{{{}widgets.{}.inbound.Body{}}}'.format('{','UPI' + l,'}')},
        {'key':'pin','value':'{{{}widgets.{}.inbound.Body{}}}'.format('{','enter_pin' + l,'}')},
        
    ]
    split_amnt_var = '{{{}widgets.{}.inbound.Body{}}}'.format('{','PAY' + l,'}') 
    split_upi_var = '{{{}widgets.{}.inbound.Body{}}}'.format('{','UPI' + l,'}') 
    split_pin_var = '{{{}widgets.{}.inbound.Body{}}}'.format('{','enter_pin' + l,'}') 
    set_result_message_var = '{{{}widgets.{}.parsed.result {}}}'.format('{','sendPay' + l,'}')

    set_result_message = [
        { 'next': 'success' + l, 'friendly_name': 'success', 'type': 'equal_to', 'value': 0, 'argument': set_result_message_var}, 
        { 'next': 'fail_amnt' + l, 'friendly_name': 'fail_amnt', 'type': 'equal_to', 'value': 1, 'argument': set_result_message_var}, 
        { 'next': 'fail_upi' + l, 'friendly_name': 'fail_upi', 'type': 'equal_to', 'value': 2, 'argument': set_result_message_var}, 
        { 'next': 'fail_pin' + l, 'friendly_name': 'fail_pin', 'type': 'equal_to', 'value': 3, 'argument': set_result_message_var}, 
        { 'next': 'fail_tx' + l, 'friendly_name': 'fail_pin', 'type': 'equal_to', 'value': 4, 'argument': set_result_message_var}, 
        ]

    amount,*x = Send_Reply_Split(l,'PAY' + l,'leave_almost_silently' + l,'leave_almost_silently' + l,'UPI' + l,texts('amount',l),[],split_amnt_var,180,''), # wait 30 seconds..
    UPI,*x = Send_Reply_Split(l,'UPI' + l,'leave_almost_silently' + l,'leave_almost_silently' + l,'enter_pin' + l,texts('upi',l),[],split_upi_var,180,''), # wait 30 seconds..
    pin,*x = Send_Reply_Split(l,'enter_pin' + l,'leave_silently','leave_silently','sendPay' + l,texts('enter_pin',l),[],split_pin_var,180,''), # we reading something else, lets check what in the backend..
    
    # call to make deposit to middlemen wallet
    send_pay = MakeHttpRequest('sendPay' + l,'sendResult' + l,'success' + l,'POST',attr_post,pay_send), # call might be too long, then we assume that tx hasnt finished, so all seems fine and we show success Only when Payconfirm we are sure...
    send_result = SplitBasedOn('sendResult' + l,'leave_silently',set_result_message), 
    success = SendMessage('success' + l,'','',texts('success',l)),

    fail_amnt,*x = Send_Reply_Split(l,'fail_amnt' + l,'DEPOSIT' + l,'leave_silently','DEPOSIT' + l,texts('fail_amnt',l),[],'{{{}widgets.{}.inbound.Body{}}}'.format('{','fail_amnt' + l,'}'),2,''),
    fail_upi = SendMessage('fail_upi' + l,'UPI' + l,'',texts('fail_upi',l)),
    fail_pin = SendMessage('fail_pin' + l,'enter_pin' + l,'',texts('fail_pin',l)),
    fail_tx = SendMessage('fail_tx' + l,'','',texts('fail_tx',l)),

    silent = SendMessage('leave_almost_silently' + l,'','',texts('leave_almost_silently',l)),
    exit = SendMessage('exit' + l,'','',texts('exit',l)), # exit to parent flow and start again
    change_user = SendMessage('set_user' + l,'','',texts('exit',l)), # exit to parent flow and start again

    return *amount,*UPI,*pin,*send_pay,*send_result,*success,*fail_amnt,*fail_upi,*fail_pin,*fail_tx,*silent,*exit,*change_user #*phone,*conditions,*register,*result,*failure,*success,*silent,*exit,*change_user,*valid_phone,*phoneVar,*prev_reg

def Deposit(l):
    use_rewards = SendMessage('DEPOSIT' + l,'','',texts('deposit',l)),
    return *use_rewards,

def Transfer():
    try:
        print('PAY | DEPOSIT FLOW')

        setParent_var = [
            { 'next': 'PAY_EN', 'friendly_name': 'pay', 'type': 'equal_to', 'value': 'PAY_EN', 'argument': '{{trigger.parent.parameters.class}}' + '_' + '{{trigger.parent.parameters.l}}'}, 
            { 'next': 'PAY_TN', 'friendly_name': 'pay', 'type': 'equal_to', 'value': 'PAY_TN', 'argument': '{{trigger.parent.parameters.class}}' + '_' + '{{trigger.parent.parameters.l}}'}, 
            { 'next': 'DEPOSIT_EN', 'friendly_name': 'deposit', 'type': 'equal_to', 'value': 'DEPOSIT_EN', 'argument': '{{trigger.parent.parameters.class}}' + '_' + '{{trigger.parent.parameters.l}}'}, 
            { 'next': 'DEPOSIT_TN', 'friendly_name': 'deposit', 'type': 'equal_to', 'value': 'DEPOSIT_TN', 'argument': '{{trigger.parent.parameters.class}}' + '_' + '{{trigger.parent.parameters.l}}'}, 
            ]

        flow = { "states": [ 
                trigger('Trigger','pay_readResponse','','pay_readResponse','pay_readResponse'), # trigger, SUBFLOW connected  
                SplitBasedOn('pay_readResponse','error',setParent_var), 
                # SUBFLOW TO SEND OR DEPOSIT FUNDS

                # split send|deposit by looking at response. if not obvious pay/send, then deposit (resp can also be service redirect to add funds)

                # SEND
                   # open the link to QR or type UPI manually
                   # amount
                   # pin
                   # waiting...

                # DEPOSIT
                    # depositing funds is disabled. If you want to add funds to your wallet, simple type rewards

                # miscellaneous not language specific
                SendMessage('error','','','Ues, Sorry something has gone wrong. Please try again.'),
                SendMessage('leave_silently','','',''),
                # this is never called, just makes sure the widgets are duplicated during json builder.
                *Send('_EN'),
                *Send('_TN'),
                *Deposit('_EN'),
                *Deposit('_TN'),
                ]
        } 

        jsonDump = packaging(flow)
        validate(jsonDump,'nila_subflow_wallet',VERSION)
        commit(jsonDump,'FW3fb896f6dc93f172640f27e1d1e72dc7',VERSION)
    
    except TwilioRestException as e: 
        print(e.details)
        print('----------THIS IS AN ERROR --------------')
        return "Error"

if __name__ == "__main__":
   Transfer()