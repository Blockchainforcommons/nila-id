# Storage and Origin certificate issuance using WhatsApp

This is a experimental implementation of polygon account abstraction and polygon ID for the Polygon DevX EMEA Hackathon X, performed in august 2023 by the Nila team based in Amsterdam, the Netherlands.

## Goal

The challenge is too build an off-chain and on-chain issuer and user wallet that can be solely operated from a WhatsApp environment with a WABA account. To reach our Nila customers, web3 UX is too difficult to use. Please read the attached presentation or Buildl description for more business challenge related information.

There are three main components in this application:

1. The chatbot flows using a custom made json-flow builder for front-end communication
2. The nodeJS server providing 3 APIs to request credentials and generate proof
3. additional Python Lambda functions to run the chatbotflow (webhooks,userKYC,etcetera.)

## Languages

Our users in general are not proficient in english. Our chatbot is created to allow any minor language to be hardcoded into the UI. for the nila-id experiment we only used english. Others versions of the chatbot are also responding in Tamil, Kannada, Telugu and Hindi.

## Requirements
1. NodeJS => 18.x
2. Python => 3.9
3. Typescript => 5.1.x
4. npm => 9.x.x
5. docker => 20.x
6. serverless => 3.33
7. ethereum provider account (e.g Alchemy)

## accounts
7. a verified META WhatsApp for business (WABA)
8. a twillio account to launch the custom JSON flow
9. AWS account for S3 and dynamoDB (you can choose other providers at your convenience)
10. a phone number at your disposal with an allowed country prefix; e.g +1 

## environment variables:

```bash
# reverse hash service url
RHS_URL="https://rhs-staging.polygonid.me" 
# state v2 contract address in the mumbai network
ORIGIN_CERTS_CONTRACT="0x134B1BE34911E39A8397ec6289782989729807a4"
# Nila crop token minter in the mumbai network (check latest version)
FIELD_ACTIVITY_MINT_CONTRACT="0x134B1BE34911E39A8397ec6289782989729807a4"
# path to the circuits folder
CIRCUITS_PATH="./circuits" 
# url to polygon mumbai network rpc node
RPC_URL="https://rpc-mumbai.maticvigil.com" 
# provider api keys

# if you use another provider then alchemy, please change the ethers.providers.AlchemyProvider to your provider
PROVIDER_API_KEY=<PROVIDER_API_KEY>

#AWS KEYS
ACCESSKEYID=<AWS_IAM_ACCESS_KEY>
SECRETACCESSKEY=<AWS_IAM_SECRET_ACCESS_KEY>
REGION=<AWS_REGION>
ENDPOINT=<AWS_ENDPOINT>
S3BUCKET=<S3_BUCKET_FOR_CREATED_QR_IMAGES>

# Twilio 
ACCOUNT_SID=<TWILLIO_ACCOUNT_SID>
AUTH_TOKEN=<TWILLIO_AUTH_TOKEN>
# url
URI=<NODEJS_SERVER_URI>
```

## Invoke a flow

### registration is mandatory
1. 'Say hi :wave:' to the WABA phone number you registered with.
2. Register your property using the prop flow.

### for the nila-id ORIGIN certification
3. Type 'Sell' to invoke the origin certification 
4. if a cultivation and a harvest event are detected, the origin certificate and proof QR will be send to the registered WhatsApp user. 
5. the proof QR can be shared, send to anyone interested.
6. Answer the storage questions.
7. if in store or will be stored, let the storage manager scan the storage QR.

### for nila-id STORAGE certification

-- storage manager flow:

8. Scan the storage QR 
9. enter quantity
10. enter grade
11. receive the updated storage account root id.

-- user flow: 

12. receive result of scan, verify quantity and grade
13. if confirmed, the storage certificate and proof QR will be send to the registered WhatsApp user

## Proof limitations

Proof can only be generated for 2 query types: 

    Origin:
    - Quantity of Type ( 
        return crop type (signals a crop of this type has been cultivated by the userDID)
    )
    Storage:
    - Stored_at_issuer_location (
        return user aadhar (signals user produce is stored in issuer storage.)
    )

In the future options will be given to generate additional proofs. See the Dorahack BUIDL description for more possible credentials.

Support for cross and mixing proofs, such as 'crop_type on location x' or 'aadhar with x amount' is wanted.

## Authentication

APIs will be limited by a authentication id given in the env file. The id will be hardcoded in the chatbot flow. This means Nila-ID is open to several attack vectors:

    - Twilio and Meta potentially have access to the id
    - The phone number and the authentication id are the 

Future versions of the Nila Account Abstraction will focus on eliminating these threads.

## Origin Schema


## Storage Schemas


## API description

## Credential Storage (file storage)

Origin Credentials are not stored locally in this version of nila-id. Even though a credential schema has a expiration date. Credentials are generated for one-time proof. 

Storage Credentials are not stored locally in this version of nila-id. Storage credentials will be stored on-chain in future versions, as branches in a storage merkle tree.

## Limitations for prod stage

* As the Nila-sensing-network (formally chitta) is not available on Polygon, we are not able to create production-ready origin certificates.

* It is impossible for now to verify multiple queries at once, this makes the UX very complex and cumbersome.

* The UX provides a lot of QR codes to the user. It is likely he will get confused, in next version, the use of shorturls might be an improvement over qr images.

## How to initialize the chatbot:
1. Get an account at Twilio 
2. Sign-up for WABA messaging
3. Update the env file with your account sid and secret 
8. create the messaging flows, for each flow (handler,supply,etc) type: 
    ```bash
    python [file_name].py
    ```
4. Purchase a phone number and link it to the Whatsapp Messaging
5. Create a AWS account 
9. You are ready to go!
4. Pu


## How to run the Nila-JS-Node:
1. Clone this repository:
    ```bash
    git clone https://github.com/Blockchainforcommons/nila-id
    ```
2. Update the env file 
3. Deploy onchain issuer contract. Use these next states:
    * For mumbai network: `0x134B1BE34911E39A8397ec6289782989729807a4`
4. Run 
    ```bash
    npm start
    ```
5. Open https://localhost:8080 in your web browser
6. Please download Ngrok or a similar to ingress the localhost, 
7. add the Ngrok uri to your chatbot env file
8. update the apis endpoints in the flow, for each flow (handler,supply,etc) type: 
    ```bash
    python [file_name].py
    ```
9. You are ready to go!

## Tested on:
1. MacBook M1, OS: Monterey 12.4
