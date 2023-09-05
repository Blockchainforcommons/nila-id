import express from 'express';
var AWS = require('aws-sdk');
import { Request, Response } from 'express';
import { ethers } from "ethers";
import {
    core,
    EthStateStorage,
    ZeroKnowledgeProofRequest,
    CredentialStatusType,
    IIdentityWallet,
    ProofService,
    KmsKeyType,
    IssuerData,
    KMS,
    AbstractPrivateKeyStore,
    BjjProvider,
  } from "@0xpolygonid/js-sdk";

import { 
    createStorageCredential,
    createStorageCredentialRequest, 
  } from './credentials/storage';
import {
  createOriginCredential,
  createOriginCredentialRequest, 
  } from './credentials/origin' 

import {
    initInMemoryDataStorageAndWallets,
    initCircuitStorage,
    initProofService,
    initDataStorage,
    initCredentialWallet,
    initIdentityWallet,
  } from "./walletSetup";
import { PrivateKey } from 'aws-sdk/clients/acm';

const QR = require('qrcode')
const fs = require('fs');
const { Network, Alchemy } = require("alchemy-sdk");
const rhsUrl = process.env.RHS_URL as string;
require('dotenv').config();

var lambda = new AWS.Lambda({ apiVersion: '2015-03-31', region: 'ap-south-1'});
var ddb = new AWS.DynamoDB({apiVersion: '2012-08-10', region: 'ap-south-1'});
var s3 = new AWS.S3({apiVersion: '2006-03-01', region: 'ap-south-1'});

// initiate provider
const provider = new Alchemy({
  apiKey: process.env.PROVIDER_API_KEY,
  network: Network.MATIC_MUMBAI, // Replace with your network.
  })
  
// config AWS 
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

async function init(phone : string, SK: string){
  console.log('first time issuer, create identity')
  const gen_new_key = require("@0xpolygonid/js-sdk/dist/cjs/kms/provider-helpers");

  const circuitStorage = await initCircuitStorage();
  let { dataStorage, credentialWallet, identityWallet } = await initInMemoryDataStorageAndWallets();
    const proofService = await initProofService(
        identityWallet,
        credentialWallet,
        dataStorage.states,
        circuitStorage
    );

  // create new babyjubjub key
  const key = (0, gen_new_key.getRandomBytes)(32)

  // create new identity 
  const options = {
    method: core.DidMethod.PolygonId,
    SK,
    blockchain: core.Blockchain.Polygon,
    networkId: core.NetworkId.Mumbai,
    seed: key,
    revocationOpts: {
      type: CredentialStatusType.Iden3ReverseSparseMerkleTreeProof,
      id: 'https://rhs-staging.polygonid.me'
    }
  }
  const { did: DID, credential: issuerAuthCredential } = await identityWallet.createIdentity(options); 
  console.log('new user', DID, issuerAuthCredential) //c27d4f99b2c94404a48ea64ffce5bf3e

  // custom implementation of seed generation from private key

  // store new key in persistent storage
  var updateIdentity = {
    TableName: 'polygon_aes',
    Key: { 'phoneNumber': {'S': phone} },
    UpdateExpression: 'set BabyJubJub= :bj',
    ExpressionAttributeValues: {
      ':bj':  { 'B' : key},
    },
    ReturnValues: "ALL_NEW",
  }
  await ddb.updateItem(updateIdentity).promise()

  return {identityWallet,credentialWallet,proofService,dataStorage,DID,issuerAuthCredential}
}

async function instantiate(phone : string, SK: string, key: string){
  // instantiate is similar to init except for the BJJ key generation.
  console.log('instantiate, user found')
  const gen_new_key = require("@0xpolygonid/js-sdk/dist/cjs/kms/provider-helpers");

  const circuitStorage = await initCircuitStorage();
  let { dataStorage, credentialWallet, identityWallet } = await initInMemoryDataStorageAndWallets();
    const proofService = await initProofService(
        identityWallet,
        credentialWallet,
        dataStorage.states,
        circuitStorage
    );

  // recover babyjubjub key
  let utf8Encode = new TextEncoder();
  const seed: Uint8Array = utf8Encode.encode(key); 

  // create new identity 
  const options = {
    method: core.DidMethod.PolygonId,
    SK,
    blockchain: core.Blockchain.Polygon,
    networkId: core.NetworkId.Mumbai,
    seed: seed,
    revocationOpts: {
      type: CredentialStatusType.Iden3ReverseSparseMerkleTreeProof,
      id: 'https://rhs-staging.polygonid.me'
    }
  }
  const { did: DID, credential: issuerAuthCredential } = await identityWallet.createIdentity(options); 
  return {identityWallet,credentialWallet,proofService,dataStorage,DID,issuerAuthCredential}
}

