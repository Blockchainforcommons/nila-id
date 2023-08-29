import express from 'express';
var AWS = require('aws-sdk');
import { Request, Response } from 'express';
import { ethers } from "ethers";
import {
    core,
    EthStateStorage,
    CircuitId,
    CredentialRequest,
    ZeroKnowledgeProofRequest,
    CredentialStatusType,
    IIdentityWallet,
  } from "@0xpolygonid/js-sdk";

import { 
    createStorageCredential,
    createStorageCredentialRequest, 
  } from './credentials/storage';
import {
  createOriginCredential
  } from './credentials/origin' 

import {
    initInMemoryDataStorageAndWallets,
    initCircuitStorage,
    initProofService,
  } from "./walletSetup";

const qr = require('qr-image');
const fs = require('fs');
var path = require('path');
const { Network, Alchemy } = require("alchemy-sdk");

const rhsUrl = process.env.RHS_URL as string;
require('dotenv').config();

var lambda = new AWS.Lambda({ apiVersion: '2015-03-31', region: 'ap-south-1'});
var ddb = new AWS.DynamoDB({apiVersion: '2012-08-10', region: 'ap-south-1'});
var s3 = new AWS.S3({apiVersion: '2006-03-01', region: 'ap-south-1'});

AWS.config.update({
    accessKeyId: process.env.ACCESSKEYID,
    secretAccessKey: process.env.SECRETACCESSKEY,
    region: 'ap-south-1',
});

/* 
API routers to issue off and on-chain credentials 

  APIS: 
    /*  
    info: Generic Api to test node
    
    /IssueStorage 
      info: Create a Storage MTPV2 certificate
      - request:
          - JWT/pincode to recover wallet key (ISSUER)
          - Croptype (required)
          - Grade and Quantity (required)
          - Variety,Aadhar,Condition (optional)
          - user DID
      - steps
          - recover key
          - init Wallets and Storage
          - select credential by croptype
          - create credential
          - publish to blockchain
          - return credential id & credentials
    
    /ProofStorage
      info: Generate Proof of a Storage MTPV2 certificate
      - request:
          - JWT/pincode to recover wallet key (USER)
          - VC id
          - VC credentials
      - steps
          - recover key
          - init Wallets and Storage
          - select ProofRequest
          - generateProof
          - return QR with proofMTP
    
    /IssueProofOrigin
      info: Request onchain origin certificate and generate SIG proof of the certificate
      - request:
          - JWT/pincode to recover wallet key (USER)
      - steps:
          - recover key
          - discover wallet has updated Chitta tokens and metadata
          - request onchain certificate
          - select ProofRequest
          - generateProof
          - return QR with ProofSig

*/

const app = express();
const port = 8080;
const bodyParser = require('body-parser');

app.use(bodyParser.json()); // support json encoded bodies
app.use(express.urlencoded({ extended: true })); // support encoded bodies
app.use(express.static('schemas'))
app.use(bodyParser.json());

async function init(){
  let { dataStorage, credentialWallet, identityWallet } = await initInMemoryDataStorageAndWallets();
    const circuitStorage = await initCircuitStorage();
    const proofService = await initProofService(
        identityWallet,
        credentialWallet,
        dataStorage.states,
        circuitStorage
    );
    
    return {identityWallet,credentialWallet,dataStorage,proofService,circuitStorage}
}

