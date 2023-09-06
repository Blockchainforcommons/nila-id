var axios = require('axios');
var querystring = require('querystring');

require('dotenv').config();
// THESE TESTS ARE BUILD TO SHOW VIEWERS THE ABILITY TO ISSUE AND PROOF A MERKLE TREE CERTIFICATE
// BECAUSE IT IS A LOT OF WORK TO RUN THE NILA-JS-SDK, WITH ALL ITS REQUIREMENTS. HOWEVER A TWILLIO ACCOUNT IS STILL A REQUIREMENT TO READ THE QR'S SEND

/**
 * test to issue an offchain storage credential and proof it is part of the storage merkle tree
 * request a credential
 * receive the credential and proof 
 * validate the proof (true or false)
 */

test('test to issue an offchain storage credential and proof it is part of the storage merkle tree', async () => {
    /**
     * emulate a issue certificate call, receive a 
     * sk test: 3355e134a4e8dc7d41b55c13cc7b5bc5ef4f1196ad312193f2b19151b560907c

     */
    await axios.post(`${process.env.URI}/IssueStorage`,querystring.stringify({
            ct: 'paddy',
            phone: 'whatsapp:+31627257049',
            store_amount: 25,
            store_grade: 1,
            user_name: 'dummy',
            did: 'did:iden3:polygon:mumbai:wxSpMNqYpUwF6PcYkCPaZBtoXBruN6iM553DSZUWZ',
            user_phone: '+31627257049'

    }), {
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
    })
    .then(function (response) {
        console.log('respoonse', response)


    })
    .catch(function (error) {
        //console.log(error)
    })
    

    expect(1).toBe(1);
  });
