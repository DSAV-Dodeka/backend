Authorization Code Flow according to [RFC6749 Section 4.1](https://datatracker.ietf.org/doc/html/rfc6749#section-4.1), as recommended by [Internet Draft OAuth 2.0 for Browser-Based Apps](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-browser-based-apps), since the frontend application can be recognized as a Javascript Application without a Backend (Section 6.3 of the latter document). 

https://www.ietf.org/archive/id/draft-ietf-oauth-v2-1-04.html

We comply fully with OAuth 2.1 and implement an Authorization Code Flow with PKCE. We comply as much as possible with OpenID Connect, except on some points that are only for interoperability (like supporting certain algorithms), which we do not require.

https://auth0.com/docs/security/tokens/refresh-tokens/refresh-token-rotation

Refresh tokens are used for refreshing BOTH access tokens AND id tokens

id tokens are not very useful, but we implement them to reduce the risk of missing important parts of the OpenID spec.

**Resource Owner** - end-user

**Resource Server** - dodekabackend

**Client** - dodekaweb
- identifier: dodekaweb_client
- redirect_uri: .../callback

**Authorization Server** - dodekabackend?

1. a

Create an Authorization Request (Section 4.1.1)

2. b
3. c
4. d
5. e
6. f
7. g

https://openid.net/specs/openid-connect-core-1_0.html#IDToken