async function storePersist(phone : string,dataStorage : any,issuerDID: string, txId : string){
  // store the updated issuer identity and state
  var updateIdentity = {
    TableName: 'polygon_aes',
    Key: { 'phoneNumber': {'S': phone} },
    UpdateExpression: 'set credentials= :c, identities = :ids, idstate = :st, did = :dd',
    ExpressionAttributeValues: {
      ':c':  { 'S' : JSON.stringify(await dataStorage.credential.listCredentials())},
      ':ids':  { 'S' : JSON.stringify(await dataStorage.identity.getAllIdentities())},      
      ':dd':  { 'S' : issuerDID},
      ':st':  { 'S' : txId},

    },
    ReturnValues: "ALL_NEW",
  }
  await ddb.updateItem(updateIdentity).promise()
}

app.post('/IssueStorage', async (req: Request, res: Response) => {
    const client = require('twilio')(process.env.ACCOUNT_SID, process.env.AUTH_TOKEN);

    // API CALLED IN WABA FLOW: handler.Store
    
    // parse req
    const input = req.body
    console.log(input)
    const phone = input.phone.split(':')[1]
    const userDID = input.did
 
    // recover wallet seed (DEMO: Users have not been transferred to Polygon )
    var params = {
      TableName: 'polygon_aes',
      Key: { 'phoneNumber': {'S': phone} },
      ProjectionExpression: 'SK,BabyJubJub,BusinessName,did,credentials,identities'
    }
    var data = await ddb.getItem(params).promise()
    var data = data.Item

    console.log('data', data)

    // unknown issuer, return request to formal sign-up
    if(data === undefined){
      client.studio.v2.flows('FW1327ad94088d2b26f52988905062b4c6')
      .executions
      .create({
        to: `whatsapp:${input.user_phone}`,
        from:"whatsapp:+13478481380",
        parameters: JSON.stringify({
          'message': 'Please register first. Go to asknila.in and sign-up as a storage facility issuer.'
      })})
      return res.send('success')
    }
    // known issuer, load or init identity if wallet has been created.
    else if (typeof data.SK !== 'undefined') {
      // load or create new wallets and storage
      const { identityWallet, credentialWallet, proofService, dataStorage,DID,issuerAuthCredential } = typeof data.BabyJubJub === 'undefined' ? await init(phone,data.SK.S) : await instantiate(phone,data.SK.S,data.BabyJubJub.S)
      const issuerDID = DID
      
      // prepare and issue credential
      const credentialRequest : any = createStorageCredential(userDID,input);
      const credential = await identityWallet.issueCredential(
          issuerDID,
          credentialRequest
      );

      // cache credential
      await dataStorage.credential.saveCredential(credential);

      // storagecreds are MTVP, so have to be transited onchain
      await identityWallet.publishStateToRHS(issuerDID, rhsUrl);

      // make sure to add credentials to claims merkle tree
      const add = await identityWallet.addCredentialsToMerkleTree(
        [credential],
        issuerDID,
      );

      // publish state
      const signer = new ethers.Wallet(
        data.SK.S, 
        (dataStorage.states as EthStateStorage).provider
      );
      
      const txId = await proofService.transitState(
        issuerDID,
        add.oldTreeState,
        true,
        dataStorage.states,
        signer
      );
      console.log('txId',txId);
      // store the credentials, identity and tx id for the next time.
      await storePersist(phone,dataStorage,issuerDID.string(),txId)
      
      // send credential to user to generate proof
      console.log('TWILIO',process.env.ACCOUNT_SID, process.env.AUTH_TOKEN)
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
            'businessName': data.BusinessName.S,
            'credentialRequest': JSON.stringify('credentialRequest'), //credentialRequest, 
            'credential': JSON.stringify('credential'),
            'idW': JSON.stringify('add'),
            'txID': 'txId',
            'issuerDID': issuerDID.string(),
        })})
        .then((execution: any) => console.log(execution.sid));
    }        
  res.send('success!!!')
});

