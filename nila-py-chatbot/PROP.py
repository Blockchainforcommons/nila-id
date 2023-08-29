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
propertyAssetCreate = 'https://7l3sx25tf9.execute-api.ap-south-1.amazonaws.com/stage/asset_create'
propertyAssetView = 'https://7l3sx25tf9.execute-api.ap-south-1.amazonaws.com/stage/asset_view'
propertyAssetEdit = 'https://7l3sx25tf9.execute-api.ap-south-1.amazonaws.com/stage/asset_edit'
offline = 'https://qieasxwyji.execute-api.ap-south-1.amazonaws.com/stage/offline_mode'
VERSION = 'dev_0.0.0'

def texts(widget,language):
    key = widget + language
    string_to_list = '{% assign points = flow.variables.points | split: "$" %}{% assign names = flow.variables.names | split: "$" %}'
    iterate_arrays = '{% for p in points %}* {{ names[forloop.index0] | upcase }}: ({{ p }})\n{% endfor %}'
    return {
        ## GPS ISSUE
        'GPS_issue_EN':'Alas, it seems like your GPS has not updated. We got the exact same coordinates again. Make sure the point on the map is placed correctly. Please try again.',
        'GPS_issue_TN':'Alas, it seems like your GPS has not updated. We got the exact same coordinates again. Make sure the point on the map is placed correctly. Please try again.',

        ## CONFIRM TO LEAVE SUBFLOW
        'confirm_Exit_EN':'ok,done,completed,finish,finished,continue', # ALSO ADD NEW KEYWORDS TO ASSETS.PY - PROPERTY ASSETS
        'confirm_Exit_min3_EN':'ok_min3,done_min3,completed_min3,finish_min3,finished_min3,continue_min3',
        'confirm_Exit_TN':'ok,done,completed,finish,finished,continue',
        'confirm_Exit_min3_TN':'ok_min3,done_min3,completed_min3,finish_min3,finished_min3,continue_min3',

        ## PENDING SCORE CARD
        'pending_score_EN': 'Thank you for registering. Your account is pending a farm score card. Type _score_ to view the status and update the card if needed.',
        'pending_score_TN': 'Thank you for registering. Your account is pending a farm score card. Type _score_ to view the status and update the card if needed.',

        ## EXIT SUBFLOW
        'exit_EN':'Sure.',
        'exit_TN':'Sure',
        
        ## CONFIRM TO SUBFLOW
        'confirm_EN':'ok,yes,sure,agree,agreed,continue,next,y,proceed',
        'confirm_TN':'ok,yes,sure,agree,agreed,continue,next,y,proceed',

        ## SHARE LOCATION
        'share_location_EN':'{% assign count = flow.variables.count %}{% if count == null %}Please share a location in - or close next to - the first field.{% elsif count == "1" %}Ok, walk to the next field and share the location again. Check if the GPS has actually updated!{% elsif count == "2" %}Its going great. Move the next field. You need to share at least 1 more point.{% else %}Ok. Register as many fields as possible. If in the last year you used some part of a field as nursery, send it as a unique location, as our algorithm sees these as seperate fields. Type _done_ once you have registered the entire property.{% endif %}',
        'share_location_TN':'{% assign count = flow.variables.count %}{% if count == null %}Please share a location in - or close next to - the first field.{% elsif count == "1" %}Ok, walk to the next field and share the location again. Check if the GPS has actually updated!{% elsif count == "2" %}Its going great. Move the next field. You need to share at least 1 more point.{% else %}Ok. Register as many fields as possible. If in the last year you used some part of a field as nursery, send it as a unique location, as our algorithm sees these as seperate fields. Type _done_ once you have registered the entire property.{% endif %}',

        ## GIVE NAME 
        'field_name_EN':'Good, give a name to the field. {}'.format('{% if flow.variables.count == null %}Most farmers use names that are familiar to themselves, such as the neighbor name or a feature in the field itself.{% else %}{% endif %}'),
        'field_name_TN':'Good, give a name to the field. {}'.format('{% if flow.variables.count == null %}Most farmers use names that are familiar to themselves, such as the neighbor name or a feature in the field itself.{% else %}{% endif %}'),

        ## LIST REGISTERED FIELDS
        'list_registered_EN': string_to_list + 'Well done. These are the registered fields:\n\n' + iterate_arrays + '\nType _continue_ to create the property asset, type _remove + field name_ to remove a field.',
        'list_registered_TN': string_to_list + 'Well done. These are the registered fields:\n\n' + iterate_arrays + '\nType _continue_ to create the property asset, type _remove + field name_ to remove a field.',

        ## THRESHOLD
        'min_3_EN': 'Ues, you need to share more points. Please add another point. If there are no more fields, find another location, e.g next to the well, or another side of the field.',
        'min_3_TN': 'Ues, you need to share more points. Please add another point. If there are no more fields, find another location, e.g next to the well, or another side of the field.',

        ## ENTER PIN
        'enter_pin_EN': 'Ok. Please give your 4 digit pincode.',
        'enter_pin_TN': 'Ok. Please give your 4 digit pincode.',

        ## ESTIMATE PROPERTY SIZE IN ACRES
        'est_size_EN': 'Please what is the total size of your property in acres?',
        'est_size_TN': 'Please what is the total size of your property in acres?',

        ## SUCCESS
        'success_EN': 'Great. The property asset has been requested. It can take up to 1 hour before you receive the asset. After that, type _property for {{trigger.parent.parameters.username}}_ and collect the asset.',
        'success_TN': 'Great. The property asset has been requested. It can take up to 1 hour before you receive the asset. After that, type _property for {{trigger.parent.parameters.username}}_ and collect the asset.',

        ## FAILURE
        'failure_EN': 'Ues, something went wrong. Are you sure the pincode is correct?',
        'failure_TN': 'Ues, something went wrong. Are you sure the pincode is correct?',

        ## FAILURE
        'unclear_if_succeeded_EN': 'Done. Unfortunately I was not able to check if the transaction went fine. Type _property for {{trigger.parent.parameters.username}}_ in about 20 minutes or so.',
        'unclear_if_succeeded_TN': 'Done. Unfortunately I was not able to check if the transaction went fine. Type _property for {{trigger.parent.parameters.username}}_ in about 20 minutes or so.',

        ## REDO
        'redo_EN':'Done. we removed {{{}widgets.{}.parsed.removed_name{}}} from the list.'.format('{','getFieldCheck' + language,'}'),
        'redo_TN':'Done. we removed {{{}widgets.{}.parsed.removed_name{}}} from the list.'.format('{','getFieldCheck' + language,'}'),

        ## WAIT 20SEC 
        'wait_EN':'One second please.',
        'wait_TN':'One second please.',

        ## VIEW PROP ASSETS
        'view_prop_asset_EN':'Sure, here is the registered property for {{trigger.parent.parameters.username}}.\n\nstatus: {{flow.variables.prop_stat}}\n\nPlease click edit or exit.',
        'view_prop_asset_TN':'Sure, here is the registered property for {{trigger.parent.parameters.username}}.\n\nstatus: {{flow.variables.prop_stat}}\n\nPlease click edit or exit.',

        ## OFFLINE MODE EXPLANATION
        'offline_EN':'Sure. Only use offline mode when there is no internet on the farm to register.\n\n*How it works:*\n* Walk to a field, then send a location and a fieldname message. Make sure the red icon is located where you are standing.\n* Walk to another field and send another location and another fieldname message.\n* Continue untill you have send a location and name message for all fields, or at least from 3 locations. Dont forget to send the location of an area you used as nursery this last years.\n* Find an internet connection within 12 hours, and enter your pin.\n\nThat is it. You can move offline now. Lets go!',
        'offline_TN':'Sure. Only use offline mode when there is no internet on the farm to register.\n\n*How it works:*\n* Walk to a field, then send a location and a fieldname message. Make sure the red icon is located where you are standing.\n* Walk to another field and send another location and another fieldname message.\n* Continue untill you have send a location and name message for all fields, or at least from 3 locations. Dont forget to send the location of an area you used as nursery this last years.\n* Find an internet connection within 12 hours, and enter your pin.\n\nThat is it. You can move offline now. Lets go!',
        
        ## ISSUE ABORT
        'issue_abort_EN':'Ues. Something has gone wrong i am afraid. Did you send in at least 3 locations, each followed by a name? If not, please try again. We are not yet possible to recover your inputs.',
        'issue_abort_TN':'Ues. Something has gone wrong i am afraid. Did you send in at least 3 locations, each followed by a name? If not, please try again. We are not yet possible to recover your inputs.',
        
        ## SYNC DATA
        'sync_data_EN':'Great. You are back.',
        'sync_data_TN':'Great. You are back.',

        ## SHITTY LOOP TO ASK USER TO REQUEST AGAIN
        'try_again_EN':'Ok I ordered to generate an image. Please type _property of {{trigger.parent.parameters.username}}_ again. Sorry for the inconvenience',
        'try_again_TN':'Ok I ordered to generate an image. Please type _property of {{trigger.parent.parameters.username}}_ again. Sorry for the inconvenience',

        ## OFFLINE MODE LOOP
        'offline_loop_EN':'Ok thanks. You can go offline now.',
        'offline_loop_TN':'Ok thanks. You can go offline now.',

        ## PENDING ASSET, REQUEST PIN.
        'pending_asset_EN':'Good news. The property asset for {{trigger.parent.parameters.username}} is ready. Lets collect it. Enter your pin please',
        'pending_asset_TN':'Good news. The property asset for {{trigger.parent.parameters.username}} is ready. Lets collect it. Enter your pin please',
         }[key]

