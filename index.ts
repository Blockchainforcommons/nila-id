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
    createKYCAgeCredential, 
    createStorageCredentialRequest, 
    createKYCAgeCredentialRequest 
  } from './credentials/storage';

import {
    initInMemoryDataStorageAndWallets,
    initCircuitStorage,
    initProofService,
  } from "./walletSetup";

const qr = require('qr-image');
const fs = require('fs');
var path = require('path');
const rhsUrl = process.env.RHS_URL as string;
require('dotenv').config();

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
    var zkProof = `${addr}/verify?text=${proof_pub_json}` 
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

  // API CALLED IN WABA FLOW: handler.Proof


});

  
    /*
    // API to generate proof 
    //const userDID = core.DID.parse(req.body.user_DID)

    //const pk: string = '3355e134a4e8dc7d41b55c13cc7b5bc5ef4f1196ad312193f2b19151b560907c'
    //let userDID = core.DID.parse("did:polygonid:polygon:mumbai:2qKoN6262C6zARF7tDVTtxKhCC3eK3FRHjeTQ9Xm6i")

    // init wallets and storage
    

    // instantiate identies (user)
    
    // get credential from APIs..
    dataStorage.credential.saveCredential(credential);

    console.log('this is the user DID',userDID)
    console.log('this is the user from API','did:polygonid:polygon:mumbai:2qLhgrN1nGUMZXCwmeLFVxEPAR8ko5TXZseG445W5b')

    console.log('datastorage', dataStorage)

    // find get identity..
    console.log('credentialRequest', credentialRequest)
    // instantiate proofservice

    console.log('proofReqSig', proofReqSig)
    console.log('proofService', proofService)
    console.log('made it to here.........')
    
    // generate proof
    const { proof, pub_signals } = await proofService.generateProof(
        proofReqSig,
        userDID
      );
    console.log('proof', proof)
    return res.send('successsss')

    // verify proof
    const sigProofOk = await proofService.verifyProof(
    { proof, pub_signals },
    CircuitId.AtomicQuerySigV2
    );
      console.log("valid: ", sigProofOk);
    */

app.listen(port, () => console.info(`Express listening on port ${port}!`));