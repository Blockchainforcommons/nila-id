import {
    CredentialStorage,
    InMemoryDataSource,
    W3CCredential,
    IdentityStorage,
    Identity,
    Profile,
    InMemoryMerkleTreeStorage,
    EthStateStorage,
    defaultEthConnectionConfig,
    InMemoryPrivateKeyStore,
    BjjProvider,
    KmsKeyType,
    KMS,
    CredentialStatusResolverRegistry,
    IssuerResolver,
    CredentialStatusType,
    RHSResolver,
    CredentialWallet,
    IdentityWallet,
    core,
  } from "@0xpolygonid/js-sdk";


const dataStorage = {
    credential: new CredentialStorage(new InMemoryDataSource<W3CCredential>()),
    identity: new IdentityStorage(
      new InMemoryDataSource<Identity>(),
      new InMemoryDataSource<Profile>()
    ),
    mt: new InMemoryMerkleTreeStorage(40),
    states: new EthStateStorage(defaultEthConnectionConfig),
    };

const memoryKeyStore = new InMemoryPrivateKeyStore();
const bjjProvider = new BjjProvider(KmsKeyType.BabyJubJub, memoryKeyStore);
const kms = new KMS();
kms.registerKeyProvider(KmsKeyType.BabyJubJub, bjjProvider);

const statusRegistry = new CredentialStatusResolverRegistry();
statusRegistry.register(
    CredentialStatusType.SparseMerkleTreeProof,
    new IssuerResolver()
);
statusRegistry.register(
    CredentialStatusType.Iden3ReverseSparseMerkleTreeProof,
    new RHSResolver(dataStorage.states)
);
const credWallet = new CredentialWallet(dataStorage,statusRegistry);
const wallet = new IdentityWallet(kms, dataStorage, credWallet);

export interface IdentityCreationOptions {
    method?: core.DidMethod;
    blockchain?: core.Blockchain;
    networkId?: core.NetworkId;
    revocationOpts: {
      id: string;
      type: CredentialStatusType;
      nonce?: number;
    };
    seed?: Uint8Array;
  }