app.post('/IssueStorage', async (req: Request, res: Response) => {

    // API CALLED IN WABA FLOW: handler.Store
    
    // parse req
    const input = req.body
    console.log(input)
    const phone = input.phone.split(':')[1]
    const userDID = input.did
    const aadhar = input.aadhar
 
    //init
    let { identityWallet, credentialWallet, dataStorage, proofService, circuitStorage} = await init()

    // recover wallet seed (DEMO: Users have not been transferred to Polygon )
    var params = {
      TableName: 'polygon_aes',
      Key: { 'phoneNumber': {'S': phone} },
      ProjectionExpression: 'SK,BabyJubJub,BusinessName'
    }
    var wallet_seed = await ddb.getItem(params).promise()

    // generate the babyjubjub key from private key
    // TODO: FIND SOLUTION IN JS, TAKE PRESET

    let utf8Encode = new TextEncoder();
    const seedPhraseUser: Uint8Array = utf8Encode.encode(wallet_seed.Item.BabyJubJub.S);  

    const { did: issuerDID, credential: issuerAuthBJJCredential } = await identityWallet.createIdentity({
        method: core.DidMethod.Iden3,
        blockchain: core.Blockchain.Polygon,
        networkId: core.NetworkId.Mumbai,
        seed: seedPhraseUser,
        revocationOpts: {
        type: CredentialStatusType.Iden3ReverseSparseMerkleTreeProof,
        id: 'https://rhs-staging.polygonid.me'
        }
    });
    
    // prepare and issue credential
    const credentialRequest : any = createStorageCredential(userDID,input);
    console.log('issdid', credentialRequest)
    const credential = await identityWallet.issueCredential(
        issuerDID,
        credentialRequest
    );
    // cache credential
    await dataStorage.credential.saveCredential(credential);

    // storagecreds are MTVP, so have to be published onchain
    await identityWallet.publishStateToRHS(issuerDID, rhsUrl);

    // restore issuer merkle tree
    // TODO, restore tree

    // make sure to add credentials to up-to-date merkle tree
    const add = await identityWallet.addCredentialsToMerkleTree(
      [credential],
      issuerDID,
    );

    // publish state
    const ethSigner = new ethers.Wallet(
      wallet_seed.Item.SK.S,
      (dataStorage.states as EthStateStorage).provider
    );

    const txId = await proofService.transitState(
      issuerDID,
      add.oldTreeState,
      true,
      dataStorage.states,
      ethSigner
    );
    console.log(txId);
    
    // send credential to user to generate proof
    console.log('TWILIO',process.env.ACCOUNT_SID, process.env.AUTH_TOKEN)
    const client = require('twilio')(process.env.ACCOUNT_SID, process.env.AUTH_TOKEN);
    client.studio.v2.flows('FW1327ad94088d2b26f52988905062b4c6')
      .executions
      .create({
        to: `whatsapp:${input.user_phone}`,
        from:"whatsapp:+13478481380",
        parameters: JSON.stringify({
          'id': '300',
          'ct': input.ct,
          'quantity': input.store_amount,
          'grade': input.store_grade,
          'businessName': wallet_seed.Item.BusinessName.S,
          'credentialRequest': '',//credentialRequest, 
          'issuerDID': issuerDID,
      })})
      .then((execution: any) => console.log(execution.sid));

    // return success
    return res.send('success')

});

app.post('/ProofStorage', async (req: Request, res: Response) => {

    // API CALLED IN WABA FLOW: handler.Proof

    // receive input (device id, credentialRequest, userDID)
    const input = req.body
    const phone = input.phone.split(':')[1]
    const aadhar = input.aadhar
    const issuerDID = input.issuerDiD // postman: string, WA: core.did
    const credentialRequest = input.credentialRequest

    // initialize wallets
    let { identityWallet, credentialWallet, dataStorage, proofService, circuitStorage} = await init()

    // recover wallet seed (DEMO: Users have not been transferred to Polygon )
    var params = {
      TableName: 'polygon_aes',
      Key: { 'phoneNumber': {'S': phone} },
      ProjectionExpression: 'SK,BabyJubJub'
    }
    var wallet_seed = await ddb.getItem(params).promise()

    let utf8Encode = new TextEncoder();
    const seedPhraseUser: Uint8Array = utf8Encode.encode(wallet_seed.Item.BabyJubJub.S);  

    const { did: userDID, credential: authBJJCredentialUser } = await identityWallet.createIdentity({
        method: core.DidMethod.Iden3,
        blockchain: core.Blockchain.Polygon,
        networkId: core.NetworkId.Mumbai,
        seed: seedPhraseUser,
        revocationOpts: {
        type: CredentialStatusType.Iden3ReverseSparseMerkleTreeProof,
        id: 'https://rhs-staging.polygonid.me'
        }
    });

    // create standardized proofrequests
    // get request for MERKLE TREE proof
    const proofReqSig: ZeroKnowledgeProofRequest = createStorageCredentialRequest(
      // CircuitId.AtomicQueryMTPV2,
      credentialRequest
    );

    // generate proof
    const { proof, pub_signals } = await proofService.generateProof(
    proofReqSig,
    userDID
    );

    console.log('proof', proof)
    console.log('pub_signals', pub_signals)

    const proof_pub_json = JSON.stringify({
        'proof': proof,
        'pubsignals': pub_signals,
    })
    console.log('proof_pub_json', proof_pub_json)

    // link that let verifiers know: 
    //  - issuer
    //  - query and criteria
    //  - standard set of queries are available.

    // create the qr codes and return
    var addr = process.env.URI
    var zkProof = `${addr}/verify?text=${aadhar}${proof_pub_json}` 
    console.log('zkproof', zkProof)
    var code = qr.image(zkProof, { type: 'svg' });
    code.pipe(fs.createWriteStream('qr.svg'));

    // store image on S3 bucket
    var filename = 'qr.svg';
    await s3.upload({
      Bucket: process.env.S3BUCKET, 
      Key: filename, 
      Body: fs.readFileSync('qr.svg'),
      ACL: 'public-read',
      ContentType: 'image/jpg',
    }).promise()

    // return url of QR image
    res.send(JSON.stringify({
      'url': `https://${process.env.S3BUCKET}.s3.ap-south-1.amazonaws.com/${filename}`
    }))
});

