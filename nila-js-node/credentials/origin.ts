import {
    CredentialRequest,
    CredentialStatusType,
    CircuitId,
    ZeroKnowledgeProofRequest,
    core,
  } from "@0xpolygonid/js-sdk";
  require('dotenv').config();

  const rhsUrl = process.env.RHS_URL as string;

  export function createOriginCredential(did: core.DID, input: any, md: any) {
    let date = new Date();
    date.setMonth(date.getMonth() + 6);
    const credentialRequest: CredentialRequest = {
        credentialSchema: 'https://raw.githubusercontent.com/Blockchainforcommons/nila-id/master/nila-js-node/schemas/OriginCredentials/OriginCredential.json',
        type: "Origin",
        credentialSubject: {
            id: did,
            ct: md.ct,
            coordinates: { 
                lat: md.lat,
                lng: md.lng
            },
            aadhar: input.Aadhar, //input.Aadhar
            },
        expiration: date.getTime(), // origin certificates have a half year expiration 
        revocationOpts: {
            type: CredentialStatusType.Iden3ReverseSparseMerkleTreeProof,
            id: rhsUrl,
        },
      };
    return credentialRequest;
}

export function createOriginCredentialRequest(
  credentialRequest: CredentialRequest
): ZeroKnowledgeProofRequest {
const proofReqMtp: ZeroKnowledgeProofRequest = {
  id: 1693298208,
  circuitId: CircuitId.AtomicQuerySigV2OnChain,
  optional: false,
  query: {
    allowedIssuers: ["*"], // Nila onchain issuer
    type: credentialRequest.type,
    context: 'https://raw.githubusercontent.com/Blockchainforcommons/nila-id/master/nila-js-node/schemas/OriginCredentials/OriginCredential.jsonId',
    credentialSubject: {
      ct: {},
    },
  },
};
return proofReqMtp;
}



