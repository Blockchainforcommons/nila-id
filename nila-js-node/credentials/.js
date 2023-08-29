{
    credentialSchema: 'https://raw.githubusercontent.com/iden3/claim-schema-vocab/main/schemas/json/KYCAgeCredential-v3.json',
    type: 'KYCAgeCredential',
    credentialSubject: {
      id: 'did:polygonid:polygon:mumbai:2qLhgrN1nGUMZXCwmeLFVxEPAR8ko5TXZseG445W5b',
      birthday: 19960424,
      documentType: 99
    },
    expiration: 12345678888,
    revocationOpts: {
      type: 'Iden3ReverseSparseMerkleTreeProof',
      id: 'https://rhs-staging.polygonid.me'
    }
  }


  {
  credentialSchema: 'https://github.com/Blockchainforcommons/nila-id/blob/master/schemas/StoreCredentials/StorePaddyCredential.json',
  type: 'StoragePaddy',
  credentialSubject: {
    id: 'did:polygonid:polygon:mumbai:2qLhgrN1nGUMZXCwmeLFVxEPAR8ko5TXZseG445W5b',
    aadhar: '',
    grade: '3',
    quantity: 18,
    variety: '',
    state: ''
  },
  expiration: 1711543702532,
  revocationOpts: {
    type: 'Iden3ReverseSparseMerkleTreeProof',
    id: 'https://rhs-staging.polygonid.me'
  }
}