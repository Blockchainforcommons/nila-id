def trigger(name,incomingMessage,incomingCall,incomingRequest,subflow): 
  widget = { 'name': name, 'type': 'trigger', "properties": {"offset": { "x": 0, "y": 0 }},
    'transitions': [ 
      { 'next': incomingMessage, 'event': "incomingMessage"},
      { 'event': "incomingCall" },
      { 'next': incomingRequest, 'event': "incomingRequest"},
      { 'next': subflow, 'event': "incomingParent"},
    ]}
  print('Trigger')
  return widget

def SendMessage(name, nextSent, nextFailed, body, url):
  print(bool(nextFailed))
  if bool(nextSent) : send = {'next': nextSent, 'event': "sent"} 
  else: send = { 'event': "sent"}
  if bool(nextFailed) : failed = {'next': nextFailed, 'event': "failed"} 
  else: failed = { 'event': "failed"}
  widget = { 
    'name': name, 
    'type': 'send-message', 
    'transitions': [ 
        send,
        failed,
        ], 
        'properties': { 
          'service': "{{trigger.message.InstanceSid}}", 
          'channel': "{{trigger.message.ChannelSid}}",
          'from': '{{flow.channel.address}}',
          "offset": { "x": 0, "y": 0 },
          'body': body,
          'media_url': url if url else '',
    }}
  print('SendMessage', widget)
  return widget

def SendWaitForReply(name,nextIncoming,nextTimeout,nextFailure,body,waitingTime): 
  if bool(nextIncoming) : incoming = {'next': nextIncoming, 'event': "incomingMessage"} 
  else: incoming = { 'event': "incomingMessage"}
  if bool(nextTimeout) : timeout = {'next': nextTimeout, 'event': "timeout"} 
  else: timeout = { 'event': "timeout"}
  if bool(nextFailure) : failed = {'next': nextFailure, 'event': "deliveryFailure"} 
  else: failed = { 'event': "deliveryFailure"}
  widget = { 'name': name, 'type': 'send-and-wait-for-reply', 
        'transitions': [ 
          incoming,
          timeout,
          failed,
        ], 
        'properties': { 
          'service': "{{trigger.message.InstanceSid}}", 
          'channel': "{{trigger.message.ChannelSid}}",
          "offset": { "x": 0, "y": 0 },
          'from': '{{flow.channel.address}}',
          'body': body, #{{flow.data.message}}
          'timeout': waitingTime #"3600"
        }}
  print('SendWaitForReply')
  return widget

def SetVariables(name, nextWidget, variables):
    values = []
    for variable in variables:
        var = {
            'value': variable['value'],
            'key': variable['key']
        }
        values.append(var)

    widget = {
        'name': name,
        'type' : "set-variables",
        "transitions": [{ "next": nextWidget, "event": "next"}],
        "properties": { "variables": values ,"offset": { "x": 0, "y": 0 }}
    }
    return widget

def SplitBasedOn(name,nextNoMatch,conditions):
    Transitions = []
    for condition in conditions:
          cond = { 
              'next': condition['next'], 
              'event': "match", 
              'conditions': [{ 
                  "friendly_name": condition['friendly_name'], 
                  "arguments": [condition['argument']],
                  "type": condition['type'],
                  "value": condition['value']
                }]
          }
          Transitions.append(cond)
    Transitions.append({'next': nextNoMatch, 'event': "noMatch" })  
    print(Transitions)
    widget = {
      'name': name,
      'type' : "split-based-on",
      "properties": {
        "input": conditions[0]['argument'],
        "offset": { "x": 100, "y": 200 }
        },
      'transitions': Transitions
    }
    print('SplitBasedOn')
    return widget

def Send_Reply_Split(l,name,nextTimeout,nextFailure,nextNoMatch,body,conditions,value_conditions_check,waitingTime,url):
  send = SendWaitForReply(name,name + '_split',nextTimeout,nextFailure,body,waitingTime)

  send['properties']['media_url'] = url
  print("URL", url)
  print("MEDIA URL", send)
  standard_conditions = [
    { 'next': 'exit' + l, 'friendly_name':'remove_service', 'value':'cancel,exit,close', 'type':'matches_any_of', 'argument':value_conditions_check},
    { 'next': 'set_user' + l, 'friendly_name':'change_user', 'value':'change,edit,swap', 'type':'matches_any_of', 'argument':value_conditions_check},
    ]
  conds = standard_conditions + conditions
  split = SplitBasedOn(name + '_split',nextNoMatch,conds)
  return send,split

def MakeHttpRequest(name,nextSuccess,nextFailed, method, parameters, url):
  if bool(nextFailed) : failed = {'next': nextFailed, 'event': "sent"} 
  else: failed = { 'event': "failed"}
  print(parameters)
  widget = {
    'name': name,
    'type' : "make-http-request",
    'transitions': [
        { 'next': nextSuccess, 'event': "success"},
        { 'next': nextFailed, 'event': "failed"},
    ],
    'properties': {
        'method': method,
        "properties": {"offset": { "x": 0, "y": 0 }},
        "Content_type": "application/json",
        "parameters": parameters,
        "url": url
        }
    }
  print('MakeHttpRequest')
  return widget

def SubFlow(name,flow_sid,parameters):
  print(parameters)
  widget = {
      "name": name,
      "type": "run-subflow",
      "transitions": [
        {
          "event": "completed"
        },
        {
          "event": "failed"
        }
      ],
      "properties": {
        "flow_sid": flow_sid,
        "flow_revision": "LatestPublished",
        "offset": { "x": 0, "y": 0 },
        "parameters": parameters,
      }
    },
  return widget