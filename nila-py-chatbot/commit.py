import json
import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

account_sid = os.getenv("ACCOUNT_SID")
auth_token = os.getenv("AUTH_TOKEN")
client = Client(account_sid, auth_token)
member = 'https://nbkmpn6z0m.execute-api.ap-south-1.amazonaws.com/stage/member'
receive = 'https://fzfeh4kgbc.execute-api.ap-south-1.amazonaws.com/dev/receive'  # used in SOS,EOS but not created..

def packaging(package):
    # add parameters to JSON object  
    package['description'] = "ChittaBot"
    package['initial_state'] = "Trigger"
    package['flags'] = { "allow_concurrent_calls": True }     
    with open('flow.json', 'w') as f:
        json.dump(package, f, ensure_ascii=False, indent=4)
    f.close()
    return json.dumps(package)

def validate(package,flow_name,message):
    # run to validate the flow
    print(flow_name)
    print(message)
    flow = client.studio.flow_validate.update(
                               commit_message=message, 
                               definition=package, 
                               friendly_name=flow_name,
                               status='published')    
    print(flow)
    print(flow.valid) 


def commit(package,flow_id,message):
    # run to commit the new flow
    flow = client.studio.flows(flow_id).update(
                            commit_message=message,  
                            definition=package, 
                            status='published')
    print(flow.friendly_name)