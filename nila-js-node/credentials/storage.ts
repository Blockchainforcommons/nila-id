import {
    CredentialRequest,
    CredentialStatusType,
    CircuitId,
    ZeroKnowledgeProofRequest,
    core,
  } from "@0xpolygonid/js-sdk";
require('dotenv').config();

const rhsUrl = process.env.RHS_URL as string;

function ifPaddy(did: core.DID, input: any){
  let date = new Date();
  let schema;
  let subject;

  // paddy can be stored up to 10 years if the condition is 
  if (typeof input.conditions === 'undefined' || input.conditions !== 'raw' ){
    // set paddy as unprocessed (7 month expiration)
    date.setMonth(date.getMonth() + 7);
    schema = 'https://raw.githubusercontent.com/Blockchainforcommons/nila-id/master/schemas/StoreCredentials/StorePaddyCredential.json',
    subject = {
      id: did,
      //aadhar: '', //input.Aadhar,
      grade: input.store_grade,
      quantity: parseFloat(input.store_amount),
      //variety: '', //input.variety,
      //state: '', //input.condition,
    };
  }
  else {
    // set paddy as processed, 2 year expiration
    date.setMonth(date.getMonth() + 24);
    schema = 'https://raw.githubusercontent.com/Blockchainforcommons/nila-id/master/schemas/StoreCredentials/StorePaddyCredential.json',
    subject = {
      id: did,
      //aadhar: '', //input.Aadhar,
      grade: input.store_grade,
      quantity: parseFloat(input.store_amount),
      //variety: '', //input.variety,
      //state: '', //input.condition,
    };
  }
  return {schema, subject, date};
  }

export function createStorageCredential(did: core.DID, input: any) {
  if ( input.ct == 'paddy'){
    let { schema, subject, date } = ifPaddy(did,input)
    const credentialRequest: CredentialRequest = {
        credentialSchema: schema,
        type: "StoragePaddy",
        credentialSubject: subject,
        expiration: date.getTime(),
        revocationOpts: {
          type: CredentialStatusType.Iden3ReverseSparseMerkleTreeProof,
          id: rhsUrl,
        },
    };
    
    return credentialRequest;
  }
}

export function createStorageCredentialRequest(
  credentialRequest: CredentialRequest, ct: string, issuerDID: string
): ZeroKnowledgeProofRequest {

const Ct = ct[0].toUpperCase() + ct.slice(1) // make sure first letter is uppercase
console.log('CT', Ct)
const proofReqMtp: ZeroKnowledgeProofRequest = {
  id: 1693297968,
  circuitId: CircuitId.AtomicQueryMTPV2,
  optional: false,
  query: {
    allowedIssuers: [issuerDID],
    type: credentialRequest.type,
    context: `https://raw.githubusercontent.com/Blockchainforcommons/nila-id/master/schemas/StoreCredentials/Store${Ct}Credential.jsonld`,
    credentialSubject: {
      quantity: {},
    },
  },
};
return proofReqMtp;
}

export function createKYCAgeCredential(did: string) {
  const credentialRequest: CredentialRequest = {
    credentialSchema: "https://raw.githubusercontent.com/iden3/claim-schema-vocab/main/schemas/json/KYCAgeCredential-v3.json",
    type: "KYCAgeCredential",
    credentialSubject: {
      id: did,
      birthday: 19960424,
      documentType: 99,
    },
    expiration: 12345678888,
    revocationOpts: {
      type: CredentialStatusType.Iden3ReverseSparseMerkleTreeProof,
      id: rhsUrl,
    },
  };
  return credentialRequest;
}

export function createKYCAgeCredentialRequest(
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