def OfflineMode(l):
    attr_offline = [
        {'key':'service', 'value': 'PROP'},
        {'key':'phone', 'value': '{{trigger.parent.parameters.phone}}'},
        {'key':'phoneNumber', 'value': '{{trigger.parent.parameters.phoneNumber}}'},
        {'key':'org','value':'{{trigger.parent.parameters.org}}'},
        {'key':'pk','value':'{{trigger.parent.parameters.pk}}'}
    ]
    setVar_field = [
        {'key':'points','value': '{{{}widgets.{}.parsed.points{}}}'.format('{','offline_collect' + l,'}')},
        {'key':'names','value': '{{{}widgets.{}.parsed.names{}}}'.format('{','offline_collect' + l,'}')},
        {'key':'count','value':'OFFLINE'},
    ]
    
    resp_offline_var = '{{{}widgets.{}.parsed.response{}}}'.format('{','offline_collect' + l,'}')
    resp_offline = [
        { 'next': 'list_registered' + l, 'friendly_name': 'list', 'type': 'equal_to', 'value': 1, 'argument': resp_offline_var}, # if keyword is downcase
        { 'next': 'issue_abort' + l, 'friendly_name': 'abort', 'type': 'equal_to', 'value': 0, 'argument': resp_offline_var}, # if keyword is uppercase
    ]

    # send instructions, set possible responds as variable
    Instructions,*x = Send_Reply_Split(l,'offline' + l,'','','setVars_offline' + l,texts('offline',l),[],'{{{}widgets.{}.inbound.Body{}}}'.format('{','offline' + l,'}'),43200,''),
    setVars_offline = SetVariables('setVars_offline' + l,'sync_data' + l,[{'key': 'resp', 'value': '{{{}widgets.{}.inbound.Body{}}}'.format('{','offline' + l,'}')}]),

    # widget to wait a second for the webhook calls to store location data.
    Sync_data,*x = Send_Reply_Split(l,'sync_data' + l,'offline_collect' + l,'','offline_collect' + l,texts('sync_data',l),[],'{{{}widgets.{}.inbound.Body{}}}'.format('{','sync_data' + l,'}'),5,''),
    Offline_collect = MakeHttpRequest('offline_collect' + l,'setVars_offline_field' + l,'setVars_offline_field' + l,'POST',attr_offline,offline), #getFieldCheck, if failed, continue by entering pin..

    # set names and points so we can try something if for example the pin is incorrect.
    setfieldvarsOffline = SetVariables('setVars_offline_field' + l,'response_Offline' + l,setVar_field),
    response_Offline = SplitBasedOn('response_Offline' + l,'setVars_field' + l,resp_offline),

    issue_abort = SendMessage('issue_abort' + l,'','',texts('issue_abort',l)),

    return *Instructions,*setVars_offline,*Sync_data,*Offline_collect,*setfieldvarsOffline,*response_Offline,*issue_abort

