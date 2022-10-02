# Key rotation

Key management and rotation is not a trivial problem.

https://datatracker.ietf.org/doc/html/rfc7517#appendix-C.3
https://cryptography.io/en/latest/hazmat/primitives/asymmetric/serialization/#serialization-encodings
https://www.rfc-editor.org/rfc/rfc8037.html#section-2

https://www.rfc-editor.org/rfc/rfc7518.html
https://www.rfc-editor.org/rfc/rfc7517.html JWK

We will store the keys as an encrypted JSON Web Key Set, encrypted with a runtime key (from the dodeka secrets). Keys will be regenerated automatically.

The opaque setup value will also be rotated automatically.

At startup, the encrypted JSON Web Key Set will be extracted from the database. It will then be decrypted and the value replaced.