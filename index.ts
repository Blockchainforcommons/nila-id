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

const qr = require('qr-image');
const fs = require('fs');
const client = require('twilio')(process.env.ACCOUNT_SID, process.env.AUTH_TOKEN);
client.region = 'au1';
client.edge = 'sydney';

import {
    initInMemoryDataStorageAndWallets,
    initCircuitStorage,
    initProofService,
  } from "./walletSetup";

import { Url } from 'url';
import { Wallet } from 'ethers';

const rhsUrl = process.env.RHS_URL as string;
var ddb = new AWS.DynamoDB({apiVersion: '2012-08-10'});

AWS.config.update({
    accessKeyId: process.env.accessKeyId,
    secretAccessKey: process.env.secretAccessKey,
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

function createStorageCredential(did: core.DID, input: any) {
  let date = new Date();
  let schema;
  let subject;

  // paddy can be stored up to 10 years if the condition is 
  if (typeof input.conditions === 'undefined' || input.conditions !== 'raw' ){
      // set paddy as unprocessed (7 month expiration)
      date.setMonth(date.getMonth() + 7);
      schema = `${process.env.URI}/schemas/StoreCredentials/StorePaddyCredential.json`,
      subject = {
        id: did,
        aadhar: input.Aadhar,
        grade: input.store_grade,
        quantity: input.store_amount,
        variety: input.variety,
        state: input.condition,
      };
  }
  else {
      // set pady as processed, 2 year expiration
      date.setMonth(date.getMonth() + 24);
      schema = `${process.env.URI}/schemas/StoreCredentials/StorePaddyCredential.json`,
      subject = {
        id: did,
        aadhar: input.Aadhar,
        grade: input.store_grade,
        quantity: input.store_amount,
        variety: input.variety,
        state: input.condition,
      };
  }
  const credentialRequest: CredentialRequest = {
      credentialSchema: schema,
      type: "StorageComplianceCredential",
      credentialSubject: subject,
      expiration: date.getTime(),
      revocationOpts: {
        type: CredentialStatusType.Iden3ReverseSparseMerkleTreeProof,
        id: rhsUrl,
      },
  };
  
  return credentialRequest;
  }

function createKYCAgeCredentialRequest(
    circuitId: CircuitId,
    credentialRequest: CredentialRequest
  ): ZeroKnowledgeProofRequest {
    const proofReqSig: ZeroKnowledgeProofRequest = {
      id: 1,
      circuitId: CircuitId.AtomicQuerySigV2,
      optional: false,
      query: {
        allowedIssuers: ["*"],
        type: credentialRequest.type,
        context:
          "https://raw.githubusercontent.com/iden3/claim-schema-vocab/main/schemas/json-ld/kyc-v3.json-ld",
        credentialSubject: {
          documentType: {
            $eq: 99,
          },
        },
      },
    };

  const proofReqMtp: ZeroKnowledgeProofRequest = {
    id: 1,
    circuitId: CircuitId.AtomicQueryMTPV2,
    optional: false,
    query: {
      allowedIssuers: ["*"],
      type: credentialRequest.type,
      context:
        "https://raw.githubusercontent.com/iden3/claim-schema-vocab/main/schemas/json-ld/kyc-v3.json-ld",
      credentialSubject: {
        birthday: {
          $lt: 20020101,
        },
      },
    },
  };

  switch (circuitId) {
    case CircuitId.AtomicQuerySigV2:
      return proofReqSig;
    case CircuitId.AtomicQueryMTPV2:
      return proofReqMtp;
    default:
      return proofReqSig;
  }
}

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

    // API called in WABA flow handler.Store
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
    console.log('wallet_bjj', wallet_seed.Item.BabyJubJub.S)

    // generate the babyjubjub key from private key
    // TODO: FIND SOLUTION IN JS, TAKE PRESET

    let utf8Encode = new TextEncoder();
    const seedPhraseUser: Uint8Array = utf8Encode.encode(wallet_seed.Item.BabyJubJub.S);  
    console.log('seedPhraseUser key', seedPhraseUser) 

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
    const credentialRequest = createStorageCredential(userDID,input);
    const credential = await identityWallet.issueCredential(
        issuerDID,
        credentialRequest
    );
    // cache credential
    await dataStorage.credential.saveCredential(credential);

    // storagecreds are MTVP, so have to be published onchain
    const add = await identityWallet.addCredentialsToMerkleTree(
      [credential],
      issuerDID
    );

    // publish state
    await identityWallet.publishStateToRHS(issuerDID, rhsUrl);
  
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

    // send credential to user to generate proof
    client.messages
      .create({
        body: `Congratulations. ${wallet_seed.Item.BusinessName.S} has created your ${input.ct} storage certificates.\n\n* Quantity: ${input.store_amount}\n* Grade: ${input.store_grade}\nType *confirm* to generate the proof and sell your produce.`,
        to: `whatsapp:${input.user_phone}`,
        from:"whatsapp:+13478481380",
      })
      .then((message: any) => console.log(message.sid));

    // return success
    return res.send('success')

});