def CollectCreate(l):  
    # OFF OR ONLINE MODE
    off_online = [
        { 'next': 'share_location' + l, 'friendly_name': 'success', 'type': 'not_equal_to', 'value': '1', 'argument': '{{trigger.parent.parameters.offline_mode}}'},
        { 'next': 'offline' + l, 'friendly_name': 'failure', 'type': 'equal_to', 'value': '1', 'argument': '{{trigger.parent.parameters.offline_mode}}'},
    ] 

    # SET LOCATION OF FIELD
    split_share_var = '{% if flow.variables.count == null or flow.variables.count == "1" or flow.variables.count == "2" %}' + '{{{}widgets.{}.inbound.Body{}}}'.format('{','share_location' + l,'}') + '_min3{% else %}' + '{{{}widgets.{}.inbound.Body{}}}'.format('{','share_location' + l,'}') + '{% endif %}' # 
    split_share = [
        { 'next': 'list_registered' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('confirm_Exit',l), 'argument': split_share_var}, # if keyword + count = min
        { 'next': 'min_3' + l, 'friendly_name': 'minimal 3', 'type': 'matches_any_of', 'value': texts('confirm_Exit_min3',l), 'argument': split_share_var}, # if keyword + count = notmin
        { 'next': 'exit' + l, 'friendly_name':'remove_service', 'type':'matches_any_of',  'value':'cancel_min3,exit_min3,close_min3','argument':split_share_var},
        { 'next': 'set_user' + l, 'friendly_name':'change_user', 'type':'matches_any_of', 'value':'change_min3,edit_min3,swap_min3','argument':split_share_var},
        { 'next': 'field_name' + l, 'friendly_name': 'continue', 'type': 'not_equal_to', 'value': '', 'argument': split_share_var},
        ]

    # SET NAME OF FIELD
    split_name_var = '{% if flow.variables.count == null or flow.variables.count == "1" or flow.variables.count == "2" %}' + '{{{}widgets.{}.inbound.Body{}}}'.format('{','field_name' + l,'}') + '_min3{% else %}' + '{{{}widgets.{}.inbound.Body{}}}'.format('{','field_name' + l,'}') + '{% endif %}' # 
    split_name = [
        { 'next': 'list_registered' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('confirm_Exit',l), 'argument': split_name_var}, # if keyword is downcase
        { 'next': 'min_3' + l, 'friendly_name': 'minimal 3', 'type': 'matches_any_of', 'value': texts('confirm_Exit_min3',l), 'argument': split_name_var}, # if keyword is uppercase
        { 'next': 'exit' + l, 'friendly_name':'remove_service', 'type':'matches_any_of',  'value':'cancel_min3,exit_min3,close_min3','argument':split_name_var},
        { 'next': 'set_user' + l, 'friendly_name':'change_user', 'type':'matches_any_of', 'value':'change_min3,edit_min3,swap_min3','argument':split_name_var},
        { 'next': 'setVars_field' + l, 'friendly_name': 'continue', 'type': 'not_equal_to', 'value': '', 'argument': split_name_var},
        ]

    # APPEND POINT/NAMES TO LIST
    assign_points = '{% assign lat_EN = widgets.share_location_EN.inbound.Latitude %}{% assign lng_EN = widgets.share_location_EN.inbound.Longitude %}{% assign lat_TN = widgets.share_location_TN.inbound.Latitude %}{% assign lng_TN = widgets.share_location_TN.inbound.Longitude %}'
    assign_body = '{% assign name_EN = widgets.field_name_EN.inbound.Body %}{% assign name_TN = widgets.field_name_TN.inbound.Body %}'
    assign_latestlatlng = '{% assign points = flow.variables.points | split: "&" %}{% assign latest = points.last | split: "," %}{% assign lat = latest.first %}{% assign lng = latest.last %}'
    
    setVar_field = [
        {'key':'points','value': assign_points + '{% if flow.variables.points == null %}{{lat_EN}}{{lat_TN}},{{lng_EN}}{{lng_TN}}{% else %}{{ flow.variables.points | append: "$" | append: lat_EN | append: lat_TN | append: "," | append: lng_EN | append: lng_TN }}{% endif %}'}, # append user to service response
        {'key':'names','value': assign_body + '{% if flow.variables.names == null %}{{name_EN}}{{name_TN}}{% else %}{{ flow.variables.names | append: "$" | append: name_EN | append: name_TN }}{% endif %}'},
        {'key':'count','value':'{% if flow.variables.count %}{{flow.variables.count | plus: 1}}{% else %}1{% endif %}'},
    ]
    
    updateVar_field = [
        {'key':'points','value':'{{{}widgets.{}.parsed.points{}}}'.format('{','getFieldCheck' + l,'}')}, 
        {'key':'names','value':'{{{}widgets.{}.parsed.names{}}}'.format('{','getFieldCheck' + l,'}')},         
        {'key':'count','value':'{% if flow.variables.count %}{{flow.variables.count | minus: 1}}{% else %}1{% endif %}'},
    ]

    compare_points = assign_points + assign_latestlatlng + '{% if points.size > 1 and lat == lat_EN or lat == lat_TN or lng == lng_EN or lng == lng_TN %}0{% else %}1{% endif %}' # skip if points = empty, otherwise split string &, split ',' then compare last with new, true if different false if same.
    break_loop = [{ 'next': 'GPS_issue' + l, 'friendly_name': 'gps_not_updating', 'type': 'equal_to', 'value': '0', 'argument': compare_points}] # check to see if all is going fine.

    http_check_var = '{{{}widgets.{}.body{}}}'.format('{','getPropertyAsset' + l,'}') 
    http_check = [
        { 'next': 'success' + l, 'friendly_name': 'success', 'type': 'equal_to', 'value': 1, 'argument': http_check_var},
        { 'next': 'enter_pin' + l, 'friendly_name': 'data_error', 'type': 'equal_to', 'value': 2, 'argument': http_check_var},
       ] 

    http_check_var_retry = '{{{}widgets.{}.body{}}}'.format('{','getPropertyRetry' + l,'}') 
    http_check_retry = [
        { 'next': 'success' + l, 'friendly_name': 'success', 'type': 'equal_to', 'value': 1, 'argument': http_check_var_retry},
        { 'next': 'enter_pin' + l, 'friendly_name': 'data_error', 'type': 'equal_to', 'value': 2, 'argument': http_check_var_retry},
       ] 

    # PRINT LIST OF FIELDS FOR VERIFICATION
    split_list_var = '{{{}widgets.{}.inbound.Body | downcase {}}}'.format('{','list_registered' + l,'}') # listen if any response has been done, lowercase responds
    split_list = [
        { 'next': 'est_size' + l, 'friendly_name': 'continue', 'type': 'matches_any_of', 'value': texts('confirm_Exit',l), 'argument': split_list_var},
        ]

    # SET SIZE AND PINCODE
    split_size_var = '{{{}widgets.{}.inbound.Body{}}}'.format('{','est_size' + l,'}') 
    split_pin_var = '{{{}widgets.{}.inbound.Body{}}}'.format('{','enter_pin' + l,'}') 

    # HTTPS CREATE PROPERTY ASSET ATTRIBUTES
    attr_gets = [
        {'key':'count','value':'{{flow.variables.count}}'},
        {'key':'points','value':'{{flow.variables.points}}'},
        {'key':'names','value':'{{flow.variables.names}}'},
        {'key':'list_responds','value':'{{{}widgets.{}.inbound.Body{}}}'.format('{','list_registered' + l,'}')},
        {'key':'pin','value':'{{{}widgets.{}.inbound.Body{}}}'.format('{','enter_pin' + l,'}')},
        {'key':'size','value':'{{{}widgets.{}.inbound.Body{}}}'.format('{','est_size' + l,'}')},
        {'key':'phone', 'value': '{{trigger.parent.parameters.phone}}'},
        {'key':'phoneNumber', 'value': '{{trigger.parent.parameters.phoneNumber}}'},
        {'key':'l', 'value': '{{trigger.parent.parameters.l}}'},
        {'key':'org','value':'{{trigger.parent.parameters.org}}'},
        {'key':'pk','value':'{{trigger.parent.parameters.pk}}'},
        {'key':'status','value':'{{trigger.parent.parameters.status}}'},
    ]
    
    # DIVIDE FIRST ON OFF OR ONLINE MODE
    off_online = SplitBasedOn('off_online' + l,'share_location' + l,off_online), 

    # SHARE LOCATION
    share,*x = Send_Reply_Split(l,'share_location' + l,'leave_silently','leave_silently','field_name' + l,texts('share_location',l),split_share,split_share_var,1800,''), # give half hour to share location, needs B var to look in BODY...
    # ADD FIELD NAME
    name,*x =Send_Reply_Split(l,'field_name' + l,'leave_silently','leave_silently','setVars_field' + l,texts('field_name',l),split_name,split_name_var,1800,''), # give half hour to name field
    # GPS CHECK
    break_loop = SplitBasedOn('break_loop' + l,'setVars_field' + l,break_loop),    
    # SET VARS: append coordinates, append names, append counter
    setfieldvars =SetVariables('setVars_field' + l,'share_location' + l,setVar_field),
    gps_issue = SendMessage('GPS_issue' + l,'share_location' + l,'',texts('GPS_issue',l)), # GPS not updated, skip set variables and try again.
    # END LOOP #

    # loop is completed, list all fields, NO_MATCH = remove + fieldname. 
    list_registered,*x = Send_Reply_Split(l,'list_registered' + l,'leave_silently','error','getFieldCheck' + l,texts('list_registered',l),split_list,split_list_var,14400,''), # loop for completed, otherwise read input backend to decide next.
    min_3 = SendMessage('min_3' + l,'share_location' + l,'share_location' + l,texts('min_3',l)),

    # SEND
    getFieldCheck = MakeHttpRequest('getFieldCheck' + l,'updateVars_field' + l,'failure' + l,'POST',attr_gets,propertyAssetCreate), #getFieldCheck, if failed, continue by entering pin..
    getPropertyAsset = MakeHttpRequest('getPropertyAsset' + l,'getPropertyAssetResult' + l,'getPropertyRetry' + l,'POST',attr_gets,propertyAssetCreate), #getPropertyAsset, if failed, try again by entering pin.. 
    
    # CALL TO CHECK IF SUCCESSFULL
    getPropertyRetry = MakeHttpRequest('getPropertyRetry' + l,'getPropertyAssetRetry' + l,'failure' + l,'POST',[{'key':'retry','value':'1'},{'key':'pk','value':'{{trigger.parent.parameters.pk}}'}],propertyAssetCreate),
    PropertyAssetResponse = SplitBasedOn('getPropertyAssetResult' + l,'unclear_if_succeeded' + l,http_check),    
    PropertyAssetRetry = SplitBasedOn('getPropertyAssetRetry' + l,'unclear_if_succeeded' + l,http_check_retry),  

    # REDO FIELD FLOW
    updatefieldvars = SetVariables('updateVars_field' + l,'redo' + l,updateVar_field),
    redo = SendMessage('redo' + l,'share_location' + l,'',texts('redo',l)),

    # ADD EST.SIZE AND PIN
    size,*x =Send_Reply_Split(l,'est_size' + l,'leave_silently','leave_silently','enter_pin' + l,texts('est_size',l),[],split_size_var,1800,''), # we reading something else, lets check what in the backend..
    pin,*x =Send_Reply_Split(l,'enter_pin' + l,'leave_silently','leave_silently','getPropertyAsset' + l,texts('enter_pin',l),[],split_pin_var,1800,''), # we reading something else, lets check what in the backend..

    # miscellaneous with language attr
    success = SendMessage('success' + l,'','',texts('success',l)), # exit to parent flow and start again
    failure = SendMessage('failure' + l,'enter_pin' + l,'',texts('failure',l)),
    unclear_success = SendMessage('unclear_if_succeeded' + l,'enter_pin' + l,'',texts('unclear_if_succeeded',l)),
    exit = SendMessage('exit' + l,'','',texts('exit',l)), # exit to parent flow and start again
    change_user = SendMessage('set_user' + l,'','',texts('exit',l)), # exit to parent flow and start again

    return *off_online,*share,*name,*setfieldvars,*updatefieldvars,*break_loop,*gps_issue,*list_registered,*min_3,*pin,*size,*exit,*change_user,*getFieldCheck,*getPropertyAsset,*PropertyAssetResponse,*PropertyAssetRetry,*getPropertyRetry,*success,*failure,*redo,*unclear_success