app.post('/IssueProofOrigin', async (req: Request, res: Response) => {
  // API CALLED IN WABA FLOW: SUPPLY.py
  let input = req.body
  let pk = input.pk
  let phone = input.phone.split(':')[1]
  console.log('SISFJWOIDFJOSD', phone)

 // recover wallet seed (DEMO: Users have not been transferred to Polygon )
 var params = {
   TableName: 'polygon_aes',
   Key: { 'phoneNumber': {'S': phone} },
   ProjectionExpression: 'SK,BabyJubJub'
 }
 var wallet_seed = await ddb.getItem(params).promise()

// initiate provider (use superlib of ethers because of ease to fetch metadata)
 const provider = new Alchemy({
    apiKey: process.env.PROVIDER_API_KEY,
    network: Network.maticmum, // Replace with your network.

 });
 // find recent token deposits on user address from token minter
 const blocknmb = await provider.core.getBlockNumber()
 console.log('blocknmb', blocknmb)
 const histblock = blocknmb - ((60*60*24*21) / 12.06) // doesnt have to be precise, current block minus estimated blocks by blocktime

 const txs = await provider.core.getAssetTransfers({
  fromBlock: '0x' + Math.round(histblock).toString(16).toUpperCase(), // find block of about 3 weeks ago.
  fromAddress: process.env.FIELD_ACTIVITY_MINT_CONTRACT,
  toAddress: pk,
  excludeZeroValue: false,
  category: ["erc20"],
});

 // check for recent tx from our crop token mint contact ( not sufficient - can also be seperate cultivations!!)
  if (txs.transfers.length != 0){
  // find metadata to create origin credentialRequest
  // chitta sensing network is not available on Polygon yet.
  let md = {
    ct: 'paddy',
    hrvst: '08/11/2023',
    yield: 15,
    lat: 12.543117,
    lng: 79.326588,
    size: 3,
    fields: 6,
    other: null
  } // dummy metadata

  // propose contract to issue credentialRequest
  const credentialRequest : any = createOriginCredential(userDID,input,md);

  // generate proof 

  // return origin proof QR and storage request QR
 }
 else {
  // queue request for field analysis to the chitta remote sensing node
  var lambda_params = {
    FunctionName: 'arn:aws:lambda:ap-south-1:867185477215:function:Chitta-Sensing-stage-GETLABEL', // the lambda function we are going to invoke
    InvocationType: 'RequestResponse',
    LogType: 'Tail',
    Payload: JSON.stringify({
      'phone': input['phone'].split(':')[1], 
      'pk': pk,
      }),
  };
  lambda.invoke(lambda_params).promise()
  // return flow to wait for the sensing node to finish (unclear how long, depends on queue)
  return res.send({ 'res': 0 })
 }

 /*
 // return r
 console.log('pk', pk)
 const latestBlock = await provider.core.getBalance(pk,"latest");
 console.log('balance', latestBlock)

 // request credential from onchain issuer
 const tokenContract = new ethers.Contract(process.env.CONTRACT_ADDRESS :, tokenAbi, connection);
var signer = new ethers.Wallet(wallet_seed.Item.SK.S, connection);
const txSigner= tokenContract.connect(signer);
// where to put the credentialRequest
const transaction = await txSigner.transfer(to,address,amount)
const data = Promise.resolve(transaction)
data.then(value => {

    console.log(value)

});
*/




 // request account balance 

  // 
  /*
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
  */

  // ping the account for recent token transactions and underlying metadata
  // if none, request the remote sensing node for a update, return and repeat (outside the 30sec request time)

  // if available, request onchain issue

  


});
  

app.listen(port, () => console.info(`listening on port ${port}!`));