## Deployment

Sample config.toml

```toml
[authentication]
access_token_expire_minutes = 15
algorithm = "EdDSA"
```

### Private key for JSON Web Tokens

The [config](src/ahbackend/config/__init__.py) searches for a private key in the location defined by the environment variable `D3HUB_PKPATH`. You have to set this variable.