app.post('/ProofStorage', async (req: Request, res: Response) => {

    // API CALLED IN WABA FLOW: handler.Proof
    const client = require('twilio')(process.env.ACCOUNT_SID, process.env.AUTH_TOKEN);
    
    // parse req
    const input = req.body
    console.log(input)
    const phone = input.phone.split(':')[1]
    const aadhar = input.aadhar
    const issuerDID = input.issuerDID // postman: string, WA: core.did
    const credentialRequest = JSON.parse(input.credentialRequest)
    const credential = JSON.parse(input.credential)
    const txID = input.txID
 
    // recover wallet seed (DEMO: Users have not been transferred to Polygon )
    var params = {
      TableName: 'polygon_aes',
      Key: { 'phoneNumber': {'S': phone} },
      ProjectionExpression: 'SK,BabyJubJub,BusinessName,did,credentials,identities'
    }
    var data = await ddb.getItem(params).promise()
    var data = data.Item

    console.log('data', data)
  
    // unknown user, return request to formal field registration
    if(data === undefined){
      client.studio.v2.flows('FW1327ad94088d2b26f52988905062b4c6')
      .executions
      .create({
        to: `whatsapp:${input.user_phone}`,
        from:"whatsapp:+13478481380",
        parameters: JSON.stringify({
          'message': 'Ues something has gone wrong. Please try again or contact the Nila manager in your region.'
      })})
      return res.send('success')
    }
    // known issuer, load or init identity if wallet has been created.
    else if (typeof data.SK !== 'undefined') {
      // load or create new wallets and storage
      const { identityWallet, credentialWallet, proofService, dataStorage,DID,issuerAuthCredential } = typeof data.BabyJubJub === 'undefined' ? await init(phone,data.SK.S) : await instantiate(phone,data.SK.S,data.BabyJubJub.S)
      const userDID = DID

      // the new credential hasnt been stored yet, make sure it does.
      await dataStorage.credential.saveCredential(credential);

      // get request for MERKLE TREE proof
      const proofReqMtp: ZeroKnowledgeProofRequest = createStorageCredentialRequest(credentialRequest,input.ct,issuerDID);
      console.log('proofReqMtp', proofReqMtp)

      // generate proof
      const { proof: proofMTP } = await proofService.generateProof(proofReqMtp,userDID);

      console.log('proof', proofMTP)

      const proof_pub_json = JSON.stringify({
          'proof': proofMTP,
      })
      console.log('proof_pub_json', proof_pub_json)

      // link that let verifiers know: 
      //  - issuer
      //  - query and criteria

      // create the qr codes and return
      var addr = process.env.URI
      var zkProof = `${addr}/verify?text=${aadhar}${proof_pub_json}` 
      await QR.toFile('qr.png',zkProof)

      // store image on S3 bucket
      var filename = 'qr.png';
      await s3.upload({
        Bucket: process.env.S3BUCKET, 
        Key: filename, 
        Body: fs.readFileSync('qr.png'),
        ACL: 'public-read',
        ContentType: 'image/png',
      }).promise()

      // update persistent storage with new identifiers and credentials
      await storePersist(phone,dataStorage,userDID.string(),txID)

      // return url of QR image
      res.send(`https://${process.env.S3BUCKET}.s3.ap-south-1.amazonaws.com/${filename}`)
  }
});

app.post('/IssueProofOrigin', async (req: Request, res: Response) => {

  // API CALLED IN WABA FLOW: SUPPLY.py
  const client = require('twilio')(process.env.ACCOUNT_SID, process.env.AUTH_TOKEN);
  
  // parse req
  const input = req.body
  console.log(input)
  const phone = input.phone.split(':')[1]

  // recover wallet seed (DEMO: Users have not been transferred to Polygon )
  var params = {
    TableName: 'polygon_aes',
    Key: { 'phoneNumber': {'S': phone} },
    ProjectionExpression: 'SK,BabyJubJub,BusinessName,did,credentials,identities'
  }
  var data = await ddb.getItem(params).promise()
  var data = data.Item

  console.log('data', data)

  // unknown issuer, return request to formal sign-up
  if(data === undefined){
    client.studio.v2.flows('FW1327ad94088d2b26f52988905062b4c6')
    .executions
    .create({
      to: `whatsapp:${input.user_phone}`,
      from:"whatsapp:+13478481380",
      parameters: JSON.stringify({
        'message': 'Ues something has gone wrong. Please try again or contact the Nila manager in your region.'
    })})
    return res.send('success')
  }
  // known issuer, load or init identity if wallet has been created.
  else if (typeof data.SK !== 'undefined') {
    // load or create new wallets and storage
    const { identityWallet, credentialWallet, proofService, dataStorage,DID,issuerAuthCredential } = typeof data.BabyJubJub === 'undefined' ? await init(phone,data.SK.S) : await instantiate(phone,data.SK.S,data.BabyJubJub.S)
    const userDID = DID
    
    /*
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
    */

    // find recent token deposits on user address from token minter
    const blocknmb = await provider.core.getBlockNumber()
    console.log('blocknmb', blocknmb)
    const histblock = blocknmb - ((60*60*24*21) / 12.06) // doesnt have to be precise, current block minus estimated blocks by blocktime

    const txs = await provider.core.getAssetTransfers({
      fromBlock: '0x' + Math.round(histblock).toString(16).toUpperCase(), // find block of about 3 weeks ago.
      fromAddress: process.env.FIELD_ACTIVITY_MINT_CONTRACT,
      toAddress: data.SK.S,
      excludeZeroValue: false,
      category: ["erc20"],
    });

  // check for recent tx from our crop token mint contact ( not sufficient - can also be seperate cultivations!!)
    if (txs.transfers.length == 0){
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

      console.log('credentialRequest', credentialRequest)

      // generate proof
      const { proof, pub_signals } = await proofService.generateProof(credentialRequest,userDID);

      console.log('proof', proof)
      console.log('pub_signals', pub_signals)

      const proof_pub_json = JSON.stringify({
          'proof': proof,
          'pubsignals': pub_signals,
      })
      console.log('proof_pub_json', proof_pub_json)

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
          'pk': data.SK.S,
          }),
      };
      lambda.invoke(lambda_params).promise()
      // return flow to wait for the sensing node to finish (unclear how long, depends on queue)
      return res.send({ 'res': 0 })
    }
  }
});
  
app.listen(port, () => console.info(`listening on port ${port}!`));