def RequestView(l):
    '''
        issue with loop to get url if image is still being created (on repetitive call, viewAsset.parsed.url is not updated.)
    '''
    url = '{{{}widgets.{}.parsed.url{}}}'.format('{','viewAsset' + l,'}')
    # HTTPS VIEW PROPERTY ASSET ATTRIBUTES
    attr_gets = [
        {'key':'phone', 'value': '{{trigger.parent.parameters.phone}}'},
        {'key':'org','value':'{{trigger.parent.parameters.org}}'},
        {'key':'pk','value':'{{trigger.parent.parameters.pk}}'},
        {'key':'status','value':'{{trigger.parent.parameters.status}}'},
        {'key':'pin','value':'{{{}widgets.{}.inbound.Body{}}}'.format('{','pending_asset' + l,'}')},
    ]

    setUrl = [
       {'key':'url','value': url},
       {'key':'count','value': '{{flow.variables.count | plus: 1}}'},
       {'key':'prop_stat','value':  '{{{}widgets.{}.parsed.prop_stat{}}}'.format('{','viewAsset' + l,'}')},
    ]

    follow_up = [ # show image if available and new, otherwise show wait message
        { 'next': 'pending_asset' + l, 'friendly_name': 'image_unavailable', 'type': 'equal_to', 'value': 1, 'argument': '{{flow.variables.url}}'},
        { 'next': 'break_' + l, 'friendly_name': 'image_unavailable', 'type': 'equal_to', 'value': 0, 'argument': '{{flow.variables.url}}'},
        { 'next': 'view_prop_asset' + l, 'friendly_name': 'image_available', 'type': 'not_equal_to', 'value': 0, 'argument': '{{flow.variables.url}}'},
    ]
    
    split_view_var = '{{{}widgets.{}.inbound.Body | downcase {}}}'.format('{','view_prop_asset' + l,'}') # listen if any response has been done, lowercase responds

    split_view = [
        { 'next': 'wait' + l, 'friendly_name': 'continue', 'type': 'equal_to', 'value':'add point', 'argument': split_view_var},
        { 'next': 'wait' + l, 'friendly_name': 'continue', 'type': 'equal_to', 'value': 'edit', 'argument': split_view_var},
        { 'next': 'setService' + l, 'friendly_name': 'continue', 'type': 'equal_to', 'value': 'score', 'argument': split_view_var},
        { 'next': 'setService' + l, 'friendly_name': 'continue', 'type': 'equal_to', 'value': 'croptag', 'argument': split_view_var},
        ]

    setService = [
        {'key':'service','value':split_view_var},
    ]

    # api will call a new image to be made, however it can already be available (previous call) so we 
    getAsset = MakeHttpRequest('viewAsset' + l,'setUrl' + l,'error','POST',attr_gets,propertyAssetView),
    setUrl = SetVariables('setUrl' + l,'follow_up' + l,setUrl),
    followUp = SplitBasedOn('follow_up' + l,'break_' + l,follow_up),
    break_ = SplitBasedOn('break_' + l,'wait' + l,[{ 'next': 'error', 'friendly_name': 'check_to_often', 'type': 'greater_than', 'value': 3, 'argument': '{{flow.variables.count}}'}]), 

    pending,*x =Send_Reply_Split(l,'pending_asset' + l,'viewAsset' + l,'viewAsset' + l,'viewAsset' + l,texts('pending_asset',l),[],split_view_var,180,''), #pending asset, request pin

    wait,*x =Send_Reply_Split(l,'wait' + l,'viewAsset' + l,'viewAsset' + l,'viewAsset' + l,texts('wait',l),[],split_view_var,20,''), # wait 20 seconds..
    view,*x =Send_Reply_Split(l,'view_prop_asset' + l,'leave_silently','try_again' + l,'leave_silently',texts('view_prop_asset',l),split_view,split_view_var,120,url), # add options (edit + add point)
    setService = SetVariables('setService' + l,'leave_silently',setService),
    try_again = SendMessage('try_again' + l,'','',texts('try_again',l)),

    pending_score = SendMessage('pendingScore' + l,'','',texts('pending_score',l)),

    # request edit (sends prop token to contract (to be destroyed), request nodes to assess new data, investigate score card (to increase status), and or newly added points..

    return *getAsset,*wait,*view,*setUrl,*break_,*setService,*pending,*followUp,*try_again,*pending_score

