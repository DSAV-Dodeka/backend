## Uitleg

Belangrijke informatie:
- We maken gebruik van access en ID tokens. Dit zijn zogenaamde JSON Web Tokens (JWTs), strings in een bepaald format waarvan je kunt verifiëren of ze authentiek zijn (te weten, zijn ze echt door de veilige backend gemaakt en klopt de informatie die erin staat).
- Met een access token kunnen requests naar de backend gemaakt worden, die ze kan verifiëren en dan afgeschermde informatie kan terugsturen. Het hebben van een "token" betekent dus dat je ingelogd bent.
- Deze tokens worden lokaal opgeslagen in de browser, zodat je niet telkens hoeft in te loggen. Echter, er is geen (volledig) veilige opslagplaats. Daarom hebben deze tokens slechts een beperkte levensduur, zodat een potentiële aanvaller er niet langdurig kwaad mee kan.
- Deze levensduur mag maar een paar uur zijn. Elke paar uur inloggen blijft irritant, dus daarom bestaan er ook "refresh tokens". Dit zijn geen JWTs, in tegenstelling tot de andere tokens. Ze bevatten encrypted (dus niet leesbaar voor de client) en verifieerbare informatie die de backend kan gebruiken om nieuwe ID tokens te sturen. Door deze refresh tokens ook te roteren en te voorkomen dat er meerdere tegelijkertijd bestaan, verhoogt dit de veiligheid en kunnen ze een levensduur van een maand (of mogelijk langer) hebben.

Dit is niet een zelfbedacht systeem, maar een implementatie van internetstandaarden, die rekening houden met allerlei verschillende aanvallen. In principe wordt volledig gehouden aan [RFC6749 Section 4.1 (OAuth 2.0)](https://datatracker.ietf.org/doc/html/rfc6749#section-4.1), maar omdat het hier gaat om een _authenticatie_ (=inlog, ipv autorisatie), wordt ook grotendeels voldaan aan [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html), vooral de additionele veiligheidstips. Op dit moment is er een vebeterde standaard in ontwikkeling, [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-04), waarvan de veiligheidstips ook worden opgevolgd. Die nieuwe standaard raadt aan in bijna alle gevallen de Authorization Code Flow with PKCE te volgen, wat wij ook doen.

Deze standaarden laten het exacte authenticatiesysteem volledig open. Hiermee wordt specifiek het systeem bedoeld waarmee je checkt of iemand is wie die is. In de meeste gevallen wordt dit gedaan door te checken of iemand over het correcte wachtwoord beschikt. Wachtwoordprotocollen staan al jarenlang onder druk, omdat het moeilijk is ze veilig te maken, vooral omdat mensen vaak slechte wachtwoorden kiezen. Er is daarom hier een keuze gemaakt voor het [OPAQUE-protocol](https://datatracker.ietf.org/doc/html/draft-irtf-cfrg-opaque-07), een internetstandaard onder ontwikkeling (maar wel al in de afrondende fase).

Helaas bestaan er (voor zover ik weet) geen lightweight implementaties van OAuth die tegelijkertijd makkelijk aanpasbaar zijn. Het vergt ook veel tussentijdse database queries. Verder is het een relatief simpel protocol, dus daarom is de keuze gemaakt dit zelf te doen.

Van OPAQUE bestaat een goede implementatie, geschreven in Rust. Gelukkig bestaan er manieren om Rust makkelijk aan te roepen vanuit JavaScript en Python. Hiervoor heb ik twee hele kleine libraries geschreven, elk met vier functies, [opaquepy](https://github.com/tiptenbrink/opaquepy)en [opaquewasm](https://github.com/tiptenbrink/opaquewasm). Die eerste werkt heel gemakkelijk en kan gewoon als package worden ingeladen. De tweede maakt gebruik van [WebAssembly](https://webassembly.org/), een platform dat het mogelijk maakt gecompileerde talen te gebruiken in de browser. Omdat alles op de browser moet werken, is dit iets ingewikkelder en is er speciale configuratie via webpack nodig om de bestanden in te laden.

### Specification

Authorization Code Flow according to [RFC6749 Section 4.1](https://datatracker.ietf.org/doc/html/rfc6749#section-4.1), as recommended by [Internet Draft OAuth 2.0 for Browser-Based Apps](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-browser-based-apps), since the frontend application can be recognized as a Javascript Application without a Backend (Section 6.3 of the latter document). 



We comply fully with OAuth 2.1 and implement an Authorization Code Flow with PKCE. We comply as much as possible with OpenID Connect, except on some points that are only for interoperability (like supporting certain algorithms), which we do not require.



### Useful resources

* https://auth0.com/docs/security/tokens/refresh-tokens/refresh-token-rotation
  * Other pages from https://auth0.com/docs
* https://www.ietf.org/archive/id/draft-ietf-oauth-v2-1-04.html
* https://openid.net/specs/openid-connect-core-1_0.html
* https://www.oauth.com/

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


## Remembering session

#### Why OPAQUE

OPAQUE is nieuw en kent nog weinig implementaties, maar is revolutionair in het veilig opslaan van wachtwoorden. In het verleden was de "gold standard" het opslaan van een hash en salt op de server. Het probleem hiermee was echter dat of de salt vrij beschikbaar moest worden gemaakt, of het wachtwoord moest tijdelijk beschikbaar zijn op de server. Als de salt vrij beschikbaar is, kan iemand al *voor* het hacken van de server rekenen aan de hash, iets wat niet onmogelijk is voor simpele wachtwoorden. Met OPAQUE kan dit pas na een potentiële hack, waarna iedereen er meteen van op de hoogte kan worden gebracht.