app.post('/ProofStorage', async (req: Request, res: Response) => {
    // API called in WABA flow sales.GenerateProof
    // receive input (device id, credentialRequest, userDID)
    const input = req.body
    console.log(input)
    const phone = input.phone.split(':')[1]
    const issuerDID = input.did

    // initialize wallets
    let { identityWallet, credentialWallet, dataStorage, proofService, circuitStorage} = await init()

    // recover wallet seed (DEMO: Users have not been transferred to Polygon )
    var params = {
      TableName: 'polygon_aes',
      Key: { 'phoneNumber': {'S': phone} },
      ProjectionExpression: 'SK,BabyJubJub'
    }
    var wallet_seed = await ddb.getItem(params).promise()
    console.log('wallet_bjj', wallet_seed.Item.BabyJubJub.S)

    let utf8Encode = new TextEncoder();
    const seedPhraseUser: Uint8Array = utf8Encode.encode(wallet_seed.Item.BabyJubJub.S);  
    console.log('seedPhraseUser key', seedPhraseUser) 

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
    // get request for proof
    const proofReqSig: ZeroKnowledgeProofRequest = createKYCAgeCredentialRequest(
      CircuitId.AtomicQueryMTPV2,
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
    var addr = 'https://fbae-2a02-a46a-7ff7-1-7109-a94f-21e6-e7d6.ngrok-free.app'
    var zkProof = `${addr}/verify?text=${proof_pub_json}` 
    console.log('zkproof', zkProof)
    var code = qr.image(zkProof, { type: 'svg' });
    code.pipe(fs.createWriteStream('qr.svg'));

    // return qr image
    res.send('success')
});
  

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


app.get('/', async (req: Request, res: Response) => {

    console.log("=============== generate proofs ===============");

    async function createIdentity(identityWallet: IIdentityWallet) {
        const { did, credential } = await identityWallet.createIdentity({
          method: core.DidMethod.Iden3,
          blockchain: core.Blockchain.Polygon,
          networkId: core.NetworkId.Mumbai,
          revocationOpts: {
            type: CredentialStatusType.Iden3ReverseSparseMerkleTreeProof,
            id: rhsUrl,
          },
        });
      
        return {
          did,
          credential,
        };
    }
        
    let { dataStorage, credentialWallet, identityWallet } =
        await initInMemoryDataStorageAndWallets();

    const circuitStorage = await initCircuitStorage();
    const proofService = await initProofService(
        identityWallet,
        credentialWallet,
        dataStorage.states,
        circuitStorage
    );

    const { did: userDID, credential: authBJJCredentialUser } =
        await createIdentity(identityWallet);

    console.log("=============== user did ===============");
    console.log(userDID.string());

    const { did: issuerDID, credential: issuerAuthBJJCredential } =
        await createIdentity(identityWallet);

    const credentialRequest = createStorageCredential(userDID,'input');

    const credential = await identityWallet.issueCredential(
        issuerDID,
        credentialRequest
    );
    await dataStorage.credential.saveCredential(credential);

    console.log('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    console.log(credential)

    const proofReqSig: ZeroKnowledgeProofRequest = createKYCAgeCredentialRequest(
        CircuitId.AtomicQuerySigV2,
        credentialRequest
      );
    
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
    var addr = 'https://fbae-2a02-a46a-7ff7-1-7109-a94f-21e6-e7d6.ngrok-free.app'
    var zkProof = `${addr}/verify?text=${proof_pub_json}` 
    console.log('zkproof', zkProof)
    var code = qr.image(zkProof, { type: 'svg' });
    code.pipe(fs.createWriteStream('qr.svg'));
    /*

    const walletKey = process.env.WALLET_KEY as string;

    // Q = if key is not PK but social login, how to initiate identity..
    
        FLOW:
            - ISSUER CREATES IDENTITY WITH KEY
            - ISSUER ISSUES CREDENTIAL USING USER DID
            - USER CLAIMS CREDENTIAL
            - USER PROOFS CREDENTIAL
            - VERIFIER RECEIVES ZNP OF CREDENTIAL - TRUE OR FALSE, OR ATTRIBUTE
            - 


    // initiate identity DID (changes each call)
    //console.log('req', req)

    // create identity or instantiate identity for user

    // example DID (android app)
    //let userDID = "did:polygonid:polygon:mumbai:2qKoN6262C6zARF7tDVTtxKhCC3eK3FRHjeTQ9Xm6i"
    
    let { did: userDID } = await identityCreation();
    // create identity or instantiate identity for issuer
    let { did: issuerDID,identityWallet,credentialWallet,dataStorage } = await identityCreation();
    
    // issue credential
    let {credential,credentialRequest} = await issueCredential(userDID.string(),issuerDID,identityWallet,dataStorage);

    // publish the credentials onchain. Using the signer key derived from web3 auth social login!!!
    let {proofService,txId} = await publishState(dataStorage,identityWallet,walletKey,issuerDID,credentialWallet,credential)

    console.log('ask for proof::::::')
    // generate proof
    let {proof,vp} = await genProof(proofService,credentialRequest,userDID.string())

    console.log('result', proof)    
    console.log('vp', vp)
    console.log(' userDID:core.DID', userDID)

    */
    res.send('Express app works!')
});

app.get('/verify', async (req: Request, res: Response) => {
    console.log(req.query);

    let { dataStorage, credentialWallet, identityWallet } =
        await initInMemoryDataStorageAndWallets();

    const circuitStorage = await initCircuitStorage();
    const proofService = await initProofService(
        identityWallet,
        credentialWallet,
        dataStorage.states,
        circuitStorage
    );
    //const sigProofOk = await proofService.verifyProof(
    //{ proof, pub_signals },
    //CircuitId.AtomicQuerySigV2
    //);

    //res.send(`RESULT valid: ${sigProofOk}`)


    // flow to verify a generated proof through a QR scan 
    // Nila users publish and share QRs to sell there produce. To speed up the sales process, we use
    // a standard set of generated proofs. Interested buyers can call this API to verify the proof
    // without the need of a app.
    // !! this is simply an example of a verifier. In production, this should be another entity.



})

app.listen(port, () => console.info(`Express listening on port ${port}!`));