def Property():
    try:
        print('PROPERTY FLOW')
        setParent_var = [
            { 'next': 'off_online_EN', 'friendly_name': 'unreg', 'type': 'equal_to', 'value': 'unreg_EN', 'argument': '{{trigger.parent.parameters.status}}' + "_" + '{{trigger.parent.parameters.l}}'}, # get language set from parent flow.
            { 'next': 'viewAsset_EN', 'friendly_name': 'unreg', 'type': 'equal_to', 'value': 'unreg_EN', 'argument': '{{trigger.parent.parameters.status}}' + "_" + '{{trigger.parent.parameters.l}}'}, # get language set from parent flow.
            { 'next': 'pendingScore_EN', 'friendly_name': 'pending', 'type': 'equal_to', 'value': 'pending_EN', 'argument': '{{trigger.parent.parameters.status}}' + "_" + '{{trigger.parent.parameters.l}}'}, # get language set from parent flow.

            { 'next': 'off_online_TN', 'friendly_name': 'reg', 'type': 'equal_to', 'value': 'reg_TN', 'argument': '{{trigger.parent.parameters.status}}' + "_" + '{{trigger.parent.parameters.l}}'}, # get language set from parent flow.
            { 'next': 'viewAsset_TN', 'friendly_name': 'reg', 'type': 'equal_to', 'value': 'reg_TN', 'argument': '{{trigger.parent.parameters.status}}' + "_" + '{{trigger.parent.parameters.l}}'}, # get language set from parent flow.
            { 'next': 'pendingScore_TN', 'friendly_name': 'pending', 'type': 'equal_to', 'value': 'pending_TN', 'argument': '{{trigger.parent.parameters.status}}' + "_" + '{{trigger.parent.parameters.l}}'}, # get language set from parent flow.

        ]

        flow = { "states": [ 
                trigger('Trigger','prop_readResponse','','prop_readResponse','prop_readResponse'), # trigger, SUBFLOW connected  
                SplitBasedOn('prop_readResponse','error',setParent_var), 

                # SUBFLOW SPLIT INTO CREATE AND VIEW
                # -------
                # CREATE (NEW REGISTRATION)

                # -- loop
                # Please share a location in - or close next to - the first field.
                # Good, give a name to the field. (after 3x -> Type done once you have registered the entire property.)
                # -- end loop

                # Well done. These are the registered fields: * OK1: (52.3726919,4.8814964) * OK2: (52.3726326,4.8815565) * OK3: (52.3726326,4.8815565) Type continue to create the property asset, type remove + field name to remove a field.
                # if continue: 
                #    Please what is the total size of your property in acres?
                #    Ok. Please give your 4 digit pincode.

                # if remove + field:
                #    Done. we removed {fieldname} from the list.

                # miscellaneous not language specific
                SendMessage('error','','','Ues, Sorry something has gone wrong. Please try again.'),
                SendMessage('leave_silently','','',''),
                # this is never called, just makes sure the widgets are duplicated during json builder.
                *CollectCreate('_EN'),
                *CollectCreate('_TN'),
                *RequestView('_EN'),
                *RequestView('_TN'),
                *OfflineMode('_EN'),
                *OfflineMode('_TN'),
                ]
        } 

        jsonDump = packaging(flow)
        validate(jsonDump,'nila_subflow_property',VERSION)
        commit(jsonDump,'FW3a373f0f82aabe0033e6c6be2abc22ac',VERSION)
    
    except TwilioRestException as e: 
        print(e.details)
        print('----------THIS IS AN ERROR --------------')
        return "Error"

if __name__ == "__main__":